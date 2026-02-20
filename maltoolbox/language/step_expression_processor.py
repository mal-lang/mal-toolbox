from __future__ import annotations
import json
import logging
from typing import Any, Optional

from maltoolbox.language.expression_chain import ExprType, ExpressionsChain
from maltoolbox.language.language_graph_lookup import get_var_expr_for_asset
from maltoolbox.language.language_graph_asset import LanguageGraphAsset
from maltoolbox.exceptions import (
    LanguageGraphException,
    LanguageGraphAssociationError,
)

logger = logging.getLogger(__name__)

StepResult = tuple[
    LanguageGraphAsset,
    Optional[ExpressionsChain],
    Optional[str],
]

def process_attack_step_expression(
    target_asset: LanguageGraphAsset,
    step_expression: dict[str, Any]
) -> StepResult:
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
    assets: dict[str, LanguageGraphAsset],
    target_asset: LanguageGraphAsset,
    expr_chain: ExpressionsChain | None,
    step_expression: dict[str, Any],
    lang_spec
) -> StepResult:
    """The set operators are used to combine the left hand and right
    hand targets accordingly.
    """
    lh_target_asset, lh_expr_chain, _ = process_step_expression(
        assets,
        target_asset,
        expr_chain,
        step_expression['lhs'],
        lang_spec
    )
    rh_target_asset, rh_expr_chain, _ = process_step_expression(
        assets,
        target_asset,
        expr_chain,
        step_expression['rhs'],
        lang_spec
    )

    if lh_target_asset is None:
        raise ValueError(
            f"No lh target in step expression {step_expression}"
        )
    if rh_target_asset is None:
        raise ValueError(
            f"No rh target in step expression {step_expression}"
        )

    if not lh_target_asset.get_all_common_superassets(rh_target_asset):
        raise ValueError(
            "Set operation attempted between targets that do not share "
            f"any common superassets: {lh_target_asset.name} "
            f"and {rh_target_asset.name}!"
        )

    new_expr_chain = ExpressionsChain(
        type=ExprType(step_expression['type']),
        left_link=lh_expr_chain,
        right_link=rh_expr_chain
    )
    return (
        lh_target_asset,
        new_expr_chain,
        None
    )

def process_variable_step_expression(
    assets: dict[str, LanguageGraphAsset],
    target_asset: LanguageGraphAsset,
    step_expression: dict[str, Any],
    lang_spec
) -> StepResult:

    var_name = step_expression['name']
    var_target_asset, var_expr_chain = (
        resolve_variable(assets, target_asset, var_name, lang_spec)
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
    target_asset: LanguageGraphAsset,
    step_expression: dict[str, Any]
) -> StepResult:
    """Change the target asset from the current one to the associated
    asset given the specified field name and add the parent
    fieldname and association to the parent associations chain.
    """
    fieldname = step_expression['name']

    if target_asset is None:
        raise ValueError(
            f'Missing target asset for field "{fieldname}"!'
        )

    for association in target_asset.associations.values():
        if (
            association.left_field.fieldname == fieldname and
            target_asset.is_subasset_of(association.right_field.asset)
        ):
            return (
                association.left_field.asset,
                ExpressionsChain(
                    type=ExprType.FIELD,
                    fieldname=fieldname,
                    association=association
                ),
                None
            )

        if (
            association.right_field.fieldname == fieldname and
            target_asset.is_subasset_of(association.left_field.asset)
        ):
            return (
                association.right_field.asset,
                ExpressionsChain(
                    type=ExprType.FIELD,
                    fieldname=fieldname,
                    association=association
                ),
                None
            )
    raise LookupError(
        f'Failed to find field {fieldname} on asset {target_asset.name}!',
    )

def process_transitive_step_expression(
    assets: dict[str, LanguageGraphAsset],
    target_asset: LanguageGraphAsset,
    expr_chain: ExpressionsChain | None,
    step_expression: dict[str, Any],
    lang_spec
) -> StepResult:
    """Create a transitive tuple entry that applies to the next
    component of the step expression.
    """
    result_target_asset, result_expr_chain, _ = (
        process_step_expression(
            assets,
            target_asset,
            expr_chain,
            step_expression['stepExpression'],
            lang_spec
        )
    )
    new_expr_chain = ExpressionsChain(
        type=ExprType.TRANSITIVE,
        sub_link=result_expr_chain
    )
    return (
        result_target_asset,
        new_expr_chain,
        None
    )

def process_subType_step_expression(
    assets: dict[str, LanguageGraphAsset],
    target_asset: LanguageGraphAsset,
    expr_chain: ExpressionsChain | None,
    step_expression: dict[str, Any],
    lang_spec
) -> StepResult:
    """Create a subType tuple entry that applies to the next
    component of the step expression and changes the target
    asset to the subasset.
    """
    subtype_name = step_expression['subType']
    result_target_asset, result_expr_chain, _ = (
        process_step_expression(
            assets,
            target_asset,
            expr_chain,
            step_expression['stepExpression'],
            lang_spec
        )
    )

    if subtype_name not in assets:
        raise LanguageGraphException(
            f'Failed to find subtype {subtype_name}'
        )

    subtype_asset = assets[subtype_name]

    if result_target_asset is None:
        raise LookupError("Nonexisting asset for subtype")

    if not subtype_asset.is_subasset_of(result_target_asset):
        raise ValueError(
            f'Found subtype {subtype_name} which does not extend '
            f'{result_target_asset.name}, subtype cannot be resolved.'
        )

    new_expr_chain = ExpressionsChain(
        type=ExprType.SUBTYPE,
        sub_link=result_expr_chain,
        subtype=subtype_asset
    )
    return (
        subtype_asset,
        new_expr_chain,
        None
    )

