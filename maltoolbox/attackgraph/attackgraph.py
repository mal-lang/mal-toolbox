"""MAL-Toolbox Attack Graph Module
"""
from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Optional

from maltoolbox.attackgraph.generate import generate_graph
from maltoolbox.attackgraph.node_getters import get_node_by_full_name
from maltoolbox.language.languagegraph import disaggregate_attack_step_full_name

from ..file_utils import load_dict_from_json_file, load_dict_from_yaml_file, save_dict_to_file
from ..language import LanguageGraph, LanguageGraphAttackStep
from ..model import Model
from .node import AttackGraphNode

if TYPE_CHECKING:
    from ..model import ModelAsset

logger = logging.getLogger(__name__)


def attack_graph_from_dict(
    serialized_object: dict, lang_graph: LanguageGraph, model: Optional[Model]
):
    attack_graph = AttackGraph(lang_graph)
    attack_graph.model = model
    serialized_attack_steps: dict[str, dict] = serialized_object['attack_steps']

    # Create all of the nodes in the imported attack graph.
    for node_full_name, node_dict in serialized_attack_steps.items():

        # Recreate asset links if model is available.
        node_asset = None
        if model and 'asset' in node_dict:
            node_asset = model.get_asset_by_name(node_dict['asset'])
            if node_asset is None:
                msg = (
                    'Failed to find asset with name "%s"'
                    ' when loading from attack graph dict'
                )
                logger.error(msg, node_dict["asset"])
                raise LookupError(msg % node_dict["asset"])

        lg_asset_name, lg_attack_step_name = (
            disaggregate_attack_step_full_name(
                node_dict['lang_graph_attack_step']
            )
        )
        lg_attack_step = (
            lang_graph.assets[lg_asset_name].attack_steps[lg_attack_step_name]
        )
        ag_node = attack_graph.add_node(
            lg_attack_step=lg_attack_step,
            node_id=node_dict['id'],
            model_asset=node_asset,
            ttc_dist=node_dict['ttc'],
            existence_status=(
                bool(node_dict['existence_status'])
                if 'existence_status' in node_dict else None
            ),
            # Give explicit full name if model is missing, otherwise
            # it will generate automatically in node.full_name
            full_name=node_full_name if not model else None
        )
        ag_node.tags = list(node_dict.get('tags', []))
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

    return attack_graph


def attack_graph_from_file(
    filename: str, lang_graph: LanguageGraph, model: Optional[Model]
):
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
    return attack_graph_from_dict(serialized_attack_graph, lang_graph, model)


class AttackGraph:
    """Graph representation of attack and defense steps"""

    def __init__(self, lang_graph: LanguageGraph, model: Model | None = None):
        self.nodes: dict[int, AttackGraphNode] = {}
        self.attack_steps: list[AttackGraphNode] = []
        self.defense_steps: list[AttackGraphNode] = []
        self.model = model
        self.lang_graph = lang_graph
        self.next_node_id = 0
        self.full_name_to_node: dict[str, AttackGraphNode] = {}

        if self.model is not None:
            self.nodes, self.attack_steps, self.defense_steps, self.full_name_to_node = (
                generate_graph(self.model)
            )

    def __repr__(self) -> str:
        return (
            f'AttackGraph(Number of nodes: {len(self.nodes)}, '
            f'model: {self.model}, language: {self.lang_graph}'
        )

    def _to_dict(self) -> dict:
        """Convert AttackGraph to dict"""
        serialized_attack_steps = {}
        for ag_node in self.nodes.values():
            serialized_attack_steps[ag_node.full_name] = ag_node.to_dict()
        return {
            'attack_steps': serialized_attack_steps
        }

    def __deepcopy__(self, memo):
        """Custom deepcopy implementation for attack graph"""
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

        # Copy lookup dicts
        copied_attackgraph.full_name_to_node = \
            copy.deepcopy(self.full_name_to_node, memo)

        # Copy counters
        copied_attackgraph.next_node_id = self.next_node_id
        return copied_attackgraph

    def save_to_file(self, filename: str) -> None:
        """Save to json/yml depending on extension"""
        logger.debug('Save attack graph to file "%s".', filename)
        return save_dict_to_file(filename, self._to_dict())

    @classmethod
    def load_from_file(
            cls,
            filename: str,
            lang_graph: LanguageGraph,
            model: Model | None = None
        ) -> AttackGraph:
        """Create from json or yaml file depending on file extension"""
        return attack_graph_from_file(filename, lang_graph, model)

    def get_node_by_full_name(self, full_name: str) -> AttackGraphNode:
        """Return the attack node that matches the full name provided.

        Arguments:
        ---------
        full_name   - the full name of the attack graph node we are looking
                      for

        Return:
        ------
        The attack step node that matches the given full name.

        """
        return get_node_by_full_name(self.full_name_to_node, full_name)

    def regenerate_graph(self) -> None:
        """Regenerate the attack graph based on the original model instance and
        the MAL language specification provided at initialization.
        """
        assert self.model, "Model required to generate graph"
        self.nodes, self.attack_steps, self.defense_steps, self.full_name_to_node = (
            generate_graph(self.model)
        )

    def add_node(
        self,
        lg_attack_step: LanguageGraphAttackStep,
        node_id: int | None = None,
        model_asset: ModelAsset | None = None,
        ttc_dist: dict | None = None,
        existence_status: bool | None = None,
        full_name: str | None = None
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
        ttc_dist            - the ttc distribution to assign to the node. This
                              is relevant for when we want to override the ttc
                              distribution as it is defined in the language.
                              Frequently used for defenses.
        existence_status    - the existence status of the node. Only, relevant
                              for exist and notExist type nodes.

        Return:
        ------
        The newly created attack step node.

        """

        node_id = node_id if node_id is not None else self.next_node_id
        if node_id in self.nodes:
            raise ValueError(f'Node index {node_id} already in use.')
        self.next_node_id = node_id + 1

        logger.debug(
            'Create and add to attackgraph node of type "%s" with id:%d.\n',
            lg_attack_step.full_name, node_id
        )

        node = AttackGraphNode(
            node_id=node_id,
            lg_attack_step=lg_attack_step,
            model_asset=model_asset,
            ttc_dist=ttc_dist,
            existence_status=existence_status,
            full_name=full_name
        )

        # Add to different lists depending on types
        # Useful but not vital for functionality
        if node.type in ('or', 'and'):
            self.attack_steps.append(node)
        if node.type == 'defense':
            self.defense_steps.append(node)

        self.nodes[node_id] = node
        self.full_name_to_node[node.full_name] = node

        return node

    def remove_node(self, node: AttackGraphNode) -> None:
        """Remove node from attack graph
        Arguments:
        node    - the node we wish to remove from the attack graph
        """
        logger.debug(
            'Remove node "%s"(%d).', node.full_name, node.id
        )
        for child in node.children:
            child.parents.remove(node)
        for parent in node.parents:
            parent.children.remove(node)
        del self.nodes[node.id]
        del self.full_name_to_node[node.full_name]

