import copy
import logging
from maltoolbox.language.language_graph_attack_step import LanguageGraphAttackStep
from maltoolbox.model import ModelAsset

logger = logging.getLogger(__name__)

def get_ttc_dist(
    asset: ModelAsset, attack_step: LanguageGraphAttackStep
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
