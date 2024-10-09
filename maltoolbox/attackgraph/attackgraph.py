"""
MAL-Toolbox Attack Graph Module
"""
from __future__ import annotations
import copy
import logging
import json

from typing import TYPE_CHECKING

from .node import AttackGraphNode
from .attacker import Attacker
from ..exceptions import AttackGraphStepExpressionError
from ..model import Model
from ..exceptions import AttackGraphException
from ..file_utils import (
    load_dict_from_json_file,
    load_dict_from_yaml_file,
    save_dict_to_file
)

if TYPE_CHECKING:
    from typing import Any, Optional
    from ..language import LanguageGraph

logger = logging.getLogger(__name__)

# TODO see if (part of) this can be incorporated into the LanguageGraph, so that
# the LanguageGraph's _lang_spec private property does not need to be accessed
def _process_step_expression(
        lang_graph: LanguageGraph,
        model: Model,
        target_assets: list[Any],
        step_expression: dict[str, Any]
    ) -> tuple[list, Optional[str]]:
    """
    Recursively process an attack step expression.

    Arguments:
    lang_graph      - a language graph representing the MAL language
                      specification
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

    if logger.isEnabledFor(logging.DEBUG):
        # Avoid running json.dumps when not in debug
        logger.debug(
            'Processing Step Expression:\n%s',
            json.dumps(step_expression, indent = 2)
        )

    match (step_expression['type']):
        case 'attackStep':
            # The attack step expression just adds the name of the attack
            # step. All other step expressions only modify the target assets.
            return (target_assets, step_expression['name'])

        case 'union' | 'intersection' | 'difference':
            # The set operators are used to combine the left hand and right
            # hand targets accordingly.
            lh_targets, lh_attack_steps = _process_step_expression(
                lang_graph, model, target_assets, step_expression['lhs'])
            rh_targets, rh_attack_steps = _process_step_expression(
                lang_graph, model, target_assets, step_expression['rhs'])

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
                        if next((lnode for lnode in lh_targets \
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
                if (hasattr(target_asset, 'type')):
                    # TODO how can this info be accessed in the lang_graph
                    # directly without going through the private method?
                    variable_step_expr = lang_graph._get_variable_for_asset_type_by_name(
                        target_asset.type, step_expression['name'])
                    return _process_step_expression(
                        lang_graph, model, target_assets, variable_step_expr)

                else:
                    logger.error(
                        'Requested variable from non-asset target node:'
                        '%s which cannot be resolved.', target_asset
                    )
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
                    lang_graph, model, new_target_assets, step_expression)
                new_target_assets.extend(additional_assets)
                return (new_target_assets, None)
            else:
                return ([], None)

        case 'subType':
            new_target_assets = []
            for target_asset in target_assets:
                (assets, _) = _process_step_expression(
                    lang_graph, model, target_assets,
                    step_expression['stepExpression'])
                new_target_assets.extend(assets)

            selected_new_target_assets = []
            for asset in new_target_assets:
                lang_graph_asset = lang_graph.get_asset_by_name(
                    asset.type
                )
                if not lang_graph_asset:
                    raise LookupError(
                        f'Failed to find asset \"{asset.type}\" in the '
                        'language graph.'
                    )
                lang_graph_subtype_asset = lang_graph.get_asset_by_name(
                    step_expression['subType']
                )
                if not lang_graph_subtype_asset:
                    raise LookupError(
                        'Failed to find asset '
                        f'\"{step_expression["subType"]}\" in the '
                        'language graph.'
                    )
                if lang_graph_asset.is_subasset_of(lang_graph_subtype_asset):
                    selected_new_target_assets.append(asset)

            return (selected_new_target_assets, None)

        case 'collect':
            # Apply the right hand step expression to left hand step
            # expression target assets.
            lh_targets, _ = _process_step_expression(
                lang_graph, model, target_assets, step_expression['lhs'])
            return _process_step_expression(lang_graph, model, lh_targets,
                step_expression['rhs'])


        case _:
            logger.error(
                'Unknown attack step type: %s', step_expression["type"]
            )
            return ([], None)

class AttackGraph():
    """Graph representation of attack steps"""
    def __init__(self, lang_graph = None, model: Optional[Model] = None):
        self.nodes: list[AttackGraphNode] = []
        self.attackers: list[Attacker] = []
        # Dictionaries used in optimization to get nodes and attackers by id
        # or full name faster
        self._id_to_node: dict[int, AttackGraphNode] = {}
        self._full_name_to_node: dict[str, AttackGraphNode] = {}
        self._id_to_attacker: dict[int, Attacker] = {}

        self.model = model
        self.lang_graph = lang_graph
        self.next_node_id = 0
        self.next_attacker_id = 0
        if self.model is not None and self.lang_graph is not None:
            self._generate_graph()

    def __repr__(self) -> str:
        return f'AttackGraph({len(self.nodes)} nodes)'

    def _to_dict(self) -> dict:
        """Convert AttackGraph to dict"""
        serialized_attack_steps = {}
        serialized_attackers = {}
        for ag_node in self.nodes:
            serialized_attack_steps[ag_node.full_name] =\
                ag_node.to_dict()
        for attacker in self.attackers:
            serialized_attackers[attacker.name] = attacker.to_dict()
        return {
            'attack_steps': serialized_attack_steps,
            'attackers': serialized_attackers,
        }

    def __deepcopy__(self, memo):

        # Check if the object is already in the memo dictionary
        if id(self) in memo:
            return memo[id(self)]

        copied_attackgraph = AttackGraph(self.lang_graph)
        copied_attackgraph.model = self.model

        copied_attackgraph.nodes = []

        # Deep copy nodes
        for node in self.nodes:
            copied_node = copy.deepcopy(node, memo)
            copied_attackgraph.nodes.append(copied_node)

        # Re-link node references
        for node in self.nodes:
            if node.parents:
                memo[id(node)].parents = copy.deepcopy(node.parents, memo)
            if node.children:
                memo[id(node)].children = copy.deepcopy(node.children, memo)

        # Deep copy attackers and references to them
        copied_attackgraph.attackers = copy.deepcopy(self.attackers, memo)

        # Re-link attacker references
        for node in self.nodes:
            if node.compromised_by:
                memo[id(node)].compromised_by = copy.deepcopy(
                    node.compromised_by, memo)

        # Copy lookup dicts
        copied_attackgraph._id_to_attacker = \
            copy.deepcopy(self._id_to_attacker, memo)
        copied_attackgraph._id_to_node = \
            copy.deepcopy(self._id_to_node, memo)
        copied_attackgraph._full_name_to_node = \
            copy.deepcopy(self._full_name_to_node, memo)

        # Copy counters
        copied_attackgraph.next_node_id = self.next_node_id
        copied_attackgraph.next_attacker_id = self.next_attacker_id

        return copied_attackgraph

    def save_to_file(self, filename: str) -> None:
        """Save to json/yml depending on extension"""
        logger.debug('Save attack graph to file "%s".', filename)
        return save_dict_to_file(filename, self._to_dict())

    @classmethod
    def _from_dict(
            cls,
            serialized_object: dict,
            model: Optional[Model]=None
        ) -> AttackGraph:
        """Create AttackGraph from dict
        Args:
        serialized_object   - AttackGraph in dict format
        model               - Optional Model to add connections to
        """

        attack_graph = AttackGraph()
        attack_graph.model = model
        serialized_attack_steps = serialized_object['attack_steps']
        serialized_attackers = serialized_object['attackers']

        # Create all of the nodes in the imported attack graph.
        for node_full_name, node_dict in serialized_attack_steps.items():

            # Recreate asset links if model is available.
            node_asset = None
            if model and 'asset' in node_dict:
                node_asset = model.get_asset_by_name(node_dict['asset'])
                if node_asset is None:
                    msg = ('Failed to find asset with id %s'
                            'when loading from attack graph dict')
                    logger.error(msg, node_dict["asset"])
                    raise LookupError(msg % node_dict["asset"])

            ag_node = AttackGraphNode(
                type=node_dict['type'],
                name=node_dict['name'],
                ttc=node_dict['ttc'],
                asset=node_asset
            )

            if node_asset:
                # Add AttackGraphNode to attack_step_nodes of asset
                if hasattr(node_asset, 'attack_step_nodes'):
                    node_attack_steps = list(node_asset.attack_step_nodes)
                    node_attack_steps.append(ag_node)
                    node_asset.attack_step_nodes = node_attack_steps
                else:
                    node_asset.attack_step_nodes = [ag_node]

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
            ag_node.extras = node_dict.get('extras', {})

            # Add AttackGraphNode to AttackGraph
            attack_graph.add_node(ag_node, node_id=node_dict['id'])

        # Re-establish links between nodes.
        for node_full_name, node_dict in serialized_attack_steps.items():
            _ag_node = attack_graph.get_node_by_id(node_dict['id'])
            if not isinstance(_ag_node, AttackGraphNode):
                msg = ('Failed to find node with id %s when loading'
                       ' attack graph from dict')
                logger.error(msg, node_dict["id"])
                raise LookupError(msg % node_dict["id"])
            else:
                for child_id in node_dict['children']:
                    child = attack_graph.get_node_by_id(int(child_id))
                    if child is None:
                        msg = ('Failed to find child node with id %s'
                               ' when loading from attack graph from dict')
                        logger.error(msg, child_id)
                        raise LookupError(msg % child_id)
                    _ag_node.children.append(child)

                for parent_id in node_dict['parents']:
                    parent = attack_graph.get_node_by_id(int(parent_id))
                    if parent is None:
                        msg = ('Failed to find parent node with id %s '
                               'when loading from attack graph from dict')
                        logger.error(msg, parent_id)
                        raise LookupError(msg % parent_id)
                    _ag_node.parents.append(parent)

        for attacker_name, attacker in serialized_attackers.items():
            ag_attacker = Attacker(
                name = attacker['name'],
                entry_points = [],
                reached_attack_steps = []
            )
            attack_graph.add_attacker(
                attacker = ag_attacker,
                attacker_id = int(attacker['id']),
                entry_points = attacker['entry_points'].keys(),
                reached_attack_steps = [
                    int(node_id) # Convert to int since they can be strings
                    for node_id in attacker['reached_attack_steps'].keys()
                ]
            )

        return attack_graph

    @classmethod
    def load_from_file(
            cls,
            filename: str,
            model: Optional[Model]=None
        ) -> AttackGraph:
        """Create from json or yaml file depending on file extension"""
        if model is not None:
            logger.debug('Load attack graph from file "%s" with '
            'model "%s".', filename, model.name)
        else:
            logger.debug('Load attack graph from file "%s" '
            'without model.', filename)
        serialized_attack_graph = None
        if filename.endswith(('.yml', '.yaml')):
            serialized_attack_graph = load_dict_from_yaml_file(filename)
        elif filename.endswith('.json'):
            serialized_attack_graph = load_dict_from_json_file(filename)
        else:
            raise ValueError('Unknown file extension, expected json/yml/yaml')
        return cls._from_dict(serialized_attack_graph, model=model)

    def get_node_by_id(self, node_id: int) -> Optional[AttackGraphNode]:
        """
        Return the attack node that matches the id provided.

        Arguments:
        node_id     - the id of the attack graph node we are looking for

        Return:
        The attack step node that matches the given id.
        """

        logger.debug('Looking up node with id %s', node_id)
        return self._id_to_node.get(node_id)

    def get_node_by_full_name(self, full_name: str) -> Optional[AttackGraphNode]:
        """
        Return the attack node that matches the full name provided.

        Arguments:
        full_name   - the full name of the attack graph node we are looking
                      for

        Return:
        The attack step node that matches the given full name.
        """

        logger.debug(f'Looking up node with full name "{full_name}"')
        return self._full_name_to_node.get(full_name)

    def get_attacker_by_id(self, attacker_id: int) -> Optional[Attacker]:
        """
        Return the attacker that matches the id provided.

        Arguments:
        attacker_id     - the id of the attacker we are looking for

        Return:
        The attacker that matches the given id.
        """

        logger.debug(f'Looking up attacker with id {attacker_id}')
        return self._id_to_attacker.get(attacker_id)

    def attach_attackers(self) -> None:
        """
        Create attackers and their entry point nodes and attach them to the
        relevant attack step nodes and to the attackers.
        """

        if not self.model:
            msg = "Can not attach attackers without a model"
            logger.error(msg)
            raise AttackGraphException(msg)

        logger.info(
            'Attach attackers from "%s" model to the graph.', self.model.name
        )

        for attacker_info in self.model.attackers:

            if not attacker_info.name:
                msg = "Can not attach attacker without name"
                logger.error(msg)
                raise AttackGraphException(msg)

            attacker = Attacker(
                name = attacker_info.name,
                entry_points = [],
                reached_attack_steps = []
            )
            self.add_attacker(attacker)

            for (asset, attack_steps) in attacker_info.entry_points:
                for attack_step in attack_steps:
                    full_name = asset.name + ':' + attack_step
                    ag_node = self.get_node_by_full_name(full_name)
                    if not ag_node:
                        logger.warning(
                            'Failed to find attacker entry point '
                            '%s for %s.',
                            full_name, attacker.name
                        )
                        continue
                    attacker.compromise(ag_node)

            attacker.entry_points = list(attacker.reached_attack_steps)

    def _generate_graph(self) -> None:
        """
        Generate the attack graph based on the original model instance and the
        MAL language specification provided at initialization.
        """

        if not self.model:
            msg = "Can not generate AttackGraph without model"
            logger.error(msg)
            raise AttackGraphException(msg)

        # First, generate all of the nodes of the attack graph.
        for asset in self.model.assets:

            logger.debug(
                'Generating attack steps for asset %s which is of class %s.',
                asset.name, asset.type
            )

            attack_step_nodes = []

            # TODO probably part of what happens here is already done in lang_graph
            attack_steps = self.lang_graph._get_attacks_for_asset_type(asset.type)

            for attack_step_name, attack_step_attribs in attack_steps.items():
                logger.debug(
                    'Generating attack step node for %s.', attack_step_name
                )

                defense_status = None
                existence_status = None
                node_name = asset.name + ':' + attack_step_name

                match (attack_step_attribs['type']):
                    case 'defense':
                        # Set the defense status for defenses
                        defense_status = getattr(asset, attack_step_name)
                        logger.debug(
                            'Setting the defense status of %s to %s.',
                            node_name, defense_status
                        )

                    case 'exist' | 'notExist':
                        # Resolve step expression associated with (non-)existence
                        # attack steps.
                        (target_assets, attack_step) = _process_step_expression(
                            self.lang_graph,
                            self.model,
                            [asset],
                            attack_step_attribs['requires']['stepExpressions'][0])
                        # If the step expression resolution yielded the target
                        # assets then the required assets exist in the model.
                        existence_status = target_assets != []

                mitre_info = attack_step_attribs['meta']['mitre'] if 'mitre' in\
                    attack_step_attribs['meta'] else None
                ag_node = AttackGraphNode(
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
                self.add_node(ag_node)
            asset.attack_step_nodes = attack_step_nodes

        # Then, link all of the nodes according to their associations.
        for ag_node in self.nodes:
            logger.debug(
                'Determining children for attack step "%s"(%d)',
                ag_node.full_name,
                ag_node.id
            )
            step_expressions = \
                ag_node.attributes['reaches']['stepExpressions'] if \
                    isinstance(ag_node.attributes, dict) and ag_node.attributes['reaches'] else []

            for step_expression in step_expressions:
                # Resolve each of the attack step expressions listed for this
                # attack step to determine children.
                (target_assets, attack_step) = _process_step_expression(
                    self.lang_graph,
                    self.model,
                    [ag_node.asset],
                    step_expression)

                for target in target_assets:
                    target_node_full_name = target.name + ':' + attack_step
                    target_node = self.get_node_by_full_name(
                        target_node_full_name
                    )
                    if not target_node:
                        msg = ('Failed to find target node '
                               '"%s" to link with for attack step "%s"(%d)!')
                        logger.error(
                            msg,
                            target_node_full_name,
                            ag_node.full_name,
                            ag_node.id
                        )
                        raise AttackGraphStepExpressionError(
                            msg % (
                                target_node_full_name,
                                ag_node.full_name,
                                ag_node.id
                            )
                        )
                    ag_node.children.append(target_node)
                    target_node.parents.append(ag_node)

    def regenerate_graph(self) -> None:
        """
        Regenerate the attack graph based on the original model instance and
        the MAL language specification provided at initialization.
        """

        self.nodes = []
        self.attackers = []
        self._generate_graph()

    def add_node(
            self,
            node: AttackGraphNode,
            node_id: Optional[int] = None
        ) -> None:
        """Add a node to the graph
        Arguments:
        node    - the node to add
        node_id - the id to assign to this node, usually used when loading
                  an attack graph from a file
        """
        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(f'Add node \"{node.full_name}\" '
                f'with id:{node_id}:\n' \
                + json.dumps(node.to_dict(), indent = 2))

        if node.id in self._id_to_node:
            raise ValueError(f'Node index {node_id} already in use.')

        node.id = node_id if node_id is not None else self.next_node_id
        self.next_node_id = max(node.id + 1, self.next_node_id)

        self.nodes.append(node)
        self._id_to_node[node.id] = node
        self._full_name_to_node[node.full_name] = node

    def remove_node(self, node: AttackGraphNode) -> None:
        """Remove node from attack graph
        Arguments:
        node    - the node we wish to remove from the attack graph
        """
        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(f'Remove node "%s"(%d).', node.full_name, node.id)
        for child in node.children:
            child.parents.remove(node)
        for parent in node.parents:
            parent.children.remove(node)
        self.nodes.remove(node)

        if not isinstance(node.id, int):
            raise ValueError(f'Invalid node id.')
        del self._id_to_node[node.id]
        del self._full_name_to_node[node.full_name]

    def add_attacker(
            self,
            attacker: Attacker,
            attacker_id: Optional[int] = None,
            entry_points: list[int] = [],
            reached_attack_steps: list[int] = []
        ):
        """Add an attacker to the graph
        Arguments:
        attacker                - the attacker to add
        attacker_id             - the id to assign to this attacker, usually
                                  used when loading an attack graph from a
                                  file
        entry_points            - list of attack step ids that serve as entry
                                  points for the attacker
        reached_attack_steps    - list of ids of the attack steps that the
                                  attacker has reached
        """
        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            if attacker_id is not None:
                logger.debug('Add attacker "%s" with id:%d.',
                    attacker.name,
                    attacker_id)
            else:
                logger.debug('Add attacker "%s" without id.',
                    attacker.name)


        attacker.id = attacker_id or self.next_attacker_id
        if attacker.id in self._id_to_attacker:
            raise ValueError(f'Attacker index {attacker_id} already in use.')

        self.next_attacker_id = max(attacker.id + 1, self.next_attacker_id)
        for node_id in reached_attack_steps:
            node = self.get_node_by_id(node_id)
            if node:
                attacker.compromise(node)
            else:
                msg = ("Could not find node with id %d"
                       "in reached attack steps.")
                logger.error(msg, node_id)
                raise AttackGraphException(msg % node_id)
        for node_id in entry_points:
            node = self.get_node_by_id(int(node_id))
            if node:
                attacker.entry_points.append(node)
            else:
                msg = ("Could not find node with id %d"
                       "in attacker entrypoints.")
                logger.error(msg, node_id)
                raise AttackGraphException(msg % node_id)
        self.attackers.append(attacker)
        self._id_to_attacker[attacker.id] = attacker

    def remove_attacker(self, attacker: Attacker):
        """Remove attacker from attack graph
        Arguments:
        attacker    - the attacker we wish to remove from the attack graph
        """
        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug('Remove attacker "%s" with id:%d.',
                attacker.name,
                attacker.id)
        for node in attacker.reached_attack_steps:
            attacker.undo_compromise(node)
        self.attackers.remove(attacker)
        if not isinstance(attacker.id, int):
            raise ValueError(f'Invalid attacker id.')
        del self._id_to_attacker[attacker.id]
