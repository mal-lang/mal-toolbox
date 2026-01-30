
import logging

from maltoolbox.exceptions import LanguageGraphException


logger = logging.getLogger(__name__)

def get_attacks_for_asset_type(asset_type: str, lang_spec) -> dict[str, dict]:
    """Get all Attack Steps for a specific asset type.

    Arguments:
    ---------
    asset_type      - the name of the asset type we want to
                        list the possible attack steps for

    Return:
    ------
    A dictionary containing the possible attacks for the
    specified asset type. Each key in the dictionary is an attack name
    associated with a dictionary containing other characteristics of the
    attack such as type of attack, TTC distribution, child attack steps
    and other information

    """
    attack_steps: dict = {}
    try:
        asset = next(
            asset for asset in lang_spec['assets']
                if asset['name'] == asset_type
        )
    except StopIteration:
        logger.error(
            'Failed to find asset type %s when looking'
            'for attack steps.', asset_type
        )
        return attack_steps

    logger.debug(
        'Get attack steps for %s asset from '
        'language specification.', asset['name']
    )

    attack_steps = {step['name']: step for step in asset['attackSteps']}

    return attack_steps


def get_associations_for_asset_type(asset_type: str, lang_spec) -> list[dict]:
    """Get all associations for a specific asset type.

    Arguments:
    ---------
    asset_type      - the name of the asset type for which we want to
                        list the associations

    Return:
    ------
    A list of dicts, where each dict represents an associations
    for the specified asset type. Each dictionary contains
    name and meta information about the association.

    """
    logger.debug(
        'Get associations for %s asset from '
        'language specification.', asset_type
    )
    associations: list = []

    asset = next((asset for asset in lang_spec['assets']
        if asset['name'] == asset_type), None)
    if not asset:
        logger.error(
            'Failed to find asset type %s when '
            'looking for associations.', asset_type
        )
        return associations

    assoc_iter = (assoc for assoc in lang_spec['associations']
        if assoc['leftAsset'] == asset_type or
            assoc['rightAsset'] == asset_type)
    assoc = next(assoc_iter, None)
    while assoc:
        associations.append(assoc)
        assoc = next(assoc_iter, None)

    return associations


def get_variables_for_asset_type(asset_type: str, lang_spec) -> list[dict]:
    """Get variables for a specific asset type.
    Note: Variables are the ones specified in MAL through `let` statements

    Arguments:
    ---------
    asset_type      - a string representing the asset type which
                        contains the variables

    Return:
    ------
    A list of dicts representing the step expressions for the variables
    belonging to the asset.

    """
    asset_dict = next((asset for asset in lang_spec['assets']
        if asset['name'] == asset_type), None)
    if not asset_dict:
        msg = 'Failed to find asset type %s in language specification '\
            'when looking for variables.'
        logger.error(msg, asset_type)
        raise LanguageGraphException(msg % asset_type)

    return asset_dict['variables']


def get_var_expr_for_asset(asset_type: str, var_name: str, lang_spec) -> dict:
    """Get a variable for a specific asset type by variable name.

    Arguments:
    ---------
    asset_type      - a string representing the type of asset which
                        contains the variable
    var_name        - a string representing the variable name

    Return:
    ------
    A dictionary representing the step expression for the variable.

    """
    vars_dict = get_variables_for_asset_type(asset_type, lang_spec)

    var_expr = next((var_entry['stepExpression'] for var_entry
        in vars_dict if var_entry['name'] == var_name), None)

    if not var_expr:
        msg = 'Failed to find variable name "%s" in language '\
            'specification when looking for variables for "%s" asset.'
        logger.error(msg, var_name, asset_type)
        raise LanguageGraphException(msg % (var_name, asset_type))
    return var_expr
