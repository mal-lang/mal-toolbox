"""MAL-Toolbox Language Graph functionality
- A graph representation of a MAL language
- Used when creating models and when generating attack graphs
"""

from __future__ import annotations

import json
import logging
import zipfile
from typing import Any

from maltoolbox.file_utils import (
    load_dict_from_json_file,
    load_dict_from_yaml_file,
    save_dict_to_file,
)
from maltoolbox.language.detector import Context, Detector
from maltoolbox.language.expression_chain import ExpressionsChain
from maltoolbox.language.languagegraph_asset import LanguageGraphAsset
from maltoolbox.language.languagegraph_assoc import LanguageGraphAssociation, LanguageGraphAssociationField
from maltoolbox.language.languagegraph_attack_step import LanguageGraphAttackStep

from ..exceptions import (
    LanguageGraphAssociationError,
    LanguageGraphException,
    LanguageGraphStepExpressionError,
    LanguageGraphSuperAssetNotFoundError,
)
from .compiler import MalCompiler

logger = logging.getLogger(__name__)


def disaggregate_attack_step_full_name(
    attack_step_full_name: str
) -> list[str]:
    """From an attack step full name, get (asset_name, attack_step_name)"""
    return attack_step_full_name.split(':')

class LanguageGraph:
    """Graph representation of a MAL language"""

    def __init__(self, lang: dict | None = None):
        self.assets: dict[str, LanguageGraphAsset] = {}
        if lang is not None:
            self._lang_spec: dict = lang
            self.metadata = {
                "version": lang["defines"]["version"],
                "id": lang["defines"]["id"],
            }
            self._generate_graph()

    def __repr__(self) -> str:
        return (f'LanguageGraph(id: "{self.metadata.get("id", "N/A")}", '
            f'version: "{self.metadata.get("version", "N/A")}")')

    @classmethod
    def from_mal_spec(cls, mal_spec_file: str) -> LanguageGraph:
        """Create a LanguageGraph from a .mal file (a MAL spec).

        Arguments:
        ---------
        mal_spec_file   -   the path to the .mal file

        """
        logger.info("Loading mal spec %s", mal_spec_file)
        return LanguageGraph(MalCompiler().compile(mal_spec_file))

    @classmethod
    def from_mar_archive(cls, mar_archive: str) -> LanguageGraph:
        """Create a LanguageGraph from a ".mar" archive provided by malc
        (https://github.com/mal-lang/malc).

        Arguments:
        ---------
        mar_archive     -   the path to a ".mar" archive

        """
        logger.info('Loading mar archive %s', mar_archive)
        with zipfile.ZipFile(mar_archive, 'r') as archive:
            langspec = archive.read('langspec.json')
            return LanguageGraph(json.loads(langspec))

    def _to_dict(self):
        """Converts LanguageGraph into a dict"""
        logger.debug(
            'Serializing %s assets.', len(self.assets.items())
        )

        serialized_graph = {'metadata': self.metadata}
        for asset in self.assets.values():
            serialized_graph[asset.name] = asset.to_dict()

        return serialized_graph

    @property
    def associations(self) -> set[LanguageGraphAssociation]:
        """Return all associations in the language graph.
        """
        return {assoc for asset in self.assets.values() for assoc in asset.associations.values()}

    @staticmethod
    def _link_association_to_assets(
        assoc: LanguageGraphAssociation,
        left_asset: LanguageGraphAsset,
        right_asset: LanguageGraphAsset
    ):
        left_asset.own_associations[assoc.right_field.fieldname] = assoc
        right_asset.own_associations[assoc.left_field.fieldname] = assoc

    def save_to_file(self, filename: str) -> None:
        """Save to json/yml depending on extension"""
        return save_dict_to_file(filename, self._to_dict())

    @classmethod
    def _from_dict(cls, serialized_graph: dict) -> LanguageGraph:
        """Rebuild a LanguageGraph instance from its serialized dict form."""
        logger.debug('Create language graph from dictionary.')
        lang_graph = LanguageGraph()
        lang_graph.metadata = serialized_graph.pop('metadata')

        # Create asset nodes
        for asset in serialized_graph.values():
            logger.debug('Create asset %s', asset['name'])
            lang_graph.assets[asset['name']] = LanguageGraphAsset(
                name=asset['name'],
                own_associations={},
                attack_steps={},
                info=asset['info'],
                own_super_asset=None,
                own_sub_assets=list(),
                own_variables={},
                is_abstract=asset['is_abstract']
            )

        # Link inheritance
        for asset in serialized_graph.values():
            asset_node = lang_graph.assets[asset['name']]
            if super_name := asset['super_asset']:
                try:
                    super_asset = lang_graph.assets[super_name]
                except KeyError:
                    msg = f'Super asset "{super_name}" for "{asset["name"]}" not found'
                    logger.error(msg)
                    raise LanguageGraphSuperAssetNotFoundError(msg)

                super_asset.own_sub_assets.append(asset_node)
                asset_node.own_super_asset = super_asset

        # Associations
        for asset in serialized_graph.values():
            logger.debug('Create associations for asset %s', asset['name'])
            a_node = lang_graph.assets[asset['name']]
            for assoc in asset['associations'].values():
                try:
                    left = lang_graph.assets[assoc['left']['asset']]
                    right = lang_graph.assets[assoc['right']['asset']]
                except KeyError as e:
                    side = 'Left' if 'left' in str(e) else 'Right'
                    msg = f'{side} asset for association "{assoc["name"]}" not found'
                    logger.error(msg)
                    raise LanguageGraphAssociationError(msg)
                assoc_node = LanguageGraphAssociation(
                    name=assoc['name'],
                    left_field=LanguageGraphAssociationField(
                        left, assoc['left']['fieldname'],
                        assoc['left']['min'], assoc['left']['max']
                    ),
                    right_field=LanguageGraphAssociationField(
                        right, assoc['right']['fieldname'],
                        assoc['right']['min'], assoc['right']['max']
                    ),
                    info=assoc['info']
                )
                lang_graph._link_association_to_assets(assoc_node, left, right)

        # Variables
        for asset in serialized_graph.values():
            a_node = lang_graph.assets[asset['name']]
            for var, (target_name, expr_dict) in asset['variables'].items():
                target = lang_graph.assets[target_name]
                a_node.own_variables[var] = (
                    target, ExpressionsChain._from_dict(expr_dict, lang_graph)
                )

        # Attack steps
        for asset in serialized_graph.values():
            a_node = lang_graph.assets[asset['name']]
            for step in asset['attack_steps'].values():
                a_node.attack_steps[step['name']] = LanguageGraphAttackStep(
                    name=step['name'],
                    type=step['type'],
                    asset=a_node,
                    causal_mode=step.get('causal_mode'),
                    ttc=step['ttc'],
                    overrides=step['overrides'],
                    own_children={}, own_parents={},
                    info=step['info'],
                    tags=list(step['tags'])
                )

        # Inheritance for attack steps
        for asset in serialized_graph.values():
            a_node = lang_graph.assets[asset['name']]
            for step in asset['attack_steps'].values():
                if not (inh := step.get('inherits')):
                    continue
                a_step = a_node.attack_steps[step['name']]
                a_name, s_name = disaggregate_attack_step_full_name(inh)
                a_step.inherits = lang_graph.assets[a_name].attack_steps[s_name]

        # Expression chains and requirements
        for asset in serialized_graph.values():
            a_node = lang_graph.assets[asset['name']]
            for step in asset['attack_steps'].values():
                s_node = a_node.attack_steps[step['name']]
                for tgt_name, exprs in step['own_children'].items():
                    t_asset, t_step = disaggregate_attack_step_full_name(tgt_name)
                    t_node = lang_graph.assets[t_asset].attack_steps[t_step]
                    for expr in exprs:
                        chain = ExpressionsChain._from_dict(expr, lang_graph)
                        s_node.own_children.setdefault(t_node, []).append(chain)
                for tgt_name, exprs in step['own_parents'].items():
                    t_asset, t_step = disaggregate_attack_step_full_name(tgt_name)
                    t_node = lang_graph.assets[t_asset].attack_steps[t_step]
                    for expr in exprs:
                        chain = ExpressionsChain._from_dict(expr, lang_graph)
                        s_node.own_parents.setdefault(t_node, []).append(chain)
                if step['type'] in ('exist', 'notExist') and (reqs := step.get('requires')):
                    s_node.own_requires = [
                        chain for expr in reqs
                        if (chain := ExpressionsChain._from_dict(expr, lang_graph))
                    ]

        return lang_graph

    @classmethod
    def load_from_file(cls, filename: str) -> LanguageGraph:
        """Create LanguageGraph from mal, mar, yaml or json"""
        lang_graph = None
        if filename.endswith('.mal'):
            lang_graph = cls.from_mal_spec(filename)
        elif filename.endswith('.mar'):
            lang_graph = cls.from_mar_archive(filename)
        elif filename.endswith(('.yaml', '.yml')):
            lang_graph = cls._from_dict(load_dict_from_yaml_file(filename))
        elif filename.endswith('.json'):
            lang_graph = cls._from_dict(load_dict_from_json_file(filename))
        else:
            raise TypeError(
                "Unknown file extension, expected json/mal/mar/yml/yaml"
            )

        if lang_graph:
            return lang_graph
        raise LanguageGraphException(
            f'Failed to load language graph from file "{filename}".'
        )

    def save_language_specification_to_json(self, filename: str) -> None:
        """Save a MAL language specification dictionary to a JSON file

        Arguments:
        ---------
        filename        - the JSON filename where the language specification will be written

        """
        logger.info('Save language specification to %s', filename)

        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(self._lang_spec, file, indent=4)

    def process_attack_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any]
    ) -> tuple[
                LanguageGraphAsset,
                None,
                str
            ]:
        """The attack step expression just adds the name of the attack
        step. All other step expressions only modify the target
        asset and parent associations chain.
        """
        return (
            target_asset,
            None,
            step_expression['name']
        )

    def process_set_operation_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """The set operators are used to combine the left hand and right
        hand targets accordingly.
        """
        lh_target_asset, lh_expr_chain, _ = self.process_step_expression(
            target_asset,
            expr_chain,
            step_expression['lhs']
        )
        rh_target_asset, rh_expr_chain, _ = self.process_step_expression(
            target_asset,
            expr_chain,
            step_expression['rhs']
        )

        assert lh_target_asset, (
            f"No lh target in step expression {step_expression}"
        )
        assert rh_target_asset, (
            f"No rh target in step expression {step_expression}"
        )

        if not lh_target_asset.get_all_common_superassets(rh_target_asset):
            raise ValueError(
                "Set operation attempted between targets that do not share "
                f"any common superassets: {lh_target_asset.name} "
                f"and {rh_target_asset.name}!"
            )

        new_expr_chain = ExpressionsChain(
            type=step_expression['type'],
            left_link=lh_expr_chain,
            right_link=rh_expr_chain
        )
        return (
            lh_target_asset,
            new_expr_chain,
            None
        )

    def process_variable_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:

        var_name = step_expression['name']
        var_target_asset, var_expr_chain = (
            self._resolve_variable(target_asset, var_name)
        )

        if var_expr_chain is None:
            raise LookupError(
                f'Failed to find variable "{step_expression["name"]}" '
                f'for {target_asset.name}',
            )

        return (
            var_target_asset,
            var_expr_chain,
            None
        )

    def process_field_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """Change the target asset from the current one to the associated
        asset given the specified field name and add the parent
        fieldname and association to the parent associations chain.
        """
        fieldname = step_expression['name']

        if target_asset is None:
            raise ValueError(
                f'Missing target asset for field "{fieldname}"!'
            )

        new_target_asset = None
        for association in target_asset.associations.values():
            if (association.left_field.fieldname == fieldname and
                target_asset.is_subasset_of(
                    association.right_field.asset)):
                new_target_asset = association.left_field.asset

            if (association.right_field.fieldname == fieldname and
                target_asset.is_subasset_of(
                    association.left_field.asset)):
                new_target_asset = association.right_field.asset

            if new_target_asset:
                new_expr_chain = ExpressionsChain(
                    type='field',
                    fieldname=fieldname,
                    association=association
                )
                return (
                    new_target_asset,
                    new_expr_chain,
                    None
                )

        raise LookupError(
            f'Failed to find field {fieldname} on asset {target_asset.name}!',
        )

    def process_transitive_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """Create a transitive tuple entry that applies to the next
        component of the step expression.
        """
        result_target_asset, result_expr_chain, _ = (
            self.process_step_expression(
                target_asset,
                expr_chain,
                step_expression['stepExpression']
            )
        )
        new_expr_chain = ExpressionsChain(
            type='transitive',
            sub_link=result_expr_chain
        )
        return (
            result_target_asset,
            new_expr_chain,
            None
        )

    def process_subType_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """Create a subType tuple entry that applies to the next
        component of the step expression and changes the target
        asset to the subasset.
        """
        subtype_name = step_expression['subType']
        result_target_asset, result_expr_chain, _ = (
            self.process_step_expression(
                target_asset,
                expr_chain,
                step_expression['stepExpression']
            )
        )

        if subtype_name not in self.assets:
            raise LanguageGraphException(
                f'Failed to find subtype {subtype_name}'
            )

        subtype_asset = self.assets[subtype_name]

        if result_target_asset is None:
            raise LookupError("Nonexisting asset for subtype")

        if not subtype_asset.is_subasset_of(result_target_asset):
            raise ValueError(
                f'Found subtype {subtype_name} which does not extend '
                f'{result_target_asset.name}, subtype cannot be resolved.'
            )

        new_expr_chain = ExpressionsChain(
            type='subType',
            sub_link=result_expr_chain,
            subtype=subtype_asset
        )
        return (
            subtype_asset,
            new_expr_chain,
            None
        )

    def process_collect_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain | None,
            str | None
        ]:
        """Apply the right hand step expression to left hand step
        expression target asset and parent associations chain.
        """
        lh_target_asset, lh_expr_chain, _ = self.process_step_expression(
            target_asset, expr_chain, step_expression['lhs']
        )

        if lh_target_asset is None:
            raise ValueError(
                'No left hand asset in collect expression '
                f'{step_expression["lhs"]}'
            )

        rh_target_asset, rh_expr_chain, rh_attack_step_name = (
            self.process_step_expression(
                lh_target_asset, None, step_expression['rhs']
            )
        )

        new_expr_chain = lh_expr_chain
        if rh_expr_chain:
            new_expr_chain = ExpressionsChain(
                type='collect',
                left_link=lh_expr_chain,
                right_link=rh_expr_chain
            )

        return (
            rh_target_asset,
            new_expr_chain,
            rh_attack_step_name
        )

    def process_step_expression(self,
            target_asset: LanguageGraphAsset,
            expr_chain: ExpressionsChain | None,
            step_expression: dict
        ) -> tuple[
                LanguageGraphAsset,
                ExpressionsChain | None,
                str | None
            ]:
        """Recursively process an attack step expression.

        Arguments:
        ---------
        target_asset        - The asset type that this step expression should
                              apply to. Initially it will contain the asset
                              type to which the attack step belongs.
        expr_chain          - A expressions chain of linked of associations
                              and set operations from the attack step to its
                              parent attack step.
                              Note: This was done for the parent attack step
                              because it was easier to construct recursively
                              given the left-hand first expansion of the
                              current MAL language specification.
        step_expression     - A dictionary containing the step expression.

        Return:
        ------
        A tuple triplet containing the target asset, the resulting parent
        associations chain, and the name of the attack step.

        """
        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(
                'Processing Step Expression:\n%s',
                json.dumps(step_expression, indent=2)
            )

        result: tuple[
            LanguageGraphAsset,
            ExpressionsChain | None,
            str | None
        ]

        match (step_expression['type']):
            case 'attackStep':
                result = self.process_attack_step_expression(
                    target_asset, step_expression
                )
            case 'union' | 'intersection' | 'difference':
                result = self.process_set_operation_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case 'variable':
                result = self.process_variable_step_expression(
                    target_asset, step_expression
                )
            case 'field':
                result = self.process_field_step_expression(
                    target_asset, step_expression
                )
            case 'transitive':
                result = self.process_transitive_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case 'subType':
                result = self.process_subType_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case 'collect':
                result = self.process_collect_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case _:
                raise LookupError(
                    f'Unknown attack step type: "{step_expression["type"]}"'
                )
        return result

    def reverse_expr_chain(
            self,
            expr_chain: ExpressionsChain | None,
            reverse_chain: ExpressionsChain | None
        ) -> ExpressionsChain | None:
        """Recursively reverse the associations chain. From parent to child or
        vice versa.

        Arguments:
        ---------
        expr_chain          - A chain of nested tuples that specify the
                              associations and set operations chain from an
                              attack step to its connected attack step.
        reverse_chain       - A chain of nested tuples that represents the
                              current reversed associations chain.

        Return:
        ------
        The resulting reversed associations chain.

        """
        if not expr_chain:
            return reverse_chain
        match (expr_chain.type):
            case 'union' | 'intersection' | 'difference' | 'collect':
                left_reverse_chain = \
                    self.reverse_expr_chain(expr_chain.left_link,
                    reverse_chain)
                right_reverse_chain = \
                    self.reverse_expr_chain(expr_chain.right_link,
                    reverse_chain)
                if expr_chain.type == 'collect':
                    new_expr_chain = ExpressionsChain(
                        type=expr_chain.type,
                        left_link=right_reverse_chain,
                        right_link=left_reverse_chain
                    )
                else:
                    new_expr_chain = ExpressionsChain(
                        type=expr_chain.type,
                        left_link=left_reverse_chain,
                        right_link=right_reverse_chain
                    )

                return new_expr_chain

            case 'transitive':
                result_reverse_chain = self.reverse_expr_chain(
                    expr_chain.sub_link, reverse_chain)
                new_expr_chain = ExpressionsChain(
                    type='transitive',
                    sub_link=result_reverse_chain
                )
                return new_expr_chain

            case 'field':
                association = expr_chain.association

                if not association:
                    raise LanguageGraphException(
                        "Missing association for expressions chain"
                    )

                if not expr_chain.fieldname:
                    raise LanguageGraphException(
                        "Missing field name for expressions chain"
                    )

                opposite_fieldname = association.get_opposite_fieldname(
                    expr_chain.fieldname)
                new_expr_chain = ExpressionsChain(
                    type='field',
                    association=association,
                    fieldname=opposite_fieldname
                )
                return new_expr_chain

            case 'subType':
                result_reverse_chain = self.reverse_expr_chain(
                    expr_chain.sub_link,
                    reverse_chain
                )
                new_expr_chain = ExpressionsChain(
                    type='subType',
                    sub_link=result_reverse_chain,
                    subtype=expr_chain.subtype
                )
                return new_expr_chain

            case _:
                msg = 'Unknown assoc chain element "%s"'
                logger.error(msg, expr_chain.type)
                raise LanguageGraphAssociationError(msg % expr_chain.type)

    def _resolve_variable(self, asset: LanguageGraphAsset, var_name) -> tuple:
        """Resolve a variable for a specific asset by variable name.

        Arguments:
        ---------
        asset       - a language graph asset to which the variable belongs
        var_name    - a string representing the variable name

        Return:
        ------
        A tuple containing the target asset and expressions chain required to
        reach it.

        """
        if var_name not in asset.variables:
            var_expr = self._get_var_expr_for_asset(asset.name, var_name)
            target_asset, expr_chain, _ = self.process_step_expression(
                asset,
                None,
                var_expr
            )
            asset.own_variables[var_name] = (target_asset, expr_chain)
            return (target_asset, expr_chain)
        return asset.variables[var_name]

    def _create_associations_for_assets(
            self,
            lang_spec: dict[str, Any],
            assets: dict[str, LanguageGraphAsset]
        ) -> None:
        """Link associations to assets based on the language specification.

        Arguments:
        ---------
        lang_spec   - the language specification dictionary
        assets      - a dictionary of LanguageGraphAsset objects
                      indexed by their names

        """
        for association_dict in lang_spec['associations']:
            logger.debug(
                'Create association language graph nodes for association %s',
                association_dict['name']
            )

            left_asset_name = association_dict['leftAsset']
            right_asset_name = association_dict['rightAsset']

            if left_asset_name not in assets:
                raise LanguageGraphAssociationError(
                    f'Left asset "{left_asset_name}" for '
                    f'association "{association_dict["name"]}" not found!'
                )
            if right_asset_name not in assets:
                raise LanguageGraphAssociationError(
                    f'Right asset "{right_asset_name}" for '
                    f'association "{association_dict["name"]}" not found!'
                )

            left_asset = assets[left_asset_name]
            right_asset = assets[right_asset_name]

            assoc_node = LanguageGraphAssociation(
                name=association_dict['name'],
                left_field=LanguageGraphAssociationField(
                    left_asset,
                    association_dict['leftField'],
                    association_dict['leftMultiplicity']['min'],
                    association_dict['leftMultiplicity']['max']
                ),
                right_field=LanguageGraphAssociationField(
                    right_asset,
                    association_dict['rightField'],
                    association_dict['rightMultiplicity']['min'],
                    association_dict['rightMultiplicity']['max']
                ),
                info=association_dict['meta']
            )

            # Add the association to the left and right asset
            self._link_association_to_assets(
                assoc_node, left_asset, right_asset
            )

    def _link_assets(
            self,
            lang_spec: dict[str, Any],
            assets: dict[str, LanguageGraphAsset]
        ) -> None:
        """Link assets based on inheritance and associations.
        """
        for asset_dict in lang_spec['assets']:
            asset = assets[asset_dict['name']]
            if asset_dict['superAsset']:
                super_asset = assets[asset_dict['superAsset']]
                if not super_asset:
                    msg = 'Failed to find super asset "%s" for asset "%s"!'
                    logger.error(
                        msg, asset_dict["superAsset"], asset_dict["name"])
                    raise LanguageGraphSuperAssetNotFoundError(
                        msg % (asset_dict["superAsset"], asset_dict["name"]))

                super_asset.own_sub_assets.append(asset)
                asset.own_super_asset = super_asset

    def _set_variables_for_assets(
            self, assets: dict[str, LanguageGraphAsset]
        ) -> None:
        """Set the variables for each asset based on the language specification.

        Arguments:
        ---------
        assets      - a dictionary of LanguageGraphAsset objects
                      indexed by their names

        """
        for asset in assets.values():
            logger.debug(
                'Set variables for asset %s', asset.name
            )
            variables = self._get_variables_for_asset_type(asset.name)
            for variable in variables:
                if logger.isEnabledFor(logging.DEBUG):
                    # Avoid running json.dumps when not in debug
                    logger.debug(
                        'Processing Variable Expression:\n%s',
                        json.dumps(variable, indent=2)
                    )
                self._resolve_variable(asset, variable['name'])

    def _generate_attack_steps(self, assets) -> None:
        """
        Generate attack steps for all assets and link them according to the
        language specification.

        This method performs three phases:

        1. Create attack step nodes for each asset, including detectors.
        2. Inherit attack steps from super-assets, respecting overrides.
        3. Link attack steps via 'reaches' and evaluate 'exist'/'notExist'
        requirements.

        Args:
            assets (dict): Mapping of asset names to asset objects.

        Raises:
            LanguageGraphStepExpressionError: If a step expression cannot be
                resolved to a target asset or attack step.
            LanguageGraphException: If an existence requirement cannot be
                resolved.
        """
        langspec_dict = {}

        for asset in assets.values():
            logger.debug('Create attack steps language graph nodes for asset %s', asset.name)
            for step_dict in self._get_attacks_for_asset_type(asset.name).values():
                logger.debug(
                    'Create attack step language graph nodes for %s', step_dict['name']
                )
                node = LanguageGraphAttackStep(
                    name=step_dict['name'],
                    type=step_dict['type'],
                    asset=asset,
                    causal_mode=step_dict.get('causal_mode'),
                    ttc=step_dict['ttc'],
                    overrides=(
                        step_dict['reaches']['overrides']
                        if step_dict['reaches'] else False
                    ),
                    own_children={}, own_parents={},
                    info=step_dict['meta'],
                    tags=list(step_dict['tags'])
                )
                langspec_dict[node.full_name] = step_dict
                asset.attack_steps[node.name] = node

                for det in step_dict.get('detectors', {}).values():
                    node.detectors[det['name']] = Detector(
                        context=Context(
                            {lbl: assets[a] for lbl, a in det['context'].items()}
                        ),
                        name=det.get('name'),
                        type=det.get('type'),
                        tprate=det.get('tprate'),
                    )

        pending = list(self.assets.values())
        while pending:
            asset = pending.pop(0)
            super_asset = asset.own_super_asset
            if super_asset in pending:
                # Super asset still needs processing, defer this asset
                pending.append(asset)
                continue
            if not super_asset:
                continue
            for super_step in super_asset.attack_steps.values():
                current_step = asset.attack_steps.get(super_step.name)
                if not current_step:
                    node = LanguageGraphAttackStep(
                        name=super_step.name,
                        type=super_step.type,
                        asset=asset,
                        causal_mode=step_dict.get('causal_mode'),
                        ttc=super_step.ttc,
                        overrides=False,
                        own_children={},
                        own_parents={},
                        info=super_step.info,
                        tags=list(super_step.tags)
                    )
                    node.inherits = super_step
                    asset.attack_steps[super_step.name] = node
                elif current_step.overrides:
                    continue
                else:
                    current_step.inherits = super_step
                    current_step.tags += super_step.tags
                    current_step.info |= super_step.info

        for asset in self.assets.values():
            for step in asset.attack_steps.values():
                logger.debug('Determining children for attack step %s', step.name)
                if step.full_name not in langspec_dict:
                    continue

                entry = langspec_dict[step.full_name]
                for expr in (entry['reaches']['stepExpressions'] if entry['reaches'] else []):
                    tgt_asset, chain, tgt_name = self.process_step_expression(step.asset, None, expr)
                    if not tgt_asset:
                        raise LanguageGraphStepExpressionError(
                            'Failed to find target asset for:\n%s' % json.dumps(expr, indent=2)
                        )
                    if tgt_name not in tgt_asset.attack_steps:
                        raise LanguageGraphStepExpressionError(
                            'Failed to find target attack step %s on %s:\n%s' %
                            (tgt_name, tgt_asset.name, json.dumps(expr, indent=2))
                        )

                    tgt = tgt_asset.attack_steps[tgt_name]
                    step.own_children.setdefault(tgt, []).append(chain)
                    tgt.own_parents.setdefault(step, []).append(self.reverse_expr_chain(chain, None))

                if step.type in ('exist', 'notExist'):
                    reqs = entry['requires']['stepExpressions'] if entry['requires'] else []
                    if not reqs:
                        raise LanguageGraphStepExpressionError(
                            'Missing requirements for "%s" of type "%s":\n%s' %
                            (step.name, step.type, json.dumps(entry, indent=2))
                        )
                    for expr in reqs:
                        _, chain, _ = self.process_step_expression(step.asset, None, expr)
                        if chain is None:
                            raise LanguageGraphException(
                                f'Failed to find existence step requirement for:\n{expr}'
                            )
                        step.own_requires.append(chain)

    def _generate_graph(self) -> None:
        """Generate language graph starting from the MAL language specification
        given in the constructor.
        """
        # Generate all of the asset nodes of the language graph.
        self.assets = {}
        for asset_dict in self._lang_spec['assets']:
            logger.debug(
                'Create asset language graph nodes for asset %s',
                asset_dict['name']
            )
            asset_node = LanguageGraphAsset(
                name=asset_dict['name'],
                own_associations={},
                attack_steps={},
                info=asset_dict['meta'],
                own_super_asset=None,
                own_sub_assets=list(),
                own_variables={},
                is_abstract=asset_dict['isAbstract']
            )
            self.assets[asset_dict['name']] = asset_node

        # Link assets to each other
        self._link_assets(self._lang_spec, self.assets)

        # Add and link associations to assets
        self._create_associations_for_assets(self._lang_spec, self.assets)

        # Set the variables for each asset
        self._set_variables_for_assets(self.assets)

        # Add attack steps to the assets
        self._generate_attack_steps(self.assets)

    def _get_attacks_for_asset_type(self, asset_type: str) -> dict[str, dict]:
        """Get all Attack Steps for a specific asset type.

        Arguments:
        ---------
        asset_type      - the name of the asset type we want to
                          list the possible attack steps for

        Return:
        ------
        A dictionary containing the possible attacks for the
        specified asset type. Each key in the dictionary is an attack name
        associated with a dictionary containing other characteristics of the
        attack such as type of attack, TTC distribution, child attack steps
        and other information

        """
        attack_steps: dict = {}
        try:
            asset = next(
                asset for asset in self._lang_spec['assets']
                    if asset['name'] == asset_type
            )
        except StopIteration:
            logger.error(
                'Failed to find asset type %s when looking'
                'for attack steps.', asset_type
            )
            return attack_steps

        logger.debug(
            'Get attack steps for %s asset from '
            'language specification.', asset['name']
        )

        attack_steps = {step['name']: step for step in asset['attackSteps']}

        return attack_steps

    def _get_associations_for_asset_type(self, asset_type: str) -> list[dict]:
        """Get all associations for a specific asset type.

        Arguments:
        ---------
        asset_type      - the name of the asset type for which we want to
                          list the associations

        Return:
        ------
        A list of dicts, where each dict represents an associations
        for the specified asset type. Each dictionary contains
        name and meta information about the association.

        """
        logger.debug(
            'Get associations for %s asset from '
            'language specification.', asset_type
        )
        associations: list = []

        asset = next((asset for asset in self._lang_spec['assets']
            if asset['name'] == asset_type), None)
        if not asset:
            logger.error(
                'Failed to find asset type %s when '
                'looking for associations.', asset_type
            )
            return associations

        assoc_iter = (assoc for assoc in self._lang_spec['associations']
            if assoc['leftAsset'] == asset_type or
                assoc['rightAsset'] == asset_type)
        assoc = next(assoc_iter, None)
        while assoc:
            associations.append(assoc)
            assoc = next(assoc_iter, None)

        return associations

    def _get_variables_for_asset_type(
            self, asset_type: str) -> list[dict]:
        """Get variables for a specific asset type.
        Note: Variables are the ones specified in MAL through `let` statements

        Arguments:
        ---------
        asset_type      - a string representing the asset type which
                          contains the variables

        Return:
        ------
        A list of dicts representing the step expressions for the variables
        belonging to the asset.

        """
        asset_dict = next((asset for asset in self._lang_spec['assets']
            if asset['name'] == asset_type), None)
        if not asset_dict:
            msg = 'Failed to find asset type %s in language specification '\
                'when looking for variables.'
            logger.error(msg, asset_type)
            raise LanguageGraphException(msg % asset_type)

        return asset_dict['variables']

    def _get_var_expr_for_asset(
            self, asset_type: str, var_name) -> dict:
        """Get a variable for a specific asset type by variable name.

        Arguments:
        ---------
        asset_type      - a string representing the type of asset which
                          contains the variable
        var_name        - a string representing the variable name

        Return:
        ------
        A dictionary representing the step expression for the variable.

        """
        vars_dict = self._get_variables_for_asset_type(asset_type)

        var_expr = next((var_entry['stepExpression'] for var_entry
            in vars_dict if var_entry['name'] == var_name), None)

        if not var_expr:
            msg = 'Failed to find variable name "%s" in language '\
                'specification when looking for variables for "%s" asset.'
            logger.error(msg, var_name, asset_type)
            raise LanguageGraphException(msg % (var_name, asset_type))
        return var_expr

    def regenerate_graph(self) -> None:
        """Regenerate language graph starting from the MAL language specification
        given in the constructor.
        """
        self.assets = {}
        self._generate_graph()
