
import json
import logging
from typing import Any

from maltoolbox.exceptions import LanguageGraphAssociationError, LanguageGraphException, LanguageGraphStepExpressionError, LanguageGraphSuperAssetNotFoundError
from maltoolbox.language.detector import Context, Detector
from maltoolbox.language.language_graph_lookup import get_attacks_for_asset_type, get_variables_for_asset_type
from maltoolbox.language.language_graph_asset import LanguageGraphAsset
from maltoolbox.language.language_graph_assoc import LanguageGraphAssociation, LanguageGraphAssociationField, link_association_to_assets
from maltoolbox.language.language_graph_attack_step import LanguageGraphAttackStep
from maltoolbox.language.step_expression_processor import process_step_expression, resolve_variable, reverse_expr_chain


logger = logging.getLogger(__name__)


def generate_graph(lang_spec) -> dict[str, LanguageGraphAsset]:
    """Generate language graph starting from the MAL language specification
    given in the constructor."""
    # Generate all of the asset nodes of the language graph.
    assets = {}
    for asset_dict in lang_spec['assets']:
        logger.debug(
            'Create asset language graph nodes for asset %s',
            asset_dict['name']
        )
        asset_node = LanguageGraphAsset(
            name=asset_dict['name'],
            own_associations={},
            attack_steps={},
            info=asset_dict['meta'],
            own_super_asset=None,
            own_sub_assets=list(),
            own_variables={},
            is_abstract=asset_dict['isAbstract']
        )
        assets[asset_dict['name']] = asset_node

    # Link assets to each other
    link_assets(lang_spec, assets)

    # Add and link associations to assets
    create_associations_for_assets(lang_spec, assets)

    # Set the variables for each asset
    set_variables_for_assets(assets, lang_spec)

    # Add attack steps to the assets
    generate_attack_steps(assets, lang_spec)

    return assets

def link_assets(
        lang_spec: dict[str, Any],
        assets: dict[str, LanguageGraphAsset]
    ) -> None:
    """Link assets based on inheritance and associations."""
    for asset_dict in lang_spec['assets']:
        asset = assets[asset_dict['name']]
        if asset_dict['superAsset']:
            super_asset = assets[asset_dict['superAsset']]
            if not super_asset:
                msg = 'Failed to find super asset "%s" for asset "%s"!'
                logger.error(
                    msg, asset_dict["superAsset"], asset_dict["name"])
                raise LanguageGraphSuperAssetNotFoundError(
                    msg % (asset_dict["superAsset"], asset_dict["name"]))

            super_asset.own_sub_assets.append(asset)
            asset.own_super_asset = super_asset


def set_variables_for_assets(assets: dict[str, LanguageGraphAsset], lang_spec) -> None:
    """Set the variables for each asset based on the language specification.

    Arguments:
    ---------
    assets      - a dictionary of LanguageGraphAsset objects
                    indexed by their names

    """
    for asset in assets.values():
        logger.debug(
            'Set variables for asset %s', asset.name
        )
        variables = get_variables_for_asset_type(asset.name, lang_spec)
        for variable in variables:
            if logger.isEnabledFor(logging.DEBUG):
                # Avoid running json.dumps when not in debug
                logger.debug(
                    'Processing Variable Expression:\n%s',
                    json.dumps(variable, indent=2)
                )
            resolve_variable(assets, asset, variable['name'], lang_spec)


