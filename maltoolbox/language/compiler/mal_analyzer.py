import logging
import re
from tree_sitter import Node
from .distributions import Distributions, DistributionsException
from typing import Any, Tuple, List


class malAnalyzerException(Exception):
    def __init__(self, error_message):
        self._error_message = error_message
        super().__init__(self._error_message)


class malAnalyzer:
    """
    A class to preform syntax-checks for MAL.
    """

    def __init__(self, *args, **kwargs) -> None:
        self._error: bool = False
        self._warn: bool = False
        self._preform_post_analysis = 0

        self._defines: dict = {}
        self._assets: dict = {}
        self._category: dict = {}
        self._metas: dict = {}
        self._steps: dict = {}
        self._vars: dict = {}
        self._associations: dict = {}

        self._all_associations: list[dict[str, Any]] = []
        self._current_vars: list[str] = []
        self._include_stack: list[str] = []

        self._error_msg: str = ''

        super().__init__(*args, **kwargs)

    def _raise_analyzer_exception(self, error_msg: str):
        logging.error(error_msg)
        raise malAnalyzerException(error_msg)

    def has_error(self) -> bool:
        return self._error

    def has_warning(self) -> bool:
        return self._warn

    def _post_analysis(self) -> None:
        """
        Perform a post-analysis to confirm that the
        mandatory fields and relations are met.
        """
        self._analyse_defines()
        self._analyse_extends()
        self._analyse_abstract()
        self._analyse_parents()
        self._analyse_association()
        self._analyse_steps()
        self._analyse_fields()
        self._analyse_variables()
        self._analyse_reaches()

    def _analyse_defines(self) -> None:
        """
        Check for mandatory defines: ID & Version
        """
        if 'id' in self._defines.keys():
            define_value: str = self._defines['id']['value']
            if len(define_value) == 0:
                error_msg = "Define 'id' cannot be empty"
                self._raise_analyzer_exception(error_msg)
        else:
            error_msg = 'Missing required define \'#id: ""\''
            self._raise_analyzer_exception(error_msg)

        if 'version' in self._defines.keys():
            version: str = self._defines['version']['value']
            if not re.match(r'\d+\.\d+\.\d+', version):
                error_msg = "Define 'version' must be valid semantic versioning without pre-release identifier and build metadata"
                self._raise_analyzer_exception(error_msg)
        else:
            error_msg = 'Missing required define \'#version: ""\''
            self._raise_analyzer_exception(error_msg)

    def _analyse_extends(self) -> None:
        """
        For all assets which extend another, verify if the extended asset exists
        """
        extend_asset_name: str = ''
        for asset in self._assets:
            asset_node: Node = self._assets[asset]['node']
            if asset_node.child_by_field_name('extends'):
                # Next sibling is the identifier itself
                extend_asset = asset_node.child_by_field_name('extends')
                if extend_asset and extend_asset.next_sibling:
                    if extend_asset.next_sibling.text:
                        extend_asset_name = extend_asset.next_sibling.text.decode()

                if extend_asset_name not in self._assets:
                    """
                    Do we need to check if the extended asset is 
                    in the same category? If so we can load the asset
                    and check it's parent
                    """
                    error_msg = f"Asset '{extend_asset_name}' not defined"
                    self._raise_analyzer_exception(error_msg)

    def _analyse_abstract(self) -> None:
        """
        For every abstract asset, verify if it is extended by another asset
        """
        for parent in self._assets:
            parent_node: Node = self._assets[parent]['node']
            parent_node_id_child = parent_node.child_by_field_name('id')
            assert parent_node_id_child, 'No child id'
            assert parent_node_id_child.text, 'No child id text'
            parent_node_name: str = parent_node_id_child.text.decode()
            if (
                parent_node.children[0].text
                and parent_node.children[0].text.decode() == 'abstract'
            ):
                found: bool = False
                for extendee in self._assets:
                    extendee_node: Node = self._assets[extendee]['node']
                    extendee_node_extender = extendee_node.child_by_field_name(
                        'extends'
                    )
                    if (
                        extendee_node_extender
                        and extendee_node_extender.next_sibling
                        and extendee_node_extender.next_sibling.text
                        and extendee_node_extender.next_sibling.text.decode()
                        == parent_node_name
                    ):
                        found = True
                        break
                if not found:
                    self._warn = True
                    logging.warning(
                        f"Asset '{parent_node_name}' is abstract but never extended to"
                    )

    def _analyse_parents(self) -> None:
        """
        Verify if there are circular extend relations
        """
        for asset in self._assets:
            parents: list[str] = []
            parent_node: Node | None = self._assets[asset]['node']
            while parent_node and parent_node.type == 'asset_declaration':
                parent_name_node = parent_node.child_by_field_name('id')
                assert parent_name_node and parent_name_node.text, (
                    'Asset need name node with text'
                )
                parent_name: str = parent_name_node.text.decode()
                if parent_name in parents:
                    error_msg: str = ' -> '.join(parents)
                    error_msg += f' -> {parent_name}'
                    error_msg = f"Asset '{parent_name}' extends in loop '{error_msg}'"
                    self._raise_analyzer_exception(error_msg)
                parents.append(parent_name)
                parent_node = self._get_assets_extendee(parent_node)

    def _get_assets_extendee(self, node: Node) -> Node | None:
        """
        Verifies if the current asset extends another and, if so, return the parent's context
        """
        if extender_node := node.child_by_field_name('extends'):
            extender_name_node = extender_node.next_sibling
            assert extender_name_node and extender_name_node.text, (
                'Asset need name node with text'
            )
            extender_node_name = extender_name_node.text.decode()
            return self._assets[extender_node_name]['node']
        return None

    def _analyse_reaches(self) -> None:
        """
        For every attackStep in every asset, verify if the prerequisites point to assets and that the reaches point to
        attack steps
        """
        for asset in self._assets.keys():
            attack_steps = self._assets[asset]['obj']['attackSteps']
            for attack_step in attack_steps:
                if attack_step['type'] in ['exist', 'notExist']:
                    if attack_step['ttc']:
                        error_msg = f"Attack step of type '{attack_step['type']}' must not have TTC"
                        self._raise_analyzer_exception(error_msg)
                    if attack_step['requires']:
                        # Verify if every requires expression returns an asset
                        for expr in attack_step['requires']['stepExpressions']:
                            if not self._check_to_asset(asset, expr):
                                error_msg = (
                                    f'Line {self._steps[asset][attack_step["name"]]["node"].start_point.row}: '
                                    + "All expressions in requires ('<-') must point to a valid asset"
                                )
                                self._raise_analyzer_exception(
                                    self._error_msg + error_msg
                                )
                    else:
                        error_msg = f"Attack step of type '{attack_step['type']}' must have require '<-'"
                        self._raise_analyzer_exception(error_msg)
                elif attack_step['requires']:
                    error_msg = "Require '<-' may only be defined for attack step type exist 'E' or not-exist '!E'"
                    self._raise_analyzer_exception(error_msg)
                if attack_step['reaches']:
                    # Verify if every reaches expresion returns an attack step
                    for expr in attack_step['reaches']['stepExpressions']:
                        if not self._check_to_step(asset, expr):
                            error_msg = (
                                f'Line {self._steps[asset][attack_step["name"]]["node"].start_point.row}: '
                                + "All expressions in reaches ('->') must point to a valid attack step"
                            )
                            self._raise_analyzer_exception(self._error_msg + error_msg)

    def _analyse_association(self) -> None:
        """
        For every association, verify if the assets exist
        """
        for association in self._all_associations:
            leftAsset = association['association']['leftAsset']
            rightAsset = association['association']['rightAsset']

            if leftAsset not in self._assets.keys():
                error_msg = f"Left asset '{leftAsset}' is not defined"
                self._raise_analyzer_exception(error_msg)
            if rightAsset not in self._assets.keys():
                error_msg = f"Right asset '{leftAsset}' is not defined"
                self._raise_analyzer_exception(error_msg)

    def _analyse_fields(self) -> None:
        """
        Update a variable's fields (associations) to include its parents associations.
        Also checks if an association has been defined more than once in a hierarchy
        """
        for asset in self._assets.keys():
            parents = self._get_parents(self._assets[asset]['node'])
            for parent in parents:
                for association in self._all_associations:
                    leftAsset = association['association']['leftAsset']
                    rightAsset = association['association']['rightAsset']
                    if leftAsset == parent:
                        rightField = association['association']['rightField']
                        self._add_field(parent, asset, rightField, association)
                    if rightAsset == parent:
                        leftField = association['association']['leftField']
                        self._add_field(parent, asset, leftField, association)

    def _add_field(self, parent: str, asset: str, field: str, association: dict):
        # Check that this asset does not have an assoication with the same name
        if asset not in self._associations or field not in self._associations[asset]:
            # Check if there isn't a step with the same name
            step_node = self._has_step(asset, field)
            if not step_node:
                if asset not in self._associations.keys():
                    self._associations[asset] = {
                        field: {k: association[k] for k in ['association', 'node']}
                    }
                else:
                    self._associations[asset][field] = {
                        k: association[k] for k in ['association', 'node']
                    }
            # Otherwise, this will be an error
            else:
                error_msg = f'Field {field} previously defined as an attack step at {step_node.start_point.row}'
                self._raise_analyzer_exception(error_msg)
        # Association field was already defined for this asset
        else:
            error_msg = f'Field {parent}.{field} previously defined at {self._associations[asset][field]["node"].start_point.row}'
            self._raise_analyzer_exception(error_msg)

    def _has_step(self, asset, field):
        if asset in self._steps.keys() and field in self._steps[asset]:
            return self._steps[asset][field]['node']
        return None

    def _variable_to_asset(self, asset: str, var: str):
        """
        Checks if there is no cycle in the variables and verifies that it points to
        an existing asset
        """
        if var not in self._current_vars:
            self._current_vars.append(var)
            res = self._check_to_asset(
                asset, self._vars[asset][var]['var']['stepExpression']
            )
            self._current_vars.pop()
            return res

        cycle = '->'.join(self._current_vars) + '->' + var
        error_msg = f"Variable '{var}' contains cycle {cycle}"
        self._raise_analyzer_exception(error_msg)

    def _analyse_variables(self):
        """
        This function will verify if an asset which extends another does not redefine a variable.
        It also updates the list of variables for an asset to includes its parent's variables

        Once that is done, we need to guarantee that the variable points to an asset and that
        there are no loops in the variables, i.e. a variable does not somehow reference itself
        """
        for asset in self._assets.keys():
            parents = self._get_parents(self._assets[asset]['node'])
            parents.pop()  # The last element is the asset itself, no need to check again if variable is defined twice
            for parent in parents:
                if parent not in self._vars.keys():
                    continue  # If parent has no variables, we don't need to do anything
                if asset not in self._vars.keys():
                    self._vars[asset] = self._vars[
                        parent
                    ]  # If asset has no variables, just inherit its parents variables
                    continue
                # Otherwise, we do need to check if variables are defined more than once
                for var in self._vars[asset].keys():
                    if (
                        parent in self._vars.keys()
                        and var in self._vars[parent].keys()
                        and self._vars[asset][var]['node']
                        != self._vars[parent][var]['node']
                    ):
                        error_msg = f"Variable '{var}' previously defined at {self._vars[parent][var]['node'].start_point.row}"
                        self._raise_analyzer_exception(error_msg)
                self._vars[asset].update(self._vars[parent])

            # If the current asset has variables, we want to check they point to an asset
            if asset in self._vars.keys():
                for var in self._vars[asset].keys():
                    if self._variable_to_asset(asset, var) is None:
                        error_msg = f"Variable '{var}' defined at {self._vars[asset][var]['node'].start_point.row} does not point to an asset"
                        self._raise_analyzer_exception(self._error_msg + error_msg)

    def _check_to_step(self, asset, expr) -> Any:
        """
        Given a reaches, verify if the expression resolves to a valid AttackStep for an existing Asset
        """
        match expr['type']:
            # Returns an attackStep if it exists for this asset
            case 'attackStep':
                if asset in self._assets.keys():
                    for attackStep in self._steps[asset].keys():
                        if attackStep == expr['name']:
                            return self._steps[asset][attackStep]['step']
                error_msg = (
                    f"Attack step '{expr['name']}' not defined for asset '{asset}'"
                )
                self._raise_analyzer_exception(error_msg)
            # Returns an attackStep if it exists for the asset returned by the lhs expression
            case 'collect':
                if left_target := self._check_to_asset(asset, expr['lhs']):
                    return self._check_to_step(left_target, expr['rhs'])
                return None
            case _:
                error_msg = 'Last step is not attack step'
                self._raise_analyzer_exception(error_msg)

    def _check_to_asset(self, asset, expr) -> Any:
        """
        Verify if the expression resolves to an existing Asset
        """
        match expr['type']:
            # field - verify if asset exists via associations
            case 'field':
                return self._check_field_expr(asset, expr)
            # variable - verify if there is a variable with this name
            case 'variable':
                return self._check_variable_expr(asset, expr)
            # collect - return asset pointed by all the parts in the expression
            case 'collect':
                return self._check_collect_expr(asset, expr)
            # set - verify if the assets in the operation have an common ancestor
            case 'union' | 'intersection' | 'difference':
                return self._check_set_expr(asset, expr)
            # transitive - verify if the asset before * (STAR) exists
            case 'transitive':
                return self._check_transitive_expr(asset, expr)
            # subtype - verifies if the asset inside [] is a child from the asset preceding it
            case 'subType':
                return self._check_sub_type_expr(asset, expr)
            case _:
                logging.error(f"Unexpected expression '{expr['type']}'")
                self._error = True
                return None

    def _check_field_expr(self, asset, expr):
        """
        Check if an asset exists by checking the associations for the current asset
        """
        if asset in self._associations.keys():
            for association in self._associations[asset].keys():
                association = self._associations[asset][association]['association']
                if expr['name'] == association['leftField']:
                    if self._get_asset_name(association['leftAsset']):
                        return association['leftAsset']
                if expr['name'] == association['rightField']:
                    if self._get_asset_name(association['rightAsset']):
                        return association['rightAsset']

        # Verify if there is a variable defined with the same name; possible the user forgot to call it
        extra = ''
        if asset in self._vars.keys() and expr['name'] in self._vars[asset].keys():
            extra = f", did you mean the variable '{expr['name']}()'?"
            self._warn = True

        self._error_msg = (
            f"Field '{expr['name']}' not defined for asset '{asset}'" + extra + '\n'
        )

    def _check_variable_expr(self, asset, expr):
        """
        Check if there is a variable reference in this asset with the user identifier.
        """
        if asset in self._vars.keys() and expr['name'] in self._vars[asset].keys():
            return self._variable_to_asset(asset, expr['name'])

        self._error_msg = f"Variable '{expr['name']}' is not defined\n"
        return None

    def _check_collect_expr(self, asset, expr):
        """
        Iteratively, retrieve the asset pointed by the leftmost expression and, recursively, check the rhs associated
        with each lhs.
        """
        if left_target := self._check_to_asset(asset, expr['lhs']):
            return self._check_to_asset(left_target, expr['rhs'])
        return None

    def _check_set_expr(self, asset, expr) -> None:
        """
        Obtains the assets pointed by boths hs's and verifies if they have a common ancestor
        """
        lhs_target = self._check_to_asset(asset, expr['lhs'])
        rhs_target = self._check_to_asset(asset, expr['rhs'])
        if not lhs_target or not rhs_target:
            return None

        if target := self._get_LCA(lhs_target, rhs_target):
            return target

        self._error_msg = (
            f"Types '{lhs_target}' and '{rhs_target}' have no common ancestor\n"
        )
        return None

    def _get_LCA(self, lhs_target, rhs_target):
        """
        Receives two assets and verifies if they have an ancestor in common
        """
        if self._is_child(lhs_target, rhs_target):
            return lhs_target
        elif self._is_child(rhs_target, lhs_target):
            return rhs_target
        else:
            lhs_node = self._assets[lhs_target]['node']
            rhs_node = self._assets[rhs_target]['node']
            lhs_parent_node = self._get_assets_extendee(lhs_node)
            rhs_parent_node = self._get_assets_extendee(rhs_node)
            if not lhs_parent_node or not rhs_parent_node:
                return None
            return self._get_LCA(
                lhs_parent_node.child_by_field_name('id').text.decode(),
                rhs_parent_node.child_by_field_name('id').text.decode(),
            )

    def _check_sub_type_expr(self, asset, expr) -> None:
        """
        Given expr[ID], obtains the assets given by expr and ID and verifies if ID is
        a child of expr
        """
        target = self._check_to_asset(asset, expr['stepExpression'])
        if not target:
            return None

        if asset_type := self._get_asset_name(expr['subType']):
            if self._is_child(target, asset_type):
                return asset_type

            self._error_msg = f"Asset '{asset_type}' cannot be of type '{target}'\n"
        return None

    def _check_transitive_expr(self, asset, expr) -> None:
        """
        Given expr*, obtain the asset given by expr and verify if it is a child of the current asset
        """
        if res := self._check_to_asset(asset, expr['stepExpression']):
            if self._is_child(asset, res):
                return res

            self._error_msg = f"Previous asset '{asset}' is not of type '{res}'\n"
        return None

    def _is_child(self, parent_name, child_name):
        """
        Receives two assets and verifies if one extends the other
        """
        if parent_name == child_name:
            return True

        if valid_asset := self._get_asset_name(child_name):
            asset_node: Node = self._assets[valid_asset]['node']
            if parent_node := self._get_assets_extendee(asset_node):
                child_parent_name = self._get_asset_name(
                    parent_node.child_by_field_name('id').text.decode()
                )
                return self._is_child(parent_name, child_parent_name)

        return False

    def _get_parents(self, node: Node) -> list[str]:
        """
        Given an asset, obtain its parents in inverse order.
        I.e., A->B->C returns [C,B,A] for asset A
        """
        name_node = node.child_by_field_name('id')
        assert name_node and name_node.text, 'Name node needs text'
        parents = [name_node.text.decode()]
        while node.child_by_field_name('extends'):
            extends_node = node.child_by_field_name('extends')
            assert extends_node, 'Need extends node'
            assert extends_node.next_sibling and extends_node.next_sibling.text
            parent_name = extends_node.next_sibling.text.decode()
            if parent_name in parents:
                break
            parents.insert(0, parent_name)
            node = self._assets[parent_name]['node']
        return parents

    def _get_asset_name(self, name):
        if name in self._assets.keys():
            return name

        logging.error(f"Asset '{name}' not defined")
        self._error = True
        return None

    def _analyse_steps(self) -> None:
        """
        For each asset, obtain its parents and analyse each step
        """
        for asset in self._assets.keys():
            parents = self._get_parents(self._assets[asset]['node'])
            self._read_steps(asset, parents)

    def _attackStep_seen_in_parent(
        self, attackStep: str, seen_steps: List
    ) -> str | None:
        """
        Given a list of parent scopes, verify if the attackStep has been defined
        """
        for parent, parent_scope in seen_steps:
            if attackStep in parent_scope:
                return parent
        return None

    def _read_steps(self, asset: str, parents: List) -> None:
        """
        For an asset, check if every step is properly defined in accordance to its hierarchy, i.e. if any of the asset's parents
        also defines this step
        """

        seen_steps: list[tuple] = []
        for parent in parents:
            # If this parent has no steps, skip it
            if parent not in self._steps.keys():
                continue

            current_steps = []
            for attackStep in self._steps[parent].keys():
                # Verify if attackStep has not been defined in the current asset
                if attackStep not in current_steps:
                    # Verify if attackStep has not been defined in any parent asset
                    prevDef_parent = self._attackStep_seen_in_parent(
                        attackStep, seen_steps
                    )
                    if not prevDef_parent:
                        # Since this attackStep has never been defined, it must either not reach or reach with '->'
                        attackStep_node = self._steps[parent][attackStep]['node']
                        attackStep_node_reaches = attackStep_node.child_by_field_name(
                            'reaches'
                        )
                        if (
                            not attackStep_node_reaches
                            or attackStep_node_reaches.child_by_field_name(
                                'operator'
                            ).text.decode()
                            == '->'
                        ):
                            # Valid step
                            current_steps.append(attackStep)
                        else:
                            # Step was defined using '+>', but there is nothing to inherit from
                            error_msg = f"Cannot inherit attack step '{attackStep}' without previous definition"
                            self._raise_analyzer_exception(error_msg)
                    else:
                        # Step was previously defined in a parent
                        # So it must be of the same type (&, |, #, E, !E)
                        attackStep_node = self._steps[parent][attackStep]['node']
                        parent_attackStep_node = self._steps[prevDef_parent][
                            attackStep
                        ]['node']
                        if (
                            attackStep_node.child_by_field_name('step_type').text
                            == parent_attackStep_node.child_by_field_name(
                                'step_type'
                            ).text
                        ):
                            # Valid step
                            current_steps.append(attackStep)
                        else:
                            # Invalid, type mismatches that of parent
                            error_msg = (
                                f"Cannot override attack step '{attackStep}' previously defined "
                                + f"at {parent_attackStep_node.start_point.row} with different type '{attackStep_node.child_by_field_name('step_type').text.decode()}' "
                                + f"=/= '{parent_attackStep_node.child_by_field_name('step_type').text.decode()}'"
                            )
                            self._raise_analyzer_exception(error_msg)
            seen_steps.append((parent, current_steps))

        for parent, steps in seen_steps:
            for step in steps:
                if asset not in self._steps.keys():
                    self._steps[asset] = {step: self._steps[parent][step]}
                else:
                    self._steps[asset][step] = self._steps[parent][step]

    def check_source_file(self, node: Node) -> None:
        """
        We only want to preform _post_analysis as the very last step.
        """
        if self._preform_post_analysis == 0:
            self._post_analysis()
        else:
            self._include_stack.pop()
            self._preform_post_analysis -= 1

    def check_asset_declaration(self, node: Node, asset: dict) -> None:
        """
        Given an asset, verify if it has been previously defined in the same category

        {
        'asset':
            {
            'node': node,
            'obj' : dict,
            'parent':
                {
                'name': str,
                'node': node,
                }
            }
        }
        """
        asset_name = asset['name']
        assert node.parent, 'Category node needed'
        category_name_node = node.parent.child_by_field_name('id')
        assert category_name_node and category_name_node.text, 'Category need name'
        category_name = category_name_node.text.decode()

        if not asset_name:
            logging.error(
                f'Asset was defined without a name at line {node.start_point.row}'
            )
            self._error = True
            return

        # Check if asset was previously defined in the same category.
        if asset_name in self._assets.keys():
            prev_asset_line = self._assets[asset_name]['node'].start_point.row
            error_msg = f"Asset '{asset_name}' previously defined at {prev_asset_line}"
            self._raise_analyzer_exception(error_msg)
        else:
            self._assets[asset_name] = {
                'node': node,
                'obj': asset,
                'parent': {'name': category_name, 'node': node.parent},
            }

    def check_meta(self, node: Node, data: Tuple[str, str]) -> None:
        """
        Given a meta, verify if it was previously defined for the same type (category, asset, step or association)
        """

        meta_name, _ = data

        # Check if we don't have the metas for this parent (category, asset, step or association)
        if node.parent not in self._metas.keys():
            self._metas[node.parent] = {meta_name: node}
        # Check if the new meta is not already defined
        elif (
            node.parent in self._metas.keys()
            and meta_name not in self._metas[node.parent]
        ):
            self._metas[node.parent][meta_name] = node
        # Otherwise, throw error
        else:
            prev_node = self._metas[node.parent][meta_name]
            error_msg = f'Metadata {meta_name} previously defined at {prev_node.start_point.row}'
            self._raise_analyzer_exception(error_msg)

    def check_category_declaration(
        self, node: Node, data: Tuple[str, Tuple[List, Any]]
    ) -> None:
        """
        Given a category, verify if it has a name and if contains metadata or assets
        """
        _, [[category], assets] = data

        # TODO: is this really needed? doesn't the grammar prevent this?
        if str(category['name']) == '<missing <INVALID>>':
            category_line = node.start_point.row
            logging.error(f'Category has no name at line {category_line}')
            self._error = True
            return

        if len(category['meta']) == 0 and len(assets) == 0:
            logging.warning(
                f"Category '{category['name']}' contains no assets or metadata"
            )

        self._category[category['name']] = {
            'node': node,
            'obj': {'category': category, 'assets': assets},
        }

    def check_define_declaration(self, node: Node, data: Tuple[str, dict]) -> None:
        """
        Given a new define, verify if it has been previously defined
        """
        _, obj = data
        key, value = list(obj.items())[0]

        # ID and version can be defined multiple times
        if key != 'id' and key != 'version' and key in self._defines.keys():
            prev_define_line = self._defines[key]['node'].start_point.row
            error_msg = f"Define '{key}' previously defined at line {prev_define_line}"
            self._raise_analyzer_exception(error_msg)

        self._defines[key] = {'node': node, 'value': value}

    def check_include_declaration(self, node: Node, data: Tuple[str, str]) -> None:
        """
        When an include is found, it triggers the analysis of a new MAL file. To prevent
        checkMal from being performed before all files have been analysed, we increment
        the variable and, every time the file is finished being analysed, it is decreased
        again (in checkMal()). This prevents out-of-order analysis.
        """
        self._preform_post_analysis += 1

        include_file_node = node.child_by_field_name('file')
        assert include_file_node, 'Need include file node'
        assert include_file_node.text, 'Include needs text'
        include_file = include_file_node.text.decode()
        if include_file in self._include_stack:
            cycle = (
                '->'.join([file.replace('"', '') for file in self._include_stack])
                + ' -> '
                + include_file.replace('"', '')
            )
            error_msg = f'Include sequence contains cycle: {cycle}'
            self._raise_analyzer_exception(error_msg)
        self._include_stack.append(include_file)

    def check_attack_step(self, node: Node, step: dict) -> None:
        """
        Given a step, check if it is already defined in the current asset. Otherwise, add it to the list of
        steps related to this asset
        """
        _, step = step

        step_name = step['name']
        assert node.parent and node.parent.parent
        asset_name_node = node.parent.parent.child_by_field_name('id')
        assert asset_name_node and asset_name_node.text, 'Asset name node needs text'
        asset_name = asset_name_node.text.decode()

        # Check if asset has no steps
        if asset_name not in self._steps.keys():
            self._steps[asset_name] = {step_name: {'node': node, 'step': step}}
        # If so, check if the there is no step with this name in the current asset
        elif step_name not in self._steps[asset_name].keys():
            self._steps[asset_name][step_name] = {'node': node, 'step': step}
        # Otherwise, log error
        else:
            prev_node = self._steps[asset_name][step_name]['node']
            error_msg = f"Attack step '{step_name}' previously defined at {prev_node.start_point.row}"
            self._raise_analyzer_exception(error_msg)

        self._validate_CIA(node, step)
        self._validate_TTC(node, asset_name, step)

    def _validate_CIA(self, node: Node, step: dict) -> None:
        """
        Given a step, check if it has CIAs. In that case, verify if the step is not of type
        defense and that it does not have repeated CIAs.
        """
        if not node.child_by_field_name('cias'):
            return

        step_name = step['name']
        assert node.parent and node.parent.parent
        asset_name_node = node.parent.parent.child_by_field_name('id')
        assert asset_name_node and asset_name_node.text, 'Asset name node needs text'
        asset_name = asset_name_node.text.decode()

        if (
            step['type'] == 'defense'
            or step['type'] == 'exist'
            or step['type'] == 'notExist'
        ):
            error_msg = f'Line {node.start_point.row}: {step["type"]}: Defenses cannot have CIA classifications'
            self._raise_analyzer_exception(error_msg)

        cias = []

        # Get the CIAs node and iterate over the individual CIA
        cias_node = node.child_by_field_name('cias')
        assert cias_node, 'Need CIA node'
        for cia in cias_node.named_children:
            assert cia.text, 'CIA node need text'
            letter = cia.text.decode()

            if letter in cias:
                logging.warning(
                    f'Attack step {asset_name}.{step_name} contains duplicate classification {letter}'
                )
                self._warn = True
                return
            cias.append(letter)

    def _validate_TTC(self, node: Node, asset_name, step: dict) -> None:
        if not step['ttc']:
            return
        match step['type']:
            case 'defense':
                if step['ttc']['type'] != 'function':
                    error_msg = f'Defense {asset_name}.{step["name"]} may not have advanced TTC expressions'
                    self._raise_analyzer_exception(error_msg)

                match step['ttc']['name']:
                    case 'Enabled' | 'Disabled' | 'Bernoulli':
                        try:
                            Distributions.validate(
                                step['ttc']['name'], step['ttc']['arguments']
                            )
                        except DistributionsException as e:
                            self._raise_analyzer_exception(e._error_message)
                    case _:
                        error_msg = f"Defense {asset_name}.{step['name']} may only have 'Enabled', 'Disabled', or 'Bernoulli(p)' as TTC"
                        self._raise_analyzer_exception(error_msg)
            case 'exist' | 'notExist':
                # This should log error, but it happens later in the code
                pass
            case _:
                self._check_TTC_expr(step['ttc'])

    def _check_TTC_expr(self, expr, isSubDivExp=False):
        match expr['type']:
            case 'subtraction' | 'exponentiation' | 'division':
                self._check_TTC_expr(expr['lhs'], True)
                self._check_TTC_expr(expr['rhs'], True)
            case 'multiplication' | 'addition':
                self._check_TTC_expr(expr['lhs'], False)
                self._check_TTC_expr(expr['rhs'], False)
            case 'function':
                if expr['name'] in ['Enabled', 'Disabled']:
                    error_msg = "Distributions 'Enabled' or 'Disabled' may not be used as TTC values in '&' and '|' attack steps"
                    self._raise_analyzer_exception(error_msg)
                if isSubDivExp and expr['name'] in ['Bernoulli', 'EasyAndUncertain']:
                    error_msg = f"TTC distribution '{expr['name']}' is not available in subtraction, division or exponential expressions."
                    self._raise_analyzer_exception(error_msg)
                try:
                    Distributions.validate(expr['name'], expr['arguments'])
                except DistributionsException as e:
                    self._raise_analyzer_exception(e._error_message)
            case 'number':
                # Always ok
                pass
            case _:
                error_msg = f'Unexpected expression {expr}'
                self._raise_analyzer_exception(error_msg)

    def check_association(self, node: Node, association: dict):
        self._all_associations.append(
            {'name': association['name'], 'association': association, 'node': node}
        )

    def check_asset_variable(self, node: Node, var: dict) -> None:
        """
        This checks if the variable has been defined in the current asset.

        self._vars = {
            <asset-name>: {
                <var-name>: {'node': <var-node>, 'var' <var-dict>}
            }
        }
        """
        _, var = var

        assert node.parent, 'Asset variable needs a parent'
        parent = node.parent.parent  # Twice to skip asset_definition

        assert parent, 'Asset variable needs a parent'
        asset_name_node = parent.child_by_field_name('id')

        assert asset_name_node, 'Asset needs name node'
        assert asset_name_node.text, 'Asset name node needs text'

        asset_name: str = str(asset_name_node.text.decode())
        var_name: str = var['name']
        if asset_name not in self._vars.keys():
            self._vars[asset_name] = {var_name: {'node': node, 'var': var}}
        elif var_name not in self._vars[asset_name]:
            self._vars[asset_name][var_name] = {'node': node, 'var': var}
        else:
            prev_define_line = self._vars[asset_name][var_name]['node'].start_point.row
            error_msg = (
                f"Variable '{var_name}' previously defined at line {prev_define_line}"
            )
            self._raise_analyzer_exception(error_msg)
