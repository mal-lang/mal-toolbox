"""
MAL-Toolbox Language Specification Module

"""

import logging

logger = logging.getLogger(__name__)

# TODO move these functions to their relevant module/class

def extends_asset(lang_spec: dict, asset, target_asset):
    """
    Check if an asset extends the target asset through inheritance.

    Arguments:
    lang_spec       - a dictionary containing the MAL language specification
    asset           - the asset name we wish to evaluate
    target_asset    - the target asset name we wish to evaluate if it
                      is extended

    Return:
    True if this asset extends the target_asset via inheritance.
    False otherwise.
    """

    logger.debug(f'Check if {asset} extends {target_asset} via inheritance.')

    if asset == target_asset:
        return True

    asset_dict = next((asset_info for asset_info in lang_spec['assets'] \
        if asset_info['name'] == asset), None)
    if not asset_dict:
        logger.error(f'Failed to find asset type {asset} when '\
            'looking for variable.')
        return False
    if asset_dict['superAsset']:
        if asset_dict['superAsset'] == target_asset:
            return True
        else:
            return extends_asset(lang_spec, asset_dict['superAsset'],
                target_asset)

    return False