def generate_attack_steps(assets: dict[str, LanguageGraphAsset], lang_spec: dict) -> None:
    """
    Generate attack steps for all assets and link them according to the
    language specification.

    This method performs three phases:

    1. Create attack step nodes for each asset, including detectors.
    2. Inherit attack steps from super-assets, respecting overrides.
    3. Link attack steps via 'reaches' and evaluate 'exist'/'notExist'
    requirements.

    Args:
        assets (dict): Mapping of asset names to asset objects.

    Raises:
        LanguageGraphStepExpressionError: If a step expression cannot be
            resolved to a target asset or attack step.
        LanguageGraphException: If an existence requirement cannot be
            resolved.
    """
    langspec_dict = {}

    for asset in assets.values():
        logger.debug('Create attack steps language graph nodes for asset %s', asset.name)
        for step_dict in get_attacks_for_asset_type(asset.name, lang_spec).values():
            logger.debug(
                'Create attack step language graph nodes for %s', step_dict['name']
            )
            node = LanguageGraphAttackStep(
                name=step_dict['name'],
                type=step_dict['type'],
                asset=asset,
                causal_mode=step_dict.get('causal_mode'),
                ttc=step_dict['ttc'],
                overrides=(
                    step_dict['reaches']['overrides']
                    if step_dict['reaches'] else False
                ),
                own_children={}, own_parents={},
                info=step_dict['meta'],
                tags=list(step_dict['tags'])
            )
            langspec_dict[node.full_name] = step_dict
            asset.attack_steps[node.name] = node

            for det in step_dict.get('detectors', {}).values():
                node.detectors[det['name']] = Detector(
                    context=Context(
                        {lbl: assets[a] for lbl, a in det['context'].items()}
                    ),
                    name=det.get('name'),
                    type=det.get('type'),
                    tprate=det.get('tprate'),
                )

    pending = list(assets.values())
    while pending:
        asset = pending.pop(0)
        super_asset = asset.own_super_asset
        if super_asset in pending:
            # Super asset still needs processing, defer this asset
            pending.append(asset)
            continue
        if not super_asset:
            continue
        for super_step in super_asset.attack_steps.values():
            current_step = asset.attack_steps.get(super_step.name)
            if not current_step:
                node = LanguageGraphAttackStep(
                    name=super_step.name,
                    type=super_step.type,
                    asset=asset,
                    causal_mode=super_step.causal_mode,
                    ttc=super_step.ttc,
                    overrides=False,
                    own_children={},
                    own_parents={},
                    info=super_step.info,
                    tags=list(super_step.tags)
                )
                node.inherits = super_step
                asset.attack_steps[super_step.name] = node
            elif current_step.overrides:
                continue
            else:
                current_step.inherits = super_step
                current_step.tags += super_step.tags
                current_step.info |= super_step.info

    for asset in assets.values():
        for step in asset.attack_steps.values():
            logger.debug('Determining children for attack step %s', step.name)
            if step.full_name not in langspec_dict:
                continue

            entry = langspec_dict[step.full_name]
            for expr in (entry['reaches']['stepExpressions'] if entry['reaches'] else []):
                tgt_asset, chain, tgt_name = process_step_expression(assets, step.asset, None, expr, lang_spec)
                if not tgt_asset:
                    raise LanguageGraphStepExpressionError(
                        'Failed to find target asset for:\n%s' % json.dumps(expr, indent=2)
                    )
                if tgt_name not in tgt_asset.attack_steps:
                    raise LanguageGraphStepExpressionError(
                        'Failed to find target attack step %s on %s:\n%s' %
                        (tgt_name, tgt_asset.name, json.dumps(expr, indent=2))
                    )

                tgt = tgt_asset.attack_steps[tgt_name]
                step.own_children.setdefault(tgt, []).append(chain)
                tgt.own_parents.setdefault(step, []).append(reverse_expr_chain(chain, None))

            if step.type in ('exist', 'notExist'):
                reqs = entry['requires']['stepExpressions'] if entry['requires'] else []
                if not reqs:
                    raise LanguageGraphStepExpressionError(
                        'Missing requirements for "%s" of type "%s":\n%s' %
                        (step.name, step.type, json.dumps(entry, indent=2))
                    )
                for expr in reqs:
                    _, chain, _ = process_step_expression(assets, step.asset, None, expr, lang_spec)
                    if chain is None:
                        raise LanguageGraphException(
                            f'Failed to find existence step requirement for:\n{expr}'
                        )
                    step.own_requires.append(chain)


def create_associations_for_assets(
        lang_spec: dict[str, Any], assets: dict[str, LanguageGraphAsset]
    ) -> None:
    """Link associations to assets based on the language specification.

    Arguments:
    ---------
    lang_spec   - the language specification dictionary
    assets      - a dictionary of LanguageGraphAsset objects
                    indexed by their names

    """
    for association_dict in lang_spec['associations']:
        logger.debug(
            'Create association language graph nodes for association %s',
            association_dict['name']
        )

        left_asset_name = association_dict['leftAsset']
        right_asset_name = association_dict['rightAsset']

        if left_asset_name not in assets:
            raise LanguageGraphAssociationError(
                f'Left asset "{left_asset_name}" for '
                f'association "{association_dict["name"]}" not found!'
            )
        if right_asset_name not in assets:
            raise LanguageGraphAssociationError(
                f'Right asset "{right_asset_name}" for '
                f'association "{association_dict["name"]}" not found!'
            )

        left_asset = assets[left_asset_name]
        right_asset = assets[right_asset_name]

        assoc_node = LanguageGraphAssociation(
            name=association_dict['name'],
            left_field=LanguageGraphAssociationField(
                left_asset,
                association_dict['leftField'],
                association_dict['leftMultiplicity']['min'],
                association_dict['leftMultiplicity']['max']
            ),
            right_field=LanguageGraphAssociationField(
                right_asset,
                association_dict['rightField'],
                association_dict['rightMultiplicity']['min'],
                association_dict['rightMultiplicity']['max']
            ),
            info=association_dict['meta']
        )

        # Add the association to the left and right asset
        link_association_to_assets(
            assoc_node, left_asset, right_asset
        )