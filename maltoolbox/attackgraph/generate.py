"""Graph generation functions"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from maltoolbox.attackgraph.node_getters import get_node_by_full_name
from maltoolbox.attackgraph.ttcs import get_ttc_dist

from ..exceptions import (
    AttackGraphException,
    AttackGraphStepExpressionError,
    LanguageGraphException,
)
from ..language import ExpressionsChain, LanguageGraphAttackStep
from ..model import Model
from .node import AttackGraphNode

if TYPE_CHECKING:
    from typing import Any
    from ..model import ModelAsset

logger = logging.getLogger(__name__)

def link_node_children(
    model: Model,
    ag_node: AttackGraphNode,
    full_name_to_node: dict[str, AttackGraphNode]
) -> None:
    """Link one node to its children."""
    if not ag_node.model_asset:
        raise AttackGraphException('Attack graph node is missing asset link')

    lg_asset = model.lang_graph.assets[ag_node.model_asset.type]
    lg_attack_step: LanguageGraphAttackStep | None = (
        lg_asset.attack_steps[ag_node.name]
    )
    while lg_attack_step:
        for child_type, expr_chains in lg_attack_step.children.items():
            for expr_chain in expr_chains:
                link_from_expr_chain(
                    model, ag_node, child_type, expr_chain, full_name_to_node
                )
        if lg_attack_step.overrides:
            break
        lg_attack_step = lg_attack_step.inherits


def link_from_expr_chain(
    model: Model,
    ag_node: AttackGraphNode,
    child_type: LanguageGraphAttackStep,
    expr_chain: ExpressionsChain | None,
    full_name_to_node: dict[str, AttackGraphNode]
) -> None:
    """Link a node to targets from a specific expression chain."""
    if not ag_node.model_asset:
        raise AttackGraphException(
            "Need model asset connection to generate graph"
        )

    target_assets = follow_expr_chain(model, {ag_node.model_asset}, expr_chain)
    for target_asset in target_assets:
        if not target_asset:
            continue
        target_node = get_node_by_full_name(
            full_name_to_node, f"{target_asset.name}:{child_type.name}"
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


def follow_field_expr_chain(
    target_assets: set[ModelAsset], expr_chain: ExpressionsChain
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


def follow_transitive_expr_chain(
    model: Model,
    target_assets: set[ModelAsset],
    expr_chain: ExpressionsChain
):
    if not expr_chain.sub_link:
        raise LanguageGraphException(
            '"transitive" step expression chain is missing sub link.'
        )

    new_assets = target_assets
    while new_assets := follow_expr_chain(
        model, new_assets, expr_chain.sub_link
    ):
        new_assets = new_assets.difference(target_assets)
        if not new_assets:
            break
        target_assets.update(new_assets)
    return target_assets


def follow_subtype_expr_chain(
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
        follow_expr_chain(
            model, target_assets, expr_chain.sub_link
        )
    )
    selected_new_target_assets = set()
    for asset in new_target_assets:
        lang_graph_asset = model.lang_graph.assets[asset.type]
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

def follow_union_intersection_difference_expr_chain(
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
    lh_targets = follow_expr_chain(
        model, target_assets, expr_chain.left_link
    )
    rh_targets = follow_expr_chain(
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


def follow_collect_expr_chain(
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
    lh_targets = follow_expr_chain(
        model,
        target_assets,
        expr_chain.left_link
    )
    rh_targets = set()
    for lh_target in lh_targets:
        rh_targets |= follow_expr_chain(
            model,
            {lh_target},
            expr_chain.right_link
        )
    return rh_targets


def follow_expr_chain(
    model: Model,
    target_assets: set[ModelAsset],
    expr_chain: Optional[ExpressionsChain]
):
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
            return follow_union_intersection_difference_expr_chain(
                model, target_assets, expr_chain
            )

        case 'field':
            return follow_field_expr_chain(target_assets, expr_chain)

        case 'transitive':
            return follow_transitive_expr_chain(model, target_assets, expr_chain)

        case 'subType':
            return follow_subtype_expr_chain(model, target_assets, expr_chain)

        case 'collect':
            return follow_collect_expr_chain(model, target_assets, expr_chain)

        case _:
            msg = 'Unknown attack expressions chain type: %s'
            logger.error(
                msg,
                expr_chain.type
            )
            raise AttackGraphStepExpressionError(
                msg % expr_chain.type
            )


def link_nodes_by_language(
    model: Model, full_name_to_node: dict[str, AttackGraphNode]
):
    for ag_node in full_name_to_node.values():
        link_node_children(model, ag_node, full_name_to_node)


def create_nodes_from_model(model: Model):
    id_to_node = {}
    full_name_to_node = {}
    attack_steps = []
    defense_steps = []

    node_id = 0
    for asset in model.assets.values():
        asset.attack_step_nodes = [] # TODO: deprecate this
        for lg_attack_step in asset.lg_asset.attack_steps.values():
            node = AttackGraphNode(
                node_id=node_id,
                lg_attack_step=lg_attack_step,
                model_asset=asset,
                ttc_dist=get_ttc_dist(asset, lg_attack_step),
                existence_status=(
                    get_existance_status(model, asset, lg_attack_step)
                ),
            )
            asset.attack_step_nodes.append(node) # TODO: deprecate this
            id_to_node[node.id] = node
            full_name_to_node[node.full_name] = node

            if node.type in ('or', 'and'):
                attack_steps.append(node)
            elif node.type == 'defense':
                defense_steps.append(node)
    
            node_id += 1

    return id_to_node, attack_steps, defense_steps, full_name_to_node


def generate_graph(model: Model):
    id_to_node, attack_steps, defense_steps, full_name_to_node = create_nodes_from_model(model)
    link_nodes_by_language(model, full_name_to_node)
    return id_to_node, attack_steps, defense_steps, full_name_to_node


def get_existance_status(
        model: Model,
        asset: ModelAsset,
        lg_attack_step: LanguageGraphAttackStep
    ):

    if lg_attack_step.type not in ('exist', 'notExist'):
        # No existence status for other type of steps
        return None

    existence_status = False
    for requirement in lg_attack_step.requires:
        target_assets = follow_expr_chain(
            model, set([asset]), requirement
        )
        # If the step expression resolution yielded
        # the target assets then the required assets
        # exist in the model.
        if target_assets:
            existence_status = True
            break
    return existence_status
