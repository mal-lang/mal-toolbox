"""
MAL-Toolbox Attack Graph Module
"""

import logging
import json

from typing import Optional

from .node import AttackGraphNode
from .attacker import Attacker
from ..exceptions import AttackGraphStepExpressionError
from ..language import specification
from ..model import Model

logger = logging.getLogger(__name__)

def _process_step_expression(lang: dict, model: Model,
    target_assets: list, step_expression: dict):
    """
    Recursively process an attack step expression.

    Arguments:
    lang            - a dictionary representing the MAL language specification
    model           - a maltoolbox.model.Model instance from which the attack
                      graph was generated
    target_assets   - the list of assets that this step expression should apply
                      to. Initially it will contain the asset to which the
                      attack step belongs
    step_expression - a dictionary containing the step expression

    Return:
    A tuple pair containing a list of all of the target assets and the name of
    the attack step.
    """
    logger.debug('Processing Step Expression:\n' \
        + json.dumps(step_expression, indent = 2))

    match (step_expression['type']):
        case 'attackStep':
            # The attack step expression just adds the name of the attack
            # step. All other step expressions only modify the target assets.
            return (target_assets, step_expression['name'])

        case 'union' | 'intersection' | 'difference':
            # The set operators are used to combine the left hand and right
            # hand targets accordingly.
            lh_targets, lh_attack_steps = _process_step_expression(
                lang, model, target_assets, step_expression['lhs'])
            rh_targets, rh_attack_steps = _process_step_expression(
                lang, model, target_assets, step_expression['rhs'])

            new_target_assets = []
            match (step_expression['type']):
                case 'union':
                    new_target_assets = lh_targets
                    for ag_node in rh_targets:
                        if next((lnode for lnode in new_target_assets \
                            if lnode.id != ag_node.id), None):
                            new_target_assets.append(ag_node)

                case 'intersection':
                    for ag_node in rh_targets:
                        if next((lnode for lnode in new_target_assets \
                            if lnode.id == ag_node.id), None):
                            new_target_assets.append(ag_node)

                case 'difference':
                    new_target_assets = lh_targets
                    for ag_node in lh_targets:
                        if next((rnode for rnode in rh_targets \
                            if rnode.id != ag_node.id), None):
                            new_target_assets.remove(ag_node)

            return (new_target_assets, None)

        case 'variable':
            # Fetch the step expression associated with the variable from
            # the language specification and resolve that.
            for target_asset in target_assets:
                if (hasattr(target_asset, 'metaconcept')):
                    variable_step_expr = specification.\
                        get_variable_for_class_by_name(lang,
                        target_asset.metaconcept, step_expression['name'])
                    return _process_step_expression(
                        lang, model, target_assets, variable_step_expr)

                else:
                    logger.error('Requested variable from non-asset'
                        f'target node: {target_asset} which cannot be'
                        'resolved.')
            return ([], None)

        case 'field':
            # Change the target assets from the current ones to the associated
            # assets given the specified field name.
            new_target_assets = []
            for target_asset in target_assets:
                new_target_assets.extend(model.\
                    get_associated_assets_by_field_name(target_asset,
                        step_expression['name']))
            return (new_target_assets, None)

        case 'transitive':
            # The transitive expression is very similar to the field
            # expression, but it proceeds recursively until no target is
            # found and it and it sets the new targets to the entire list
            # of assets identified during the entire transitive recursion.
            new_target_assets = []
            for target_asset in target_assets:
                new_target_assets.extend(model.\
                    get_associated_assets_by_field_name(target_asset,
                        step_expression['stepExpression']['name']))
            if new_target_assets:
                (additional_assets, _) = _process_step_expression(
                    lang, model, new_target_assets, step_expression)
                new_target_assets.extend(additional_assets)
                return (new_target_assets, None)
            else:
                return ([], None)

        case 'subType':
            new_target_assets = []
            for target_asset in target_assets:
                (assets, _) = _process_step_expression(
                    lang, model, target_assets, step_expression['stepExpression'])
                new_target_assets.extend(assets)

            selected_new_target_assets = (asset for asset in \
                new_target_assets if specification.extends_asset(
                    lang,
                    asset.metaconcept,
                    step_expression['subType']))
            return (selected_new_target_assets, None)

        case 'collect':
            # Apply the right hand step expression to left hand step
            # expression target assets.
            lh_targets, _ = _process_step_expression(
                lang, model, target_assets, step_expression['lhs'])
            return _process_step_expression(lang, model, lh_targets,
                step_expression['rhs'])


        case _:
            logger.error('Unknown attack step type: '
                f'{step_expression["type"]}')
            return ([], None)



