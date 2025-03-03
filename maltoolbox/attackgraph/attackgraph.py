"""
MAL-Toolbox Attack Graph Module
"""
from __future__ import annotations
import copy
import logging
import json
import sys
import zipfile

from itertools import chain
from typing import TYPE_CHECKING

from .analyzers.apriori import calculate_viability_and_necessity
from .node import AttackGraphNode
from .attacker import Attacker
from .. import log_configs
from ..exceptions import AttackGraphStepExpressionError, AttackGraphException
from ..exceptions import LanguageGraphException
from ..model import Model
from ..language import (LanguageGraph, ExpressionsChain,
    LanguageGraphAttackStep, disaggregate_attack_step_full_name)
from ..file_utils import (
    load_dict_from_json_file,
    load_dict_from_yaml_file,
    save_dict_to_file
)


if TYPE_CHECKING:
    from typing import Any, Optional
    from ..model import ModelAsset

logger = logging.getLogger(__name__)


def create_attack_graph(
        lang_file: str,
        model_file: str,
        attach_attackers=True,
        calc_viability_and_necessity=True
    ) -> AttackGraph:
    """Create and return an attack graph

    Args:
    lang_file                       - path to language file (.mar or .mal)
    model_file                      - path to model file (yaml or json)
    attach_attackers                - whether to run attach_attackers or not
    calc_viability_and_necessity    - whether run apriori calculations or not
    """
    try:
        lang_graph = LanguageGraph.from_mar_archive(lang_file)
    except zipfile.BadZipFile:
        lang_graph = LanguageGraph.from_mal_spec(lang_file)

    if log_configs['langspec_file']:
        lang_graph.save_to_file(log_configs['langspec_file'])

    instance_model = Model.load_from_file(model_file, lang_graph)

    if log_configs['model_file']:
        instance_model.save_to_file(log_configs['model_file'])

    try:
        attack_graph = AttackGraph(lang_graph, instance_model)
    except AttackGraphStepExpressionError:
        logger.error(
            'Attack graph generation failed when attempting '
            'to resolve attack step expression!'
        )
        sys.exit(1)

    if attach_attackers:
        attack_graph.attach_attackers()

    if calc_viability_and_necessity:
        calculate_viability_and_necessity(attack_graph)

    return attack_graph


