"""MAL-Toolbox Attack Graph Module
"""
from __future__ import annotations

import copy
import json
import logging
import sys
import zipfile
from typing import TYPE_CHECKING

from .. import log_configs
from ..exceptions import (
    AttackGraphException,
    AttackGraphStepExpressionError,
    LanguageGraphException,
)
from ..file_utils import (
    load_dict_from_json_file,
    load_dict_from_yaml_file,
    save_dict_to_file,
)
from ..language import (
    ExpressionsChain,
    LanguageGraph,
    LanguageGraphAttackStep,
    disaggregate_attack_step_full_name,
)

from ..str_utils import levenshtein_distance
from ..model import Model
from .node import AttackGraphNode

if TYPE_CHECKING:
    from typing import Any

    from ..model import ModelAsset

logger = logging.getLogger(__name__)


def create_attack_graph(
        lang: str | LanguageGraph,
        model: str | Model,
    ) -> AttackGraph:
    """Create and return an attack graph

    Args:
    ----
    lang    - path to language file (.mar or .mal) or a LanguageGraph object
    model   - path to model file (yaml or json) or a Model object

    """
    # Load language
    if isinstance(lang, LanguageGraph):
        lang_graph = lang
    elif isinstance(lang, str):
        # Load from path
        try:
            lang_graph = LanguageGraph.from_mar_archive(lang)
        except zipfile.BadZipFile:
            lang_graph = LanguageGraph.from_mal_spec(lang)
    else:
        raise TypeError("`lang` must be either string or LanguageGraph")

    if 'langspec_file' in log_configs:
        lang_graph.save_language_specification_to_json(
            log_configs['langspec_file']
        )

    if 'langgraph_file' in log_configs:
        lang_graph.save_to_file(log_configs['langgraph_file'])

    # Load model
    if isinstance(model, Model):
        instance_model = model
    elif isinstance(model, str):
        # Load from path
        instance_model = Model.load_from_file(model, lang_graph)
    else:
        raise TypeError("`model` must be either string or Model")

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

    return attack_graph