class AttackGraph:
    def __init__(self, lang_spec = None, model: Optional[Model] = None):
        self.nodes = []
        self.attackers = []
        self.model = model
        self.lang_spec = lang_spec
        if self.model is not None and self.lang_spec is not None:
            self._generate_graph()

    def __repr__(self) -> str:
        return f'AttackGraph({len(self.nodes)} nodes)'

    def save_to_file(self, filename: str):
        """
        Save the attack graph to a json file.

        Arguments:
        filename        - the name of the output file
        """

        logger.info(f'Saving attack graph with {len(self.nodes)} attack step '
            f'nodes to {filename} file.')
        serialized_graph = []
        for ag_node in self.nodes:
            serialized_graph.append(ag_node.to_dict())
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(serialized_graph, file, indent=4)


    def load_from_file(self, filename: str, model: Optional[Model] = None):
        """
        Load the attack graph model from a json file.

        Arguments:
        filename        - the name of the input file to parse
        model           - (optional) the instance model that the attack graph was
                          generated from. If this given then the attack graph node
                          and instance model asset link can be re-established. If
                          this argument is not given the attack graph will still
                          be created it will just omit the links to the assets.
        """

        logger.info(f'Loading attack graph from {filename} file.')
        if model:
            logger.info(f'Model(\'{model.name}\') was provided will attempt '
            'to establish links to assets.')
        else:
            logger.info('No model was provided therefore asset links will '
            'not be established.')

        with open(filename, 'r', encoding='utf-8') as file:
            serialized_graph = json.load(file)
        # Create all of the nodes in the imported attack graph.
        for node_dict in serialized_graph:
            ag_node = AttackGraphNode(
                id=node_dict['id'],
                type=node_dict['type'],
                name=node_dict['name'],
                ttc=node_dict['ttc']
            )

            ag_node.defense_status = float(node_dict['defense_status']) if \
                'defense_status' in node_dict else None
            ag_node.existence_status = node_dict['existence_status'] \
                == 'True' if 'existence_status' in node_dict else None
            ag_node.is_viable = node_dict['is_viable'] == 'True' if \
                'is_viable' in node_dict else True
            ag_node.is_necessary = node_dict['is_necessary'] == 'True' if \
                'is_necessary' in node_dict else True
            ag_node.mitre_info = str(node_dict['mitre_info']) if \
                'mitre_info' in node_dict else None
            ag_node.tags = node_dict['tags'] if \
                'tags' in node_dict else []
            ag_node.reward = float(node_dict['reward']) if \
                'reward' in node_dict else 0.0
            if ag_node.name == 'firstSteps':
                # This is an attacker entry point node, recreate the attacker.
                attacker_id = ag_node.id.split(':')[1]
                ag_attacker = Attacker(
                    id = str(attacker_id),
                    entry_points = [],
                    reached_attack_steps = [],
                    node = ag_node
                )
                self.attackers.append(ag_attacker)
                ag_node.attacker = ag_attacker

            self.nodes.append(ag_node)

        # Re-establish links between nodes.
        for node_dict in serialized_graph:
            _ag_node: Optional[AttackGraphNode] = self.get_node_by_id(node_dict['id'])
            if not isinstance(_ag_node, AttackGraphNode):
                logger.error(f'Failed to find node with id {node_dict["id"]}'
                    f' when loading from attack graph from file {filename}')
            else:
                for child_id in node_dict['children']:
                    child = self.get_node_by_id(child_id)
                    if child is None:
                        logger.error(f'Failed to find child node with id {child_id}'
                            f' when loading from attack graph from file {filename}')
                        return None
                    _ag_node.children.append(child)

                    if isinstance(_ag_node.attacker, Attacker):
                        # Relink the attacker related connections since the node
                        # is an attacker entry point node.
                        ag_attacker = _ag_node.attacker
                        ag_attacker.entry_points.append(child)
                        ag_attacker.compromise(child)

                for parent_id in node_dict['parents']:
                    parent = self.get_node_by_id(parent_id)
                    if parent is None:
                        logger.error('Failed to find parent node with id '
                            f'{parent_id} when loading from attack graph from '
                            f'file {filename}')
                        return None
                    _ag_node.parents.append(parent)

                # Also recreate asset links if model is available.
                if model and 'asset' in node_dict:
                    asset = model.get_asset_by_id(
                        int(node_dict['asset'].split(':')[1]))
                    if asset is None:
                        logger.error('Failed to find asset with id '
                            f'{node_dict["asset"]} when loading from attack graph '
                            f'from file {filename}')
                        return None
                    _ag_node.asset = asset
                    if hasattr(asset, 'attack_step_nodes'):
                        attack_step_nodes = list(asset.attack_step_nodes)
                        attack_step_nodes.append(_ag_node)
                        asset.attack_step_nodes = attack_step_nodes
                    else:
                        asset.attack_step_nodes = [_ag_node]


    def get_node_by_id(self, node_id: str) -> Optional[AttackGraphNode]:
        """
        Return the attack node that matches the id provided.

        Arguments:
        node_id     - the id of the attack graph none we are looking for

        Return:
        The attack step node that matches the given id.
        """

        logger.debug(f'Looking up node with id {node_id}')
        return next((ag_node for ag_node in self.nodes \
            if ag_node.id == node_id), None)


    def attach_attackers(self, model: Model):
        """
        Create attackers and their entry point nodes and attach them to the
        relevant attack step nodes and to the attackers.

        Arguments:
        model       - the instance model containing the attackers
        """

        logger.info(f'Attach attackers from \'{model.name}\' model to the '
            'graph.')
        for attacker_info in model.attackers:
            attacker_node = AttackGraphNode(
                    id = 'Attacker:' + str(attacker_info.id) + ':firstSteps',
                    type = 'or',
                    asset = None,
                    name = 'firstSteps',
                    ttc = {},
                    children = [],
                    parents = [],
                    compromised_by = []
            )

            ag_attacker = Attacker(
                id = str(attacker_info.id),
                entry_points = [],
                reached_attack_steps = [],
                node = attacker_node
            )
            attacker_node.attacker = ag_attacker
            self.attackers.append(ag_attacker)

            for (asset, attack_steps) in attacker_info.entry_points:
                for attack_step in attack_steps:
                    attack_step_id = asset.metaconcept + ':' \
                        + str(asset.id) + ':' + attack_step
                    ag_node = self.get_node_by_id(attack_step_id)
                    if not ag_node:
                        logger.warning('Failed to find attacker entry point '
                            + attack_step_id + ' for Attacker:'
                            + ag_attacker.id + '.')
                        continue
                    ag_attacker.compromise(ag_node)

            ag_attacker.entry_points = ag_attacker.reached_attack_steps
            attacker_node.children = ag_attacker.entry_points
            self.nodes.append(attacker_node)


    def _generate_graph(self):
        """
        Generate the attack graph based on the original model instance and the
        MAL language specification provided at initialization.
        """

        # First, generate all of the nodes of the attack graph.
        for asset in self.model.assets:
            logger.debug(f'Generating attack steps for asset {asset.name} which '\
                f'is of class {asset.metaconcept}.')
            attack_step_nodes = []
            attack_steps = specification.get_attacks_for_class(
                self.lang_spec, asset.metaconcept)
            for attack_step_name, attack_step_attribs in attack_steps.items():
                logger.debug('Generating attack step node for '\
                    f'{attack_step_name}.')

                defense_status = None
                existence_status: Optional[bool] = None
                node_id = asset.metaconcept + ':' + str(asset.id) + ':' + attack_step_name

                match (attack_step_attribs['type']):
                    case 'defense':
                        # Set the defense status for defenses
                        defense_status = getattr(asset, attack_step_name)
                        logger.debug('Setting the defense status of '\
                            f'{node_id} to {defense_status}.')

                    case 'exist' | 'notExist':
                        # Resolve step expression associated with (non-)existence
                        # attack steps.
                        (target_assets, attack_step) = _process_step_expression(
                            self.lang_spec,
                            self.model,
                            [asset],
                            attack_step_attribs['requires']['stepExpressions'][0])
                        # If the step expression resolution yielded the target
                        # assets then the required assets exist in the model.
                        existence_status = target_assets != []

                mitre_info = attack_step_attribs['meta']['mitre'] if 'mitre' in\
                    attack_step_attribs['meta'] else None
                ag_node = AttackGraphNode(
                    id = node_id,
                    type = attack_step_attribs['type'],
                    asset = asset,
                    name = attack_step_name,
                    ttc = attack_step_attribs['ttc'],
                    children = [],
                    parents = [],
                    defense_status = defense_status,
                    existence_status = existence_status,
                    is_viable = True,
                    is_necessary = True,
                    mitre_info = mitre_info,
                    tags = attack_step_attribs['tags'],
                    compromised_by = []
                )
                ag_node.attributes = attack_step_attribs
                attack_step_nodes.append(ag_node)
                self.nodes.append(ag_node)
            asset.attack_step_nodes = attack_step_nodes

        # Then, link all of the nodes according to their associations.
        for ag_node in self.nodes:
            logger.debug('Determining children for attack step '\
                f'{ag_node.id}.')
            step_expressions = \
                ag_node.attributes['reaches']['stepExpressions'] if \
                    isinstance(ag_node.attributes, dict) and ag_node.attributes['reaches'] else []

            for step_expression in step_expressions:
                # Resolve each of the attack step expressions listed for this
                # attack step to determine children.
                (target_assets, attack_step) = _process_step_expression(
                    self.lang_spec,
                    self.model,
                    [ag_node.asset],
                    step_expression)
                for target in target_assets:
                    target_node_id = target.metaconcept + ':' \
                        + str(target.id) + ':' + attack_step
                    target_node = self.get_node_by_id(target_node_id)
                    if not target_node:
                        msg = 'Failed to find target node ' \
                        f'{target_node_id} to link with for attack step ' \
                        f'{ag_node.id}!'
                        logger.error(msg)
                        raise AttackGraphStepExpressionError(msg)
                    ag_node.children.append(target_node)
                    target_node.parents.append(ag_node)


    def regenerate_graph(self):
        """
        Regenerate the attack graph based on the original model instance and
        the MAL language specification provided at initialization.
        """

        self.nodes = []
        self.attackers = []
        self._generate_graph()

    def remove_node(self, node):
        """
        Arguments:
        node    - the node we wish to remove from the attack graph
        """
        for child in node.children:
            child.parents.remove(node)
        for parent in node.parents:
            parent.children.remove(node)
        self.nodes.remove(node)