class AttackGraph():
    """Graph representation of attack steps"""
    def __init__(self, lang_graph, model: Optional[Model] = None):
        self.nodes: dict[int, AttackGraphNode] = {}
        self.attackers: dict[int, Attacker] = {}
        # Dictionaries used in optimization to get nodes and attackers by id
        # or full name faster
        self._full_name_to_node: dict[str, AttackGraphNode] = {}

        self.model = model
        self.lang_graph = lang_graph
        self.next_node_id = 0
        self.next_attacker_id = 0
        if self.model is not None:
            self._generate_graph()

    def __repr__(self) -> str:
        return (f'AttackGraph(Number of nodes: {len(self.nodes)}, '
            f'model: {self.model}, language: {self.lang_graph}')

    def _to_dict(self) -> dict:
        """Convert AttackGraph to dict"""
        serialized_attack_steps = {}
        serialized_attackers = {}
        for ag_node in self.nodes.values():
            serialized_attack_steps[ag_node.full_name] =\
                ag_node.to_dict()
        for attacker in self.attackers.values():
            serialized_attackers[attacker.name] = attacker.to_dict()
        logger.debug('Serialized %d attack steps and %d attackers.' %
            (len(self.nodes), len(self.attackers))
        )
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

        copied_attackgraph.nodes = {}

        # Deep copy nodes
        for node_id, node in self.nodes.items():
            copied_node = copy.deepcopy(node, memo)
            copied_attackgraph.nodes[node_id] = copied_node

        # Re-link node references
        for node in self.nodes.values():
            if node.parents:
                memo[id(node)].parents = copy.deepcopy(node.parents, memo)
            if node.children:
                memo[id(node)].children = copy.deepcopy(node.children, memo)

        # Deep copy attackers
        for attacker_id, attacker in self.attackers.items():
            copied_attacker = copy.deepcopy(attacker, memo)
            copied_attackgraph.attackers[attacker_id] = copied_attacker

        # Re-link attacker references
        for node in self.nodes.values():
            if node.compromised_by:
                memo[id(node)].compromised_by = copy.deepcopy(
                    node.compromised_by, memo)

        # Copy lookup dicts
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
            lang_graph: LanguageGraph,
            model: Optional[Model]=None
        ) -> AttackGraph:
        """Create AttackGraph from dict
        Args:
        serialized_object   - AttackGraph in dict format
        model               - Optional Model to add connections to
        """

        attack_graph = AttackGraph(lang_graph)
        attack_graph.model = model
        serialized_attack_steps = serialized_object['attack_steps']
        serialized_attackers = serialized_object['attackers']

        # Create all of the nodes in the imported attack graph.
        for node_dict in serialized_attack_steps.values():

            # Recreate asset links if model is available.
            node_asset = None
            if model and 'asset' in node_dict:
                node_asset = model.get_asset_by_name(node_dict['asset'])
                if node_asset is None:
                    msg = ('Failed to find asset with name "%s"'
                            ' when loading from attack graph dict')
                    logger.error(msg, node_dict["asset"])
                    raise LookupError(msg % node_dict["asset"])

            lg_asset_name, lg_attack_step_name = \
                disaggregate_attack_step_full_name(
                    node_dict['lang_graph_attack_step'])
            lg_attack_step = lang_graph.assets[lg_asset_name].\
                attack_steps[lg_attack_step_name]
            ag_node = attack_graph.add_node(
                lg_attack_step = lg_attack_step,
                node_id = node_dict['id'],
                model_asset = node_asset,
                defense_status = node_dict.get('defense_status', None),
                existence_status = node_dict.get('existence_status', None)
            )
            ag_node.tags = set(node_dict.get('tags', []))
            ag_node.extras = node_dict.get('extras', {})

            if node_asset:
                # Add AttackGraphNode to attack_step_nodes of asset
                if hasattr(node_asset, 'attack_step_nodes'):
                    node_attack_steps = list(node_asset.attack_step_nodes)
                    node_attack_steps.append(ag_node)
                    node_asset.attack_step_nodes = node_attack_steps
                else:
                    node_asset.attack_step_nodes = [ag_node]


        # Re-establish links between nodes.
        for node_dict in serialized_attack_steps.values():
            _ag_node = attack_graph.nodes[node_dict['id']]
            if not isinstance(_ag_node, AttackGraphNode):
                msg = ('Failed to find node with id %s when loading'
                       ' attack graph from dict')
                logger.error(msg, node_dict["id"])
                raise LookupError(msg % node_dict["id"])
            else:
                for child_id in node_dict['children']:
                    child = attack_graph.nodes[int(child_id)]
                    if child is None:
                        msg = ('Failed to find child node with id %s'
                               ' when loading from attack graph from dict')
                        logger.error(msg, child_id)
                        raise LookupError(msg % child_id)
                    _ag_node.children.add(child)

                for parent_id in node_dict['parents']:
                    parent = attack_graph.nodes[int(parent_id)]
                    if parent is None:
                        msg = ('Failed to find parent node with id %s '
                               'when loading from attack graph from dict')
                        logger.error(msg, parent_id)
                        raise LookupError(msg % parent_id)
                    _ag_node.parents.add(parent)

        for attacker in serialized_attackers.values():
            ag_attacker = Attacker(name = attacker['name'])
            attack_graph.add_attacker(
                attacker = ag_attacker,
                attacker_id = int(attacker['id']),
                entry_points = [
                    int(node_id) # Convert to int since they can be strings
                    for node_id in attacker['entry_points'].keys()
                ],
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
            lang_graph: LanguageGraph,
            model: Optional[Model] = None
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
        return cls._from_dict(serialized_attack_graph,
            lang_graph, model = model)

    def get_node_by_full_name(self, full_name: str) -> Optional[AttackGraphNode]:
        """
        Return the attack node that matches the full name provided.

        Arguments:
        full_name   - the full name of the attack graph node we are looking
                      for

        Return:
        The attack step node that matches the given full name.
        """

        logger.debug(f'Looking up node with full name "%s"', full_name)
        return self._full_name_to_node.get(full_name)

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

            attacker = Attacker(name = attacker_info.name)
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

            attacker.entry_points = set(attacker.reached_attack_steps)

    def _follow_expr_chain(
            self,
            model: Model,
            target_assets: set[ModelAsset],
            expr_chain: Optional[ExpressionsChain]
        ) -> set[Any]:
        """
        Recursively follow a language graph expressions chain on an instance
        model.

        Arguments:
        model           - a maltoolbox.model.Model on which to follow the
                          expressions chain
        target_assets   - the set of assets that this expressions chain
                          should apply to. Initially it will contain the
                          asset to which the attack step belongs
        expr_chain      - the expressions chain we are following

        Return:
        A list of all of the target assets.
        """

        if expr_chain is None:
            # There is no expressions chain link left to follow return the
            # current target assets
            return set(target_assets)

        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(
                'Following Expressions Chain:\n%s',
                json.dumps(expr_chain.to_dict(), indent = 2)
            )

        match (expr_chain.type):
            case 'union' | 'intersection' | 'difference':
                # The set operators are used to combine the left hand and
                # right hand targets accordingly.
                if not expr_chain.left_link:
                    raise LanguageGraphException('"%s" step expression chain'
                        ' is missing the left link.' % expr_chain.type)
                if not expr_chain.right_link:
                    raise LanguageGraphException('"%s" step expression chain'
                        ' is missing the right link.' % expr_chain.type)
                lh_targets = self._follow_expr_chain(
                    model,
                    target_assets,
                    expr_chain.left_link
                )
                rh_targets = self._follow_expr_chain(
                    model,
                    target_assets,
                    expr_chain.right_link
                )

                match (expr_chain.type):
                    # Once the assets become hashable set operations should be
                    # used instead.
                    case 'union':
                        new_target_assets = lh_targets.union(rh_targets)

                    case 'intersection':
                        new_target_assets = lh_targets.intersection(rh_targets)

                    case 'difference':
                        new_target_assets = lh_targets.difference(rh_targets)

                return new_target_assets

            case 'field':
                # Change the target assets from the current ones to the
                # associated assets given the specified field name.
                if not expr_chain.fieldname:
                    raise LanguageGraphException('"field" step expression '
                        'chain is missing fieldname.')
                new_target_assets = set()
                new_target_assets.update(
                    *(
                        asset.associated_assets.get(
                            expr_chain.fieldname, set()
                        ) for asset in target_assets
                      )
                )
                return new_target_assets

            case 'transitive':
                if not expr_chain.sub_link:
                    raise LanguageGraphException('"transitive" step '
                        'expression chain is missing sub link.')

                new_assets = target_assets

                while new_assets := self._follow_expr_chain(
                    model, new_assets, expr_chain.sub_link
                ):
                    if not (new_assets := new_assets.difference(target_assets)):
                        break

                    target_assets.update(new_assets)

                return target_assets

            case 'subType':
                if not expr_chain.sub_link:
                    raise LanguageGraphException('"subType" step '
                        'expression chain is missing sub link.')
                new_target_assets = set()
                new_target_assets.update(
                    self._follow_expr_chain(
                        model, target_assets, expr_chain.sub_link
                    )
                )

                selected_new_target_assets = set()
                for asset in new_target_assets:
                    lang_graph_asset = self.lang_graph.assets[asset.type]
                    if not lang_graph_asset:
                        raise LookupError(
                            f'Failed to find asset \"{asset.type}\" in the '
                            'language graph.'
                        )
                    lang_graph_subtype_asset = expr_chain.subtype
                    if not lang_graph_subtype_asset:
                        raise LookupError(
                            'Failed to find asset "%s" in the '
                            'language graph.' % expr_chain.subtype
                        )
                    if lang_graph_asset.is_subasset_of(
                            lang_graph_subtype_asset):
                        selected_new_target_assets.add(asset)

                return selected_new_target_assets

            case 'collect':
                if not expr_chain.left_link:
                    raise LanguageGraphException('"collect" step expression chain'
                        ' is missing the left link.')
                if not expr_chain.right_link:
                    raise LanguageGraphException('"collect" step expression chain'
                        ' is missing the right link.')
                lh_targets = self._follow_expr_chain(
                    model,
                    target_assets,
                    expr_chain.left_link
                )
                rh_targets = set()
                for lh_target in lh_targets:
                    rh_targets |= self._follow_expr_chain(
                        model,
                        {lh_target},
                        expr_chain.right_link
                    )
                return rh_targets

            case _:
                msg = 'Unknown attack expressions chain type: %s'
                logger.error(
                    msg,
                    expr_chain.type
                )
                raise AttackGraphStepExpressionError(
                    msg % expr_chain.type
                )
                return None

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
        for asset in self.model.assets.values():

            logger.debug(
                'Generating attack steps for asset %s which is of class %s.',
                asset.name, asset.type
            )

            attack_step_nodes = []

            for attack_step in asset.lg_asset.attack_steps.values():
                logger.debug(
                    'Generating attack step node for %s.', attack_step.name
                )

                defense_status = None
                existence_status = None
                node_name = asset.name + ':' + attack_step.name

                match (attack_step.type):
                    case 'defense':
                        # Set the defense status for defenses
                        defense_status = asset.defenses[attack_step.name]
                        logger.debug(
                            'Setting the defense status of \"%s\" to "%s".',
                            node_name, defense_status
                        )

                    case 'exist' | 'notExist':
                        # Resolve step expression associated with
                        # (non-)existence attack steps.
                        existence_status = False
                        for requirement in attack_step.requires:
                            target_assets = self._follow_expr_chain(
                                    self.model,
                                    set([asset]),
                                    requirement
                                )
                            # If the step expression resolution yielded
                            # the target assets then the required assets
                            # exist in the model.
                            if target_assets:
                                existence_status = True
                                break

                        logger.debug(
                            'Setting the existence status of \"%s\" to '
                            '%s.',
                            node_name, existence_status
                        )

                    case _:
                        pass

                ag_node = self.add_node(
                    lg_attack_step = attack_step,
                    model_asset = asset,
                    defense_status = defense_status,
                    existence_status = existence_status
                )
                attack_step_nodes.append(ag_node)

            asset.attack_step_nodes = attack_step_nodes

        # Then, link all of the nodes according to their associations.
        for ag_node in self.nodes.values():
            logger.debug(
                'Determining children for attack step "%s"(%d)',
                ag_node.full_name,
                ag_node.id
            )

            if not ag_node.model_asset:
                raise AttackGraphException('Attack graph node is missing '
                    'asset link')
            lang_graph_asset = self.lang_graph.assets[
                ag_node.model_asset.type]

            lang_graph_attack_step = lang_graph_asset.attack_steps[
                ag_node.name]

            while lang_graph_attack_step:
                for child in lang_graph_attack_step.children.values():
                    for target_attack_step, expr_chain in child:
                        target_assets = self._follow_expr_chain(
                            self.model,
                            set([ag_node.model_asset]),
                            expr_chain
                        )

                        for target_asset in target_assets:
                            if target_asset is not None:
                                target_node_full_name = target_asset.name + \
                                    ':' + target_attack_step.name
                                target_node = self.get_node_by_full_name(
                                    target_node_full_name)
                                if target_node is None:
                                    msg = ('Failed to find target node '
                                           '"%s" to link with for attack '
                                           'step "%s"(%d)!')
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

                                assert ag_node.id is not None
                                assert target_node.id is not None

                                logger.debug('Linking attack step "%s"(%d) '
                                    'to attack step "%s"(%d)' %
                                    (
                                        ag_node.full_name,
                                        ag_node.id,
                                        target_node.full_name,
                                        target_node.id
                                    )
                                )
                                ag_node.children.add(target_node)
                                target_node.parents.add(ag_node)
                if lang_graph_attack_step.overrides:
                    break
                lang_graph_attack_step = lang_graph_attack_step.inherits


    def regenerate_graph(self) -> None:
        """
        Regenerate the attack graph based on the original model instance and
        the MAL language specification provided at initialization.
        """

        self.nodes = {}
        self.attackers = {}
        self._generate_graph()

    def add_node(
            self,
            lg_attack_step: LanguageGraphAttackStep,
            node_id: Optional[int] = None,
            model_asset: Optional[ModelAsset] = None,
            defense_status: Optional[float] = None,
            existence_status: Optional[bool] = None
        ) -> AttackGraphNode:
        """Create and add a node to the graph
        Arguments:
        lg_attack_step      - the language graph attack step that corresponds
                              to the attack graph node to create
        node_id             - id to assign to the newly created node, usually
                              provided only when loading an existing attack
                              graph from a file. If not provided the id will
                              be set to the next highest id available.
        model_asset         - the model asset that corresponds to the attack
                              step node. While optional it is highly
                              recommended that this be provided. It should
                              only be ommitted if the model which was used to
                              generate the attack graph is not available when
                              loading an attack graph from a file.
        defese_status       - the defense status of the node. Only, relevant
                              for defense type nodes. A value between 0.0 and
                              1.0 is expected.
        existence_status    - the existence status of the node. Only, relevant
                              for exist and notExist type nodes.

        Return:
        The newly created attack step node.
        """
        node_id = node_id if node_id is not None else self.next_node_id
        if node_id in self.nodes:
            raise ValueError(f'Node index {node_id} already in use.')
        self.next_node_id = max(node_id + 1, self.next_node_id)

        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug('Create and add to attackgraph node of type "%s" '
                'with id:%d.\n' % (
                    lg_attack_step.full_name,
                    node_id
                ))


        node = AttackGraphNode(
            node_id = node_id,
            lg_attack_step = lg_attack_step,
            model_asset = model_asset,
            defense_status = defense_status,
            existence_status = existence_status
        )

        self.nodes[node_id] = node
        self._full_name_to_node[node.full_name] = node

        return node

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

        if not isinstance(node.id, int):
            raise ValueError(f'Invalid node id.')
        del self.nodes[node.id]
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
                    attacker_id
                )
            else:
                logger.debug('Add attacker "%s" without id.',
                    attacker.name
                )

        attacker.id = attacker_id or self.next_attacker_id
        if attacker.id in self.attackers:
            raise ValueError(f'Attacker index {attacker_id} already in use.')

        self.next_attacker_id = max(attacker.id + 1, self.next_attacker_id)
        for node_id in reached_attack_steps:
            node = self.nodes[node_id]
            if node:
                attacker.compromise(node)
            else:
                msg = ("Could not find node with id %d"
                       "in reached attack steps.")
                logger.error(msg, node_id)
                raise AttackGraphException(msg % node_id)
        for node_id in entry_points:
            node = self.nodes[node_id]
            if node:
                attacker.entry_points.add(node)
            else:
                msg = ("Could not find node with id %d"
                       "in attacker entrypoints.")
                logger.error(msg, node_id)
                raise AttackGraphException(msg % node_id)
        self.attackers[attacker.id] = attacker

    def remove_attacker(self, attacker: Attacker):
        """Remove attacker from attack graph
        Arguments:
        attacker    - the attacker we wish to remove from the attack graph
        """
        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(
                'Remove attacker "%s" with id:%d.',
                attacker.name, attacker.id
            )

        # Copy set - we can not remove elements from a set we are looping over
        nodes_to_uncompromise = set(attacker.reached_attack_steps)
        for node in nodes_to_uncompromise:
            attacker.undo_compromise(node)

        if not isinstance(attacker.id, int):
            raise ValueError(f'Invalid attacker id: {attacker.id}')
        del self.attackers[attacker.id]
