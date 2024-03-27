"""
MAL-Toolbox Language Specification Module

"""

import logging

logger = logging.getLogger(__name__)

# TODO move these functions to their relevant module/class

def get_association_by_fields_and_assets(lang_spec: dict,
    first_field: str,
    second_field: str,
    first_asset: str,
    second_asset: str) -> str:
    """
    Get an association based on its field names and asset types

    Arguments:
    lang_spec       - a dictionary containing the MAL language specification
    first_field     - a string containing the first field
    second_field    - a string containing the second field
    first_asset     - a string representing the first asset type
    second_asset    - a string representing the second asset type

    Return:
    The name of the association matching the fieldnames and asset types.
    None if there is no match.
    """
    for assoc in lang_spec['associations']:
        logger.debug(f'Compare (\"{first_asset}\",'
            f'\"{first_field}\",'
            f'\"{second_asset}\",'
            f'\"{second_field}\") to '
            f'(\"{assoc["leftAsset"]}\",'
            f'\"{assoc["leftField"]}\",'
            f'\"{assoc["rightAsset"]}\",'
            f'\"{assoc["rightField"]}\").')

        # If the asset and fields match either way we accept it as a match.
        if assoc['leftField'] == first_field and \
            assoc['rightField'] == second_field and \
            extends_asset(lang_spec, first_asset, assoc['leftAsset']) and \
            extends_asset(lang_spec, second_asset, assoc['rightAsset']):
            return assoc['name']
        if assoc['leftField'] == second_field and \
            assoc['rightField'] == first_field and \
            extends_asset(lang_spec, second_asset, assoc['leftAsset']) and \
            extends_asset(lang_spec, first_asset, assoc['rightAsset']):
            return assoc['name']

    return None

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