def process_collect_step_expression(
    assets: dict[str, LanguageGraphAsset],
    target_asset: LanguageGraphAsset,
    expr_chain: ExpressionsChain | None,
    step_expression: dict[str, Any],
    lang_spec
) -> StepResult:
    """Apply the right hand step expression to left hand step
    expression target asset and parent associations chain.
    """
    lh_target_asset, lh_expr_chain, _ = process_step_expression(
        assets, target_asset, expr_chain, step_expression['lhs'], lang_spec
    )

    if lh_target_asset is None:
        raise ValueError(
            'No left hand asset in collect expression '
            f'{step_expression["lhs"]}'
        )

    rh_target_asset, rh_expr_chain, rh_attack_step_name = (
        process_step_expression(
            assets, lh_target_asset, None, step_expression['rhs'], lang_spec
        )
    )

    new_expr_chain = lh_expr_chain
    if rh_expr_chain:
        new_expr_chain = ExpressionsChain(
            type=ExprType.COLLECT,
            left_link=lh_expr_chain,
            right_link=rh_expr_chain
        )

    return (
        rh_target_asset,
        new_expr_chain,
        rh_attack_step_name
    )

def process_step_expression(
    assets: dict[str, LanguageGraphAsset],
    target_asset: LanguageGraphAsset,
    expr_chain: ExpressionsChain | None,
    step_expression: dict,
    lang_spec
) -> StepResult:
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

    result: StepResult

    if step_expression['type'] == 'attackStep':
        result = process_attack_step_expression(
            target_asset, step_expression
        )
    elif step_expression['type'] in ['union', 'intersection', 'difference']:
        result = process_set_operation_step_expression(
            assets, target_asset, expr_chain, step_expression, lang_spec
        )
    elif step_expression['type'] == 'variable':
        result = process_variable_step_expression(
            assets, target_asset, step_expression, lang_spec
        )
    elif step_expression['type'] == 'field':
        result = process_field_step_expression(
            target_asset, step_expression
        )
    elif step_expression['type'] == 'transitive':
        result = process_transitive_step_expression(
            assets, target_asset, expr_chain, step_expression, lang_spec
        )
    elif step_expression['type'] == 'subType':
        result = process_subType_step_expression(
            assets, target_asset, expr_chain, step_expression, lang_spec
        )
    elif step_expression['type'] == 'collect':
        result = process_collect_step_expression(
            assets, target_asset, expr_chain, step_expression, lang_spec
        )
    else:
        raise LookupError(
            f'Unknown attack step type: "{step_expression["type"]}"'
        )
    return result

def reverse_expr_chain(
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
    if expr_chain.type.is_binary():
        left_reverse_chain = \
            reverse_expr_chain(expr_chain.left_link, reverse_chain)
        right_reverse_chain = \
            reverse_expr_chain(expr_chain.right_link, reverse_chain)
        if expr_chain.type == ExprType.COLLECT:
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

    if expr_chain.type == ExprType.TRANSITIVE:
        result_reverse_chain = reverse_expr_chain(
            expr_chain.sub_link, reverse_chain)
        new_expr_chain = ExpressionsChain(
            type=ExprType.TRANSITIVE,
            sub_link=result_reverse_chain
        )
        return new_expr_chain

    if expr_chain.type == ExprType.FIELD:
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
            type=ExprType.FIELD,
            association=association,
            fieldname=opposite_fieldname
        )
        return new_expr_chain

    if expr_chain.type == ExprType.SUBTYPE:
        result_reverse_chain = reverse_expr_chain(
            expr_chain.sub_link,
            reverse_chain
        )
        new_expr_chain = ExpressionsChain(
            type=ExprType.SUBTYPE,
            sub_link=result_reverse_chain,
            subtype=expr_chain.subtype
        )
        return new_expr_chain

    else:
        msg = 'Unknown assoc chain element "%s"'
        logger.error(msg, expr_chain.type)
        raise LanguageGraphAssociationError(msg % expr_chain.type)

def resolve_variable(
    assets: dict[str, LanguageGraphAsset],
    asset: LanguageGraphAsset,
    var_name: str,
    lang_spec
) -> tuple[LanguageGraphAsset, Optional[ExpressionsChain]]:
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
        var_expr = get_var_expr_for_asset(asset.name, var_name, lang_spec)
        target_asset, expr_chain, _ = process_step_expression(
            assets, asset, None, var_expr, lang_spec
        )
        return (target_asset, expr_chain)
    return asset.variables[var_name]