class AttackGraph:
    """Graph representation of attack steps"""

    def __init__(self, lang_graph: LanguageGraph, model: Model | None = None):
        self.nodes: dict[int, AttackGraphNode] = {}
        self.attack_steps: list[AttackGraphNode] = []
        self.defense_steps: list[AttackGraphNode] = []
        self.model = model
        self.lang_graph = lang_graph
        self.next_node_id = 0

        # Dictionary used in optimization to get nodes by full name faster
        self._full_name_to_node: dict[str, AttackGraphNode] = {}

        if self.model is not None:
            self._generate_graph(self.model)

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
        copied_attackgraph._full_name_to_node = \
            copy.deepcopy(self._full_name_to_node, memo)

        # Copy counters
        copied_attackgraph.next_node_id = self.next_node_id

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
        model: Model | None = None
    ) -> AttackGraph:
        """Create AttackGraph from dict
        Args:
        serialized_object   - AttackGraph in dict format
        model               - Optional Model to add connections to
        """
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

    @classmethod
    def load_from_file(
            cls,
            filename: str,
            lang_graph: LanguageGraph,
            model: Model | None = None
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
            lang_graph, model=model)

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
        logger.debug('Looking up node with full name "%s"', full_name)
        if full_name not in self._full_name_to_node:
            similar_names = self._get_similar_full_names(full_name)
            raise LookupError(
                f'Could not find node with name "{full_name}". '
                f'Did you mean: {", ".join(similar_names)}?'
            )
        return self._full_name_to_node[full_name]

    def _follow_field_expr_chain(
        self, target_assets: set[ModelAsset], expr_chain: ExpressionsChain
    ):
        # Change the target assets from the current ones to the
        # associated assets given the specified field name.
        if not expr_chain.fieldname:
            raise LanguageGraphException(
                '"field" step expression chain is missing fieldname.'
            )
        new_target_assets: set[ModelAsset] = set()
        new_target_assets.update(
            *(
                asset.associated_assets.get(expr_chain.fieldname, set())
                for asset in target_assets
            )
        )
        return new_target_assets

    def _follow_transitive_expr_chain(
        self,
        model: Model,
        target_assets: set[ModelAsset],
        expr_chain: ExpressionsChain
    ):
        if not expr_chain.sub_link:
            raise LanguageGraphException(
                '"transitive" step expression chain is missing sub link.'
            )

        new_assets = target_assets
        while new_assets := self._follow_expr_chain(
            model, new_assets, expr_chain.sub_link
        ):
            new_assets = new_assets.difference(target_assets)
            if not new_assets:
                break
            target_assets.update(new_assets)
        return target_assets

    def _follow_subtype_expr_chain(
        self,
        model: Model,
        target_assets: set[ModelAsset],
        expr_chain: ExpressionsChain
    ):
        if not expr_chain.sub_link:
            raise LanguageGraphException(
                '"subType" step expression chain is missing sub link.'
            )
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
                    f'Failed to find asset "{asset.type}" in the '
                    'language graph.'
                )
            lang_graph_subtype_asset = expr_chain.subtype
            if not lang_graph_subtype_asset:
                raise LookupError(
                    'Failed to find asset "{expr_chain.subtype}" in '
                    'the language graph.'
                )
            if lang_graph_asset.is_subasset_of(lang_graph_subtype_asset):
                selected_new_target_assets.add(asset)

        return selected_new_target_assets

    def _follow_union_intersection_difference_expr_chain(
        self,
        model: Model,
        target_assets: set[ModelAsset],
        expr_chain: ExpressionsChain
    ) -> set[Any]:
        # The set operators are used to combine the left hand and
        # right hand targets accordingly.
        if not expr_chain.left_link:
            raise LanguageGraphException(
                '"%s" step expression chain is missing the left link.',
                expr_chain.type
            )
        if not expr_chain.right_link:
            raise LanguageGraphException(
                '"%s" step expression chain is missing the right link.',
                expr_chain.type
            )
        lh_targets = self._follow_expr_chain(
            model, target_assets, expr_chain.left_link
        )
        rh_targets = self._follow_expr_chain(
            model, target_assets, expr_chain.right_link
        )

        if expr_chain.type == 'union':
            # Once the assets become hashable set operations should be
            # used instead.
            return lh_targets.union(rh_targets)

        if expr_chain.type == 'intersection':
            return lh_targets.intersection(rh_targets)

        if expr_chain.type == 'difference':
            return lh_targets.difference(rh_targets)

        raise ValueError("Expr chain must be of type union, intersectin or difference")

    def _follow_collect_expr_chain(
        self,
        model: Model,
        target_assets: set[ModelAsset],
        expr_chain: ExpressionsChain
    ) -> set[Any]:
        if not expr_chain.left_link:
            raise LanguageGraphException(
                '"collect" step expression chain missing the left link.'
            )
        if not expr_chain.right_link:
            raise LanguageGraphException(
                '"collect" step expression chain missing the right link.'
            )
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

    def _follow_expr_chain(
        self,
        model: Model,
        target_assets: set[ModelAsset],
        expr_chain: ExpressionsChain | None
    ) -> set[Any]:
        """Recursively follow a language graph expressions chain on an instance
        model.

        Arguments:
        ---------
        model           - a maltoolbox.model.Model on which to follow the
                          expressions chain
        target_assets   - the set of assets that this expressions chain
                          should apply to. Initially it will contain the
                          asset to which the attack step belongs
        expr_chain      - the expressions chain we are following

        Return:
        ------
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
                json.dumps(expr_chain.to_dict(), indent=2)
            )

        match (expr_chain.type):
            case 'union' | 'intersection' | 'difference':
                return self._follow_union_intersection_difference_expr_chain(
                    model, target_assets, expr_chain
                )

            case 'field':
                return self._follow_field_expr_chain(target_assets, expr_chain)

            case 'transitive':
                return self._follow_transitive_expr_chain(model, target_assets, expr_chain)

            case 'subType':
                return self._follow_subtype_expr_chain(model, target_assets, expr_chain)

            case 'collect':
                return self._follow_collect_expr_chain(model, target_assets, expr_chain)

            case _:
                msg = 'Unknown attack expressions chain type: %s'
                logger.error(
                    msg,
                    expr_chain.type
                )
                raise AttackGraphStepExpressionError(
                    msg % expr_chain.type
                )

    def _get_existance_status(
        self,
        model: Model,
        asset: ModelAsset,
        attack_step: LanguageGraphAttackStep
    ) -> bool | None:
        """Get existance status of a step"""
        if attack_step.type not in ('exist', 'notExist'):
            # No existence status for other type of steps
            return None

        existence_status = False
        for requirement in attack_step.requires:
            target_assets = self._follow_expr_chain(
                model, set([asset]), requirement
            )
            # If the step expression resolution yielded
            # the target assets then the required assets
            # exist in the model.
            if target_assets:
                existence_status = True
                break

        return existence_status

    def _get_ttc_dist(
        self,
        asset: ModelAsset,
        attack_step: LanguageGraphAttackStep
    ):
        """Get step ttc distribution based on language
        and possibly overriding defense status
        """
        ttc_dist = copy.deepcopy(attack_step.ttc)
        if attack_step.type ==  'defense':
            if attack_step.name in asset.defenses:
                # If defense status was set in model, set ttc accordingly
                defense_value = float(asset.defenses[attack_step.name])
                ttc_dist = {
                    'arguments': [defense_value],
                    'name': 'Bernoulli',
                    'type': 'function'
                }
                logger.debug(
                    'Setting defense \"%s\" to "%s".',
                    asset.name + ":" + attack_step.name, defense_value
                )
        return ttc_dist

    def _generate_graph(self, model: Model) -> None:
        """Generate the attack graph from model and MAL language."""
        self.nodes = {}
        self._full_name_to_node = {}

        self._create_nodes_from_model(model)
        self._link_nodes_by_language(model)

    def _create_nodes_from_model(self, model: Model) -> None:
        """Create attack graph nodes for all model assets."""
        for asset in model.assets.values():
            asset.attack_step_nodes = []
            for attack_step in asset.lg_asset.attack_steps.values():
                node = self.add_node(
                    lg_attack_step=attack_step,
                    model_asset=asset,
                    ttc_dist=self._get_ttc_dist(asset, attack_step),
                    existence_status=(
                        self._get_existance_status(model, asset, attack_step)
                    ),
                )
                asset.attack_step_nodes.append(node)

    def _link_nodes_by_language(self, model: Model) -> None:
        """Establish parent-child links between nodes."""
        for ag_node in self.nodes.values():
            self._link_node_children(model, ag_node)

    def _link_node_children(self, model: Model, ag_node: AttackGraphNode) -> None:
        """Link one node to its children."""
        if not ag_node.model_asset:
            raise AttackGraphException('Attack graph node is missing asset link')

        lg_asset = self.lang_graph.assets[ag_node.model_asset.type]
        lg_attack_step: LanguageGraphAttackStep | None = (
            lg_asset.attack_steps[ag_node.name]
        )
        while lg_attack_step:
            for child_type, expr_chains in lg_attack_step.children.items():
                for expr_chain in expr_chains:
                    self._link_from_expr_chain(model, ag_node, child_type, expr_chain)
            if lg_attack_step.overrides:
                break
            lg_attack_step = lg_attack_step.inherits

    def _link_from_expr_chain(
        self,
        model: Model,
        ag_node: AttackGraphNode,
        child_type: LanguageGraphAttackStep,
        expr_chain: ExpressionsChain | None,
    ) -> None:
        """Link a node to targets from a specific expression chain."""
        if not ag_node.model_asset:
            raise AttackGraphException(
                "Need model asset connection to generate graph"
            )

        target_assets = self._follow_expr_chain(model, {ag_node.model_asset}, expr_chain)
        for target_asset in target_assets:
            if not target_asset:
                continue
            target_node = self.get_node_by_full_name(
                f"{target_asset.name}:{child_type.name}"
            )
            if not target_node:
                raise AttackGraphStepExpressionError(
                    f'Failed to find target node "{target_asset.name}:{child_type.name}" '
                    f'for "{ag_node.full_name}"({ag_node.id})'
                )
            logger.debug(
                'Linking attack step "%s"(%d) to attack step "%s"(%d)',
                ag_node.full_name, ag_node.id,
                target_node.full_name, target_node.id
            )
            ag_node.children.add(target_node)
            target_node.parents.add(ag_node)

    def _get_similar_full_names(self, q: str) -> list[str]:
        """Return a list of node full names that are similar to `q`"""
        shortest_dist = 100
        similar_names = []
        for full_name in self._full_name_to_node:
            dist = levenshtein_distance(q, full_name)
            if dist == shortest_dist:
                similar_names.append(full_name)
            elif dist < shortest_dist:
                similar_names = [full_name]
                shortest_dist = dist
        return similar_names

    def regenerate_graph(self) -> None:
        """Regenerate the attack graph based on the original model instance and
        the MAL language specification provided at initialization.
        """
        self.nodes = {}
        assert self.model, "Model required to generate graph"
        self._generate_graph(self.model)

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
        self.next_node_id = max(node_id + 1, self.next_node_id)

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
        self._full_name_to_node[node.full_name] = node

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

        if not isinstance(node.id, int):
            raise ValueError('Invalid node id.')
        del self.nodes[node.id]
        del self._full_name_to_node[node.full_name]
