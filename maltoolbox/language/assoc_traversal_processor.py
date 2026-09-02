import logging

from maltoolbox.language.compiler.mal_analyzer import malAnalyzerException
from maltoolbox.language.language_graph_asset import LanguageGraphAsset
from maltoolbox.language.language_graph_attack_step import LanguageGraphAttackStep
from maltoolbox.language.language_graph_model_effect import (
    AssocSet,
    AssocTraversal,
    AssocTraversalChain,
    GlobAssocTraversal,
    ModelEffectType,
    SetOperation,
)

logger = logging.getLogger(__name__)


def _assoc_traversal(
    step: LanguageGraphAttackStep,
    instigating_assets: set[LanguageGraphAsset],
    assoc_traversal: AssocTraversal,
) -> set[LanguageGraphAsset]:
    next_assets: set[LanguageGraphAsset] = set()
    for asset in instigating_assets:
        if assoc_traversal.field_name == 'self':
            next_assets.add(step.asset)
            continue
        try:
            assoc = asset.associations[assoc_traversal.field_name]
            next_assets.add(assoc.get_field(assoc_traversal.field_name).asset)
        except KeyError:
            raise malAnalyzerException(
                f'Asset {asset.name} does not have an association'
                f' for field {assoc_traversal.field_name}.'
            )
    return next_assets


def _glob_assoc_traversal(
    step: LanguageGraphAttackStep,
    instigating_assets: set[LanguageGraphAsset],
    glob_assoc_traversal: GlobAssocTraversal,
) -> set[LanguageGraphAsset]:
    next_assets = _traverse_association_chain(
        step, instigating_assets, glob_assoc_traversal.pattern
    )
    while True:
        new_assets = _traverse_association_chain(
            step, instigating_assets, glob_assoc_traversal.pattern
        )
        if len(new_assets.difference(next_assets)) == 0:
            break
        next_assets = new_assets
    return next_assets


def _assoc_set_traversal(
    step: LanguageGraphAttackStep,
    starting_assets: set[LanguageGraphAsset],
    assoc_set: AssocSet,
) -> set[LanguageGraphAsset]:
    candidate_assets = set()
    left = _traverse_association_chain(step, starting_assets, assoc_set.left)
    right = _traverse_association_chain(step, starting_assets, assoc_set.right)
    if assoc_set.set_op == SetOperation.UNION:
        candidate_assets = left | right
    elif assoc_set.set_op == SetOperation.DIFFERENCE:
        candidate_assets = left - right
    elif assoc_set.set_op == SetOperation.INTERSECTION:
        candidate_assets = left & right
    else:
        raise ValueError(
            f'Unknown set operation {assoc_set.set_op} in association set traversal.'
        )
    return candidate_assets


def _traverse_association_chain(
    step: LanguageGraphAttackStep,
    instigating_assets: set[LanguageGraphAsset],
    assoc_traversals: AssocTraversalChain,
) -> set[LanguageGraphAsset]:
    """Traverse the association chain starting from the given asset."""
    current_assets = instigating_assets
    for assoc_traversal in assoc_traversals:
        if isinstance(assoc_traversal, AssocTraversal):
            current_assets = _assoc_traversal(step, current_assets, assoc_traversal)
        elif isinstance(assoc_traversal, GlobAssocTraversal):
            current_assets = _glob_assoc_traversal(
                step, current_assets, assoc_traversal
            )
        elif isinstance(assoc_traversal, AssocSet):
            current_assets = _assoc_set_traversal(step, current_assets, assoc_traversal)
        else:
            raise TypeError(
                f'Unknown association traversal type: {type(assoc_traversal)}'
            )
    return current_assets


def _resolve_terminal_traversal(
    step: LanguageGraphAttackStep,
    instigating_assets: set[LanguageGraphAsset],
    assoc_traversals: AssocTraversalChain,
) -> set[tuple[LanguageGraphAsset, str, LanguageGraphAsset]]:
    current_assets = _traverse_association_chain(
        step, instigating_assets, assoc_traversals[:-1]
    )
    last = assoc_traversals[-1]
    if isinstance(last, AssocTraversal):
        terminal_resolves: set[tuple[LanguageGraphAsset, str, LanguageGraphAsset]] = (
            set()
        )
        for asset in current_assets:
            if last.field_name == 'self':
                terminal_resolves.add((asset, last.field_name, step.asset))
                continue
            try:
                candidate_asset = (
                    asset.associations[last.field_name].get_field(last.field_name).asset
                )
                terminal_resolves.add((asset, last.field_name, candidate_asset))
            except KeyError:
                raise malAnalyzerException(
                    f'Asset {asset.name} does not have an association'
                    f' for field {last.field_name}.'
                )
        return terminal_resolves
    elif isinstance(last, GlobAssocTraversal):
        # `*` is a repeated application of the pattern, so the termination
        # is whatever the pattern itself terminates in.
        return _resolve_terminal_traversal(step, current_assets, last.pattern)
    elif isinstance(last, AssocSet):
        left = _resolve_terminal_traversal(step, current_assets, last.left)
        right = _resolve_terminal_traversal(step, current_assets, last.right)
        if last.set_op == SetOperation.UNION:
            return left | right
        elif last.set_op == SetOperation.DIFFERENCE:
            return left - right
        elif last.set_op == SetOperation.INTERSECTION:
            return left & right
        else:
            raise ValueError(
                f'Unknown set operation {last.set_op} in association set traversal.'
            )
    else:
        raise TypeError(f'Unknown association traversal type: {type(last)}')


def validate_model_effects(assets: dict[str, LanguageGraphAsset]) -> None:
    for asset in assets.values():
        for step in asset.attack_steps.values():
            for model_effect in (
                step.additive_model_effects + step.subtractive_model_effects
            ):
                base_resolves = _resolve_terminal_traversal(
                    step, {asset}, model_effect.base
                )
                for dyn_target in model_effect.targets:
                    is_edge_addition = (
                        model_effect.model_effect_type == ModelEffectType.ADDITIVE
                        and dyn_target.assoc_op
                    )
                    if is_edge_addition:
                        dyn_target_resolves = _resolve_terminal_traversal(
                            step, {asset}, dyn_target.assoc_traversal
                        )
                        for (
                            anchor_asset,
                            field_name,
                            terminating_asset,
                        ) in dyn_target_resolves:
                            for (
                                base_asset,
                                base_field_name,
                                base_terminating_asset,
                            ) in base_resolves:
                                if not base_terminating_asset.is_subasset_of(
                                    terminating_asset
                                ):
                                    raise malAnalyzerException(
                                        'Invalid model effect for edge addition. '
                                        f'Base terminates in field {base_field_name} with type {base_terminating_asset.name}, '
                                        f'which is not a subasset of the target asset {terminating_asset.name} '
                                        f'that terminates the dynamic target with index {model_effect.targets.index(dyn_target)},'
                                        f' in {step.full_name}.'
                                    )
                    else:
                        dyn_target_resolves = _resolve_terminal_traversal(
                            step,
                            {base_resolve[2] for base_resolve in base_resolves},
                            dyn_target.assoc_traversal,
                        )
