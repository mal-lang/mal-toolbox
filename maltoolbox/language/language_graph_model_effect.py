"""LanguageGraphAttackStep functionality
- Represents a step (type) defined in a MAL language
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, TypeAlias

from maltoolbox.language.expression_chain import ExprType
from maltoolbox.language.step_expression_processor import (
    process_assoc_op_step_expression,
    process_step_expression,
)

if TYPE_CHECKING:
    from maltoolbox.language.expression_chain import ExpressionsChain
    from maltoolbox.language.language_graph_asset import LanguageGraphAsset


class AssocTraversal(NamedTuple):
    """A reference to assets by role name, optionally filtered by asset type and quantity."""
    field_name: str
    asset_filter: LanguageGraphAsset | None
    quantity_filter: int | None

SELF_TRAVERSAL = AssocTraversal(field_name="self", asset_filter=None, quantity_filter=None)

class GlobAssocTraversal(NamedTuple):
    """A glob on the traversal chain."""
    pattern: AssocTraversalChain

class SetOperation(Enum):
    UNION = "UNION"
    DIFFERENCE = "DIFFERENCE"
    INTERSECTION = "INTERSECTION"

class AssocSet(NamedTuple):
    """A set operation between the results of two AssocTraversalChains"""
    set_op: SetOperation
    left: AssocTraversalChain
    right: AssocTraversalChain

AssocTraversalChain: TypeAlias = list[AssocTraversal | GlobAssocTraversal | AssocSet]

class DynTarget(NamedTuple):
    """A target in a dynamic sentence"""
    assoc_op: bool  # Decides if we are adding/removing assets or connections to assets
    assoc_traversal: AssocTraversalChain


class ModelEffectType(Enum):
    """The type of effect on the model instance, i.e. addition or subtraction."""
    ADDITIVE = "ADDITIVE"
    SUBTRACTIVE = "SUBTRACTIVE"

@dataclass
class LanguageGraphModelEffect:
    """An effect on the model instance triggered by compromising the attack step."""
    model_effect_type: ModelEffectType
    base: AssocTraversalChain
    targets: list[DynTarget]  # Assumes ^ between targets


def build_model_effect(
    assets: dict[str, LanguageGraphAsset],
    target_asset: LanguageGraphAsset,
    step_expression: dict,
    lang_spec,
    is_additive: bool
    ) -> LanguageGraphModelEffect:
    """Build a model effect from a step expression"""

    assert step_expression["type"] == "dyn_sentence", "Only dynamic sentences can be used to build model effects"
    model_effect_type = ModelEffectType.ADDITIVE if is_additive else ModelEffectType.SUBTRACTIVE

    def parse_assoc_traversal(expr_chain: ExpressionsChain | None) -> AssocTraversalChain:
        """Create a list of AssocTraversal from an expression chain"""

        if expr_chain is None:
            return []
        elif expr_chain.type == ExprType.COLLECT:
            left = parse_assoc_traversal(expr_chain.left_link)
            right = parse_assoc_traversal(expr_chain.right_link)
            return left + right
        elif expr_chain.type == ExprType.FIELD:
            assert expr_chain.fieldname is not None, "Fieldname must be set for FIELD expression"
            return [AssocTraversal(field_name=expr_chain.fieldname, asset_filter=None, quantity_filter=None)]

        elif expr_chain.type == ExprType.SUBTYPE:
            ret = parse_assoc_traversal(expr_chain.sub_link)
            if isinstance(ret[-1], AssocTraversal):
                ret[-1] = ret[-1]._replace(asset_filter=expr_chain.subtype)
            elif isinstance(ret[-1], GlobAssocTraversal) and isinstance(ret[-1].pattern[-1], AssocTraversal):
                ret[-1].pattern[-1] = ret[-1].pattern[-1]._replace(asset_filter=expr_chain.subtype)
            else:
                raise ValueError("Unexpected traversal chain structure for SUBTYPE expression")
            return ret
        elif expr_chain.type == ExprType.TRANSITIVE:
            pattern = parse_assoc_traversal(expr_chain.sub_link)
            return [GlobAssocTraversal(pattern=pattern)]
        elif expr_chain.type == ExprType.UNION:
            left = parse_assoc_traversal(expr_chain.left_link)
            right = parse_assoc_traversal(expr_chain.right_link)
            return [AssocSet(SetOperation.UNION, left, right)]
        elif expr_chain.type == ExprType.DIFFERENCE:
            left = parse_assoc_traversal(expr_chain.left_link)
            right = parse_assoc_traversal(expr_chain.right_link)
            return [AssocSet(SetOperation.DIFFERENCE, left, right)]
        elif expr_chain.type == ExprType.INTERSECTION:
            left = parse_assoc_traversal(expr_chain.left_link)
            right = parse_assoc_traversal(expr_chain.right_link)
            return [AssocSet(SetOperation.INTERSECTION, left, right)]

        raise ValueError(f"Unexpected expression chain type: {expr_chain.type}")

    def build_assoc_traversals(expr_chain: ExpressionsChain | None) -> AssocTraversalChain:
        """Build a list of lists of AssocTraversal from an expression chain, splitting on unions"""

        if expr_chain is None:
            traversals: AssocTraversalChain = [deepcopy(SELF_TRAVERSAL)]
        else:
            traversals = parse_assoc_traversal(expr_chain)
        return traversals

    base_expr = step_expression["base"]
    target_exprs = step_expression["targets"]

    base_target_asset, base_expr_chain, base_step = process_step_expression(assets, target_asset, None, base_expr, lang_spec)
    assert not base_step, "Base can not refer to an attack step in a dynamic sentence"
    base = build_assoc_traversals(base_expr_chain)

    targets = []
    for target_expr in target_exprs:
        is_assoc_op = (target_expr["type"] == "assoc_op")
        process_function = process_assoc_op_step_expression if is_assoc_op else process_step_expression
        # If we are doing link addition the instigating asset is the asset which defines the step,
        # otherwise the instigating asset are the assets collected from the base expression.
        # See for further details: https://github.com/mal-lang/mal-toolbox/pull/244#issuecomment-5190495429
        if is_assoc_op and model_effect_type == ModelEffectType.ADDITIVE:
            _, target_expr_chain, target_step = process_function(assets, target_asset, None, target_expr, lang_spec)
        else:
            _, target_expr_chain, target_step = process_function(assets, base_target_asset, None, target_expr, lang_spec)
        assert not target_step, "Targets can not refer to an attack step in a dynamic sentence"

        if target_expr_chain:
            if target_expr_chain.type == ExprType.ASSOC_OP:
                assoc_op = True
                target_expr_chain = target_expr_chain.sub_link
            else:
                assoc_op = False
            assoc_traversal = build_assoc_traversals(target_expr_chain)
            targets.append(DynTarget(assoc_op=assoc_op, assoc_traversal=assoc_traversal))
        else:
            assoc_op = False
            self_traversal: AssocTraversalChain = [deepcopy(SELF_TRAVERSAL)]
            targets.append(DynTarget(assoc_op=assoc_op, assoc_traversal=self_traversal))

    return LanguageGraphModelEffect(model_effect_type=model_effect_type, base=base, targets=targets)