"""Graph generation functions to update the attack graph when new assets are added to the model."""

import logging

from maltoolbox.attackgraph.generate import (
    follow_expr_chain,
    get_existance_status,
)
from maltoolbox.attackgraph.ttcs import get_ttc_dist
from maltoolbox.language import LanguageGraphAttackStep
from maltoolbox.language.expression_chain import (
    ExpressionsChain,
    ExprType,
    chain_fieldnames,
)

from ..exceptions import (
    AttackGraphException,
)
from ..model import Model, ModelAsset
from .node import AttackGraphNode

logger = logging.getLogger(__name__)

def create_nodes_from_assets(
    assets: set[ModelAsset], starting_id: int, model: Model
) -> tuple[dict, list, list, dict]:
    id_to_node = {}
    full_name_to_node = {}
    attack_steps = []
    defense_steps = []

    node_id = starting_id
    for asset in assets:
        asset.attack_step_nodes = []  # TODO: deprecate this
        for lg_attack_step in asset.lg_asset.attack_steps.values():
            node = AttackGraphNode(
                node_id=node_id,
                lg_attack_step=lg_attack_step,
                model_asset=asset,
                ttc_dist=get_ttc_dist(asset, lg_attack_step),
                existence_status=(get_existance_status(model, asset, lg_attack_step)),
            )
            asset.attack_step_nodes.append(node)  # TODO: deprecate this
            id_to_node[node.id] = node
            full_name_to_node[node.full_name] = node

            if node.type in ('or', 'and'):
                attack_steps.append(node)
            elif node.type == 'defense':
                defense_steps.append(node)

            node_id += 1

    return id_to_node, attack_steps, defense_steps, full_name_to_node

def switch_fieldname(asset: ModelAsset, fieldname: str) -> str:
    """Given an asset and a fieldname, return the other fieldname in the association."""
    assoc_def = asset.lg_asset.associations.get(fieldname)
    if not assoc_def:
        raise AttackGraphException(
            f'Fieldname {fieldname} not found in associations of asset {asset.name}'
        )
    if fieldname == assoc_def.left_field.fieldname:
        return assoc_def.right_field.fieldname
    elif fieldname == assoc_def.right_field.fieldname:
        return assoc_def.left_field.fieldname
    else:
        raise AttackGraphException(
            f'Fieldname {fieldname} not found in association {assoc_def.name}'
        )

def correct_node_children_on_modified_assoc(
    model: Model,
    affected_node: AttackGraphNode,
    full_name_to_node: dict[str, AttackGraphNode],
) -> None:
    """Recompute ag_node's children from the model's current associations,
    since the expression chain's actual target may be several hops past
    the association that changed."""
    if not affected_node.model_asset:
        raise AttackGraphException('Attack graph node is missing asset link')
    model_asset = affected_node.model_asset

    lg_asset = model.lang_graph.assets[model_asset.type]
    lg_attack_step: LanguageGraphAttackStep | None = lg_asset.attack_steps[affected_node.name]

    correct_children: set[AttackGraphNode] = set()
    while lg_attack_step:
        for child_type, expr_chains in lg_attack_step.children.items():
            for expr_chain in expr_chains:
                for target_asset in follow_expr_chain(model, {model_asset}, expr_chain):
                    target_node = full_name_to_node.get(f'{target_asset.name}:{child_type.name}')
                    if target_node is None:
                        raise AttackGraphException(
                            f'Failed to find target node "{target_asset.name}:{child_type.name}" '
                            f'for "{affected_node.full_name}"({affected_node.id})'
                        )
                    correct_children.add(target_node)
        if lg_attack_step.overrides:
            break
        lg_attack_step = lg_attack_step.inherits

    for target_node in correct_children - affected_node.children:
        logger.debug(
            'Linking attack step "%s"(%d) to attack step "%s"(%d)',
            affected_node.full_name, affected_node.id, target_node.full_name, target_node.id,
        )
        affected_node.children.add(target_node)
        target_node.parents.add(affected_node)

    for target_node in affected_node.children - correct_children:
        logger.debug(
            'Unlinking attack step "%s"(%d) from attack step "%s"(%d)',
            affected_node.full_name, affected_node.id, target_node.full_name, target_node.id,
        )
        affected_node.children.discard(target_node)
        target_node.parents.discard(affected_node)

