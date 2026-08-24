"""Graph generation functions to update the attack graph when new assets are added to the model."""

import logging
from functools import cache

from maltoolbox.attackgraph.generate import (
    get_existance_status,
    link_from_expr_chain,
)
from maltoolbox.attackgraph.ttcs import get_ttc_dist
from maltoolbox.language import LanguageGraph, LanguageGraphAttackStep
from maltoolbox.language.expression_chain import ExpressionsChain, ExprType

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

@cache
def get_all_field_names(lang_graph: LanguageGraph) -> set[str]:
    """Get all field names from the language graph."""
    field_names = set()
    for assoc in lang_graph.associations:
        field_names.add(assoc.left_field.fieldname)
        field_names.add(assoc.right_field.fieldname)
    return field_names

def assoc_in_expr_chain(expr_chain: ExpressionsChain, assocs: dict[str, set[ModelAsset]], all_field_names: set[str]) -> set[str]:
    """Check if an association is in the expression chain."""
    if expr_chain.type == ExprType.FIELD:
        assert expr_chain.fieldname is not None, "Fieldname should not be None for FIELD type"
        return {expr_chain.fieldname}
    elif expr_chain.type in (ExprType.UNION, ExprType.INTERSECTION, ExprType.DIFFERENCE) or expr_chain.type == ExprType.COLLECT:
        assert expr_chain.left_link is not None and expr_chain.right_link is not None, "Left and right links should not be None for UNION, INTERSECTION, DIFFERENCE, or COLLECT types"
        return assoc_in_expr_chain(expr_chain.left_link, assocs, all_field_names) | assoc_in_expr_chain(expr_chain.right_link, assocs, all_field_names)
    elif expr_chain.type == ExprType.SUBTYPE:
        assert expr_chain.sub_link is not None, "Subtype should not be None for SUBTYPE type"
        return assoc_in_expr_chain(expr_chain.sub_link, assocs, all_field_names)
    elif expr_chain.type == ExprType.TRANSITIVE:
        # TODO: Handle this in a more efficient manner
        assert expr_chain.sub_link is not None, "Sub link should not be None for TRANSITIVE type"
        prepend_patterns = assoc_in_expr_chain(expr_chain.sub_link, assocs, all_field_names)
        return {field_name for field_name in all_field_names if any(field_name.startswith(pattern) for pattern in prepend_patterns)}
    else:
        raise ValueError(f"Unknown expression chain type: {expr_chain.type}")

def correct_node_children_on_modified_assoc(
    model: Model,
    ag_node: AttackGraphNode,
    full_name_to_node: dict[str, AttackGraphNode],
    new_assoc_dict: dict[str, set[ModelAsset]],
    removed_assoc_dict: dict[str, set[ModelAsset]],
    all_field_names_in_lang_graph: set[str]
) -> None:
    """Link one node to its children."""
    if not ag_node.model_asset:
        raise AttackGraphException('Attack graph node is missing asset link')

    lg_asset = model.lang_graph.assets[ag_node.model_asset.type]
    lg_attack_step: LanguageGraphAttackStep | None = lg_asset.attack_steps[ag_node.name]
    while lg_attack_step:
        for child_type, expr_chains in lg_attack_step.children.items():
            for expr_chain in expr_chains:

                # Child is in the same asset, so it should already be linked in the graph
                if expr_chain is None:
                    continue
                new_assocs = assoc_in_expr_chain(expr_chain, new_assoc_dict, all_field_names_in_lang_graph)
                if len(set(new_assoc_dict.keys()) & new_assocs) > 0:
                    link_from_expr_chain(
                        model, ag_node, child_type, expr_chain, full_name_to_node,
                    )
                removed_assocs = assoc_in_expr_chain(expr_chain, removed_assoc_dict, all_field_names_in_lang_graph)
                if len(set(removed_assoc_dict.keys()) & removed_assocs) > 0:
                    removed_assoc_assets = {
                        asset
                        for fieldname in removed_assocs
                        for asset in removed_assoc_dict.get(fieldname, set())
                    }
                    for removed_assoc_asset in removed_assoc_assets:
                        unlink_from_associated_asset(
                            ag_node, child_type, full_name_to_node, removed_assoc_asset
                        )
                else:
                    logger.debug(
                        f"Skipping linking of {ag_node.full_name} to step of type {child_type.full_name} via {expr_chain.fieldname} because the association was not modified."
                    )
        if lg_attack_step.overrides:
            break
        lg_attack_step = lg_attack_step.inherits

def unlink_from_associated_asset(
    ag_node: AttackGraphNode,
    child_type: LanguageGraphAttackStep,
    full_name_to_node: dict[str, AttackGraphNode],
    associated_asset: ModelAsset
) -> None:
    """Unlink a node from targets from a specific expression chain."""
    if not ag_node.model_asset:
        raise AttackGraphException('Need model asset connection to generate graph')
    
    target_node: AttackGraphNode | None = full_name_to_node.get(f'{associated_asset.name}:{child_type.name}')
    if not target_node:
        logger.debug(
            'Failed to unlink %s -> %s:%s, %s:%s already unlinked?',
            ag_node.full_name,
            associated_asset.name,
            child_type.name,
            associated_asset.name,
            child_type.name,
        )
        return

    logger.debug(
        'Unlinking attack step "%s"(%d) to attack step "%s"(%d)',
        ag_node.full_name,
        ag_node.id,
        target_node.full_name,
        target_node.id,
    )
    ag_node.children.discard(target_node)
    target_node.parents.discard(ag_node)

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

            
    