def nodes_to_be_removed(
    removed_assets: set[ModelAsset], full_name_to_node: dict[str, AttackGraphNode]
) -> set[AttackGraphNode]:
    """Remove nodes from the attack graph that correspond to the given assets."""
    removal_candidates = set()
    for asset in removed_assets:
        for lg_attack_step in asset.lg_asset.attack_steps.values():
            node_full_name = f'{asset.name}:{lg_attack_step.name}'
            node = full_name_to_node.get(node_full_name)
            if not node:
                raise AttackGraphException(
                    f'Failed to find {lg_attack_step.full_name} for removed asset {asset.name}.'
                )
            removal_candidates.add(node)
    return removal_candidates

def assoc_affected_expr_chain(
    model: Model,
    instigating_assets: set[ModelAsset],
    affected_assoc_dict: dict[ModelAsset, dict[str, set[ModelAsset]]],
    expr_chain: ExpressionsChain | None,
    modified_fieldnames: frozenset[str] | None = None,
) -> bool:
    """Check whether evaluating expr_chain starting from instigating_assets
    passes through any association recorded in affected_assoc_dict."""
    if expr_chain is None or not instigating_assets:
        return False
    if modified_fieldnames is None:
        modified_fieldnames = frozenset(
            fieldname for fields in affected_assoc_dict.values() for fieldname in fields
        )
    if not (expr_chain.fieldnames & modified_fieldnames):
        return False
    if expr_chain.type == ExprType.FIELD:
        assert expr_chain.fieldname is not None, "Fieldname should not be None for FIELD type"
        return any(
            expr_chain.fieldname in affected_assoc_dict.get(instigating_asset, {})
            for instigating_asset in instigating_assets
        )
    elif expr_chain.type in (ExprType.UNION, ExprType.INTERSECTION, ExprType.DIFFERENCE):
        # Both sides are evaluated starting from the same assets.
        return (
            assoc_affected_expr_chain(model, instigating_assets, affected_assoc_dict, expr_chain.left_link, modified_fieldnames)
            or assoc_affected_expr_chain(model, instigating_assets, affected_assoc_dict, expr_chain.right_link, modified_fieldnames)
        )
    elif expr_chain.type == ExprType.COLLECT:
        # The right hand side is evaluated starting from the assets reached
        # by the left hand side, not from the original instigating assets.
        if (
            chain_fieldnames(expr_chain.left_link) & modified_fieldnames
            and assoc_affected_expr_chain(model, instigating_assets, affected_assoc_dict, expr_chain.left_link, modified_fieldnames)
        ):
            return True
        if not (chain_fieldnames(expr_chain.right_link) & modified_fieldnames):
            return False
        next_assets = follow_expr_chain(model, instigating_assets, expr_chain.left_link)
        return assoc_affected_expr_chain(model, next_assets, affected_assoc_dict, expr_chain.right_link, modified_fieldnames)
    elif expr_chain.type == ExprType.SUBTYPE:
        return assoc_affected_expr_chain(model, instigating_assets, affected_assoc_dict, expr_chain.sub_link, modified_fieldnames)
    elif expr_chain.type == ExprType.TRANSITIVE:
        assert expr_chain.sub_link is not None, "Sub link should not be None for TRANSITIVE type"
        # Check every depth of the transitive closure, since the modified
        # association may be several hops away from instigating_assets.
        frontier = set(instigating_assets)
        visited: set[ModelAsset] = set()
        while frontier:
            if assoc_affected_expr_chain(model, frontier, affected_assoc_dict, expr_chain.sub_link, modified_fieldnames):
                return True
            visited |= frontier
            frontier = follow_expr_chain(model, frontier, expr_chain.sub_link) - visited
        return False
    else:
        raise ValueError(f"Unknown expression chain type: {expr_chain.type}")

def assoc_left_assets(
    model: Model,
    affected_assoc_dict: dict[ModelAsset, dict[str, set[ModelAsset]]],
    expr_chain: ExpressionsChain | None,
    modified_fieldnames: frozenset[str],
) -> set[ModelAsset]:
    """Return every left asset from modified associations,
    based on if the expression chain reaches the association.
    
    Only valid for additive chains, whose results union across assets.

    Arguments:
    ---------
    model                   - the model the assets belong to
    affected_assoc_dict     - per-asset, per-fieldname sets of associated
                              assets that were modified (added or removed)
    expr_chain              - the expressions chain to walk backward from
    modified_fieldnames     - every fieldname appearing anywhere in
                              affected_assoc_dict, used to skip sub-chains
                              that can't have been affected

    Return:
    ------
    The set of left assets, from which the expression chain reaches a modified association.

    """
    if expr_chain is None or not (expr_chain.fieldnames & modified_fieldnames):
        return set()

    if expr_chain.type == ExprType.FIELD:
        assert expr_chain.fieldname is not None, "Fieldname should not be None for FIELD type"
        # Fieldname strings aren't unique across associations, so also match
        # on the association to avoid an unrelated field of the same name.
        return {
            asset for asset, fields in affected_assoc_dict.items()
            if expr_chain.fieldname in fields
            and asset.lg_asset.associations.get(expr_chain.fieldname) == expr_chain.association
        }
    elif expr_chain.type in (ExprType.UNION, ExprType.INTERSECTION, ExprType.DIFFERENCE):
        return (
            assoc_left_assets(model, affected_assoc_dict, expr_chain.left_link, modified_fieldnames)
            | assoc_left_assets(model, affected_assoc_dict, expr_chain.right_link, modified_fieldnames)
        )
    elif expr_chain.type == ExprType.COLLECT:
        roots: set[ModelAsset] = set()
        if chain_fieldnames(expr_chain.left_link) & modified_fieldnames:
            roots |= assoc_left_assets(model, affected_assoc_dict, expr_chain.left_link, modified_fieldnames)
        if chain_fieldnames(expr_chain.right_link) & modified_fieldnames:
            right_roots = assoc_left_assets(model, affected_assoc_dict, expr_chain.right_link, modified_fieldnames)
            if right_roots:
                reverse_left = model.lang_graph.reverse_expr_chain(expr_chain.left_link, None)
                roots |= follow_expr_chain(model, set(right_roots), reverse_left)
        return roots
    elif expr_chain.type == ExprType.SUBTYPE:
        return assoc_left_assets(model, affected_assoc_dict, expr_chain.sub_link, modified_fieldnames)
    elif expr_chain.type == ExprType.TRANSITIVE:
        assert expr_chain.sub_link is not None, "Sub link should not be None for TRANSITIVE type"
        seed_roots = assoc_left_assets(model, affected_assoc_dict, expr_chain.sub_link, modified_fieldnames)
        reverse_sub = model.lang_graph.reverse_expr_chain(expr_chain.sub_link, None)
        roots = set(seed_roots)
        frontier = set(seed_roots)
        while frontier:
            frontier = follow_expr_chain(model, frontier, reverse_sub) - roots
            roots |= frontier
        return roots
    else:
        raise ValueError(f"Unknown expression chain type: {expr_chain.type}")

def assoc_affected_nodes(model: Model, affected_assoc_dict: dict[ModelAsset, dict[str, set[ModelAsset]]], full_name_to_node: dict[str, AttackGraphNode]) -> set[AttackGraphNode]:
    """Return every attack graph node whose children are reached via an
    association that was added or removed."""
    modified_fieldnames = frozenset(
        fieldname for fields in affected_assoc_dict.values() for fieldname in fields
    )

    candidate_steps: set[tuple[str, str]] = set()
    for fieldname in modified_fieldnames:
        candidate_steps |= model.lang_graph.fieldname_to_candidate_steps.get(fieldname, set())

    # Built lazily, only for non-additive chains.
    assets_by_type: dict[str, list[ModelAsset]] | None = None

    ret_nodes = set()
    for asset_type, step_name in candidate_steps:
        lg_step = model.lang_graph.assets[asset_type].attack_steps[step_name]
        affected_assets: set[ModelAsset] = set()
        for expr_chains in lg_step.children.values():
            for expr_chain in expr_chains:
                if expr_chain is None:
                    continue
                if expr_chain.is_additive:
                    affected_assets |= assoc_left_assets(
                        model, affected_assoc_dict, expr_chain, modified_fieldnames
                    )
                    continue
                if assets_by_type is None:
                    assets_by_type = {}
                    for asset in model.assets.values():
                        assets_by_type.setdefault(asset.type, []).append(asset)
                for asset in assets_by_type.get(asset_type, []):
                    if assoc_affected_expr_chain(model, {asset}, affected_assoc_dict, expr_chain, modified_fieldnames):
                        affected_assets.add(asset)
        for asset in affected_assets:
            # A shared association can be inherited by sibling types that
            # don't all define step_name themselves (e.g. two subtypes of
            # the same abstract asset), so re-check before the lookup.
            if step_name not in asset.lg_asset.attack_steps:
                continue
            ret_nodes.add(full_name_to_node[f'{asset.name}:{step_name}'])
    return ret_nodes