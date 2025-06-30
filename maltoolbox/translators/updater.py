import json
import logging

import yaml

import logging
from ..model import Model
from ..language import LanguageGraph
from ..file_utils import load_dict_from_json_file, load_dict_from_yaml_file

logger = logging.getLogger(__name__)

def load_model_from_older_version(
        filename: str, lang_graph: LanguageGraph,
    ) -> Model:

    """ Load an older Model file

    Load an older model from given `filename` (yml/json)
    convert the model to the new format and return a Model object. 
    """

    model_dict = load_model_dict_from_file(filename)

    # Get the version of the model, default to 0.0
    # since metadata was not given back then
    version = model_dict.get(
        'metadata', {}
    ).get('MAL-Toolbox Version', '0.0.')

    match (version):
        case x if '0.0.' in x:
            model_dict = convert_model_dict_from_version_0_0(model_dict)
            model_dict = convert_model_dict_from_version_0_1(model_dict)
            model_dict = convert_model_dict_from_version_0_2(model_dict)
        case x if '0.1.' in x:
            model_dict = convert_model_dict_from_version_0_1(model_dict)
            model_dict = convert_model_dict_from_version_0_2(model_dict)
        case x if '0.2.' in x:
            model_dict = convert_model_dict_from_version_0_2(model_dict)
        case _:
            msg = (
                'Unknown version "%s" format.'
                'Could not load model from file "%s"'
            )
            logger.error(msg, version, filename)
            raise ValueError(msg % (version, filename))

    # TODO: _from_dict should be public
    return Model._from_dict(model_dict, lang_graph)


def load_model_dict_from_file(
    filename: str,
    ) -> dict:
    """Load a json or yaml file to dict"""

    model_dict = {}
    if filename.endswith('.yml') or filename.endswith('.yaml'):
        model_dict = load_dict_from_yaml_file(filename)
    elif filename.endswith('.json'):
        model_dict = load_dict_from_json_file(filename)
    else:
        msg = 'Unknown file extension for model file to load from.'
        logger.error(msg)
        raise ValueError(msg)
    return model_dict


def convert_model_dict_from_version_0_0(model_dict: dict) -> dict:
    """
    Convert model dict version 0.0 to 0.1

    Arguments:
    model_dict  - the dictionary containing the serialized model

    Returns:
    A dictionary containing the version 0.1 equivalent serialized model
    """

    new_model_dict = {}

    # Meta data and attackers did not change
    new_model_dict['metadata'] = model_dict['metadata']
    new_model_dict['attackers'] = model_dict.get('attackers', {})

    new_model_dict['assets'] = {}

    # Reconstruct the assets
    new_assets_dict = {}
    for asset_id, asset_info in model_dict['assets'].items():
        # Make sure asset ids are ints for json compatibility
        asset_id = int(asset_id)
        new_assets_dict[asset_id] = asset_info

        # Metaconcept renamed to type
        new_assets_dict[asset_id]["type"] = (
            new_assets_dict[asset_id]["metaconcept"]
        )
        del new_assets_dict[asset_id]["metaconcept"]

    new_model_dict['assets'] = new_assets_dict

    # Reconstruct the associations dict in new format
    new_assoc_list = []
    for assoc_dict in model_dict.get('associations', []):
        new_assoc_dict: dict[str, dict] = {}

        # Assocs are not mapped from association names
        # metaconcept field removed
        assoc_name = assoc_dict['metaconcept']
        new_assoc_dict[assoc_name] = {}

        for field, targets in assoc_dict['association'].items():
            # Targets are now intes
            new_targets = [int(asset_id) for asset_id in targets]
            new_assoc_dict[assoc_name][field] = new_targets

        new_assoc_list.append(new_assoc_dict)

    # Add new assoc dict to new model dict
    new_model_dict['associations'] = new_assoc_list

    # Reconstruct the attackers
    if 'attackers' in model_dict:
        attackers_info = model_dict['attackers']

    return new_model_dict


def convert_model_dict_from_version_0_1(model_dict: dict) -> dict:
    """
    Convert model dict version 0.1 to 0.2

    Arguments:
    model_dict  - the dictionary containing the serialized model

    Returns:
    A dictionary containing the version 0.2 equivalent serialized model
    """

    new_model_dict = {}

    # Meta data and assets format did not change from version 0.1
    new_model_dict['metadata'] = model_dict['metadata']

    new_assets_dict = {}
    for asset_id, asset_info in model_dict['assets'].items():
        # Make sure asset ids are ints for json compatibility
        asset_id = int(asset_id)
        new_assets_dict[asset_id] = asset_info

    new_model_dict['assets'] = new_assets_dict

    # Reconstruct the associations dict in new format
    new_assoc_list = []
    for assoc_dict in model_dict.get('associations', []):
        new_assoc_dict: dict[str, dict] = {}

        assert len(assoc_dict.keys()) == 1, (
            "Only one key per association in model file allowed"
        )

        assoc_name = list(assoc_dict.keys())[0]
        new_assoc_name = assoc_name.split("_")[0]
        new_assoc_dict[new_assoc_name] = {}
        for field, targets in assoc_dict[assoc_name].items():
            new_assoc_dict[new_assoc_name][field] = targets

        new_assoc_list.append(new_assoc_dict)

    # Add new assoc dict to new model dict
    new_model_dict['associations'] = new_assoc_list

    # Reconstruct attackers dict for new format
    new_attackers_dict: dict[int, dict] = {}
    attackers_dict: dict = model_dict.get('attackers', {})
    for attacker_id, attacker_dict in attackers_dict.items():
        attacker_id = int(attacker_id) # JSON compatibility
        new_attackers_dict[attacker_id] = {}
        new_attackers_dict[attacker_id]['name'] = attacker_dict['name']
        new_entry_points_dict = {}

        entry_points_dict = attacker_dict['entry_points']
        for asset_id, attack_steps in entry_points_dict.items():
                asset_id = int(asset_id) # JSON compatibility
                asset_name = new_assets_dict[asset_id]['name']
                new_entry_points_dict[asset_name] = {
                    'asset_id': asset_id,
                    'attack_steps': attack_steps['attack_steps']
                }

        new_attackers_dict[attacker_id]['entry_points'] = new_entry_points_dict

    # Add new attackers dict to new model dict
    new_model_dict['attackers'] = new_attackers_dict
    return new_model_dict


def convert_model_dict_from_version_0_2(model_dict: dict) -> dict:
    """
    Convert model dict version 0.2 to 0.3

    Arguments:
    model_dict  - the dictionary containing the serialized model

    Returns:
    A dictionary containing the version 0.3 equivalent serialized model
    """

    new_model_dict = {}

    # Meta data and assets format did not change from version 0.1
    new_model_dict['metadata'] = model_dict['metadata']
    new_model_dict['attackers'] = model_dict['attackers']

    new_assets_dict: dict[int, dict] = {}
    for asset_id, asset_info in model_dict['assets'].items():
        # Make sure asset ids are ints for json compatibility
        asset_id = int(asset_id)
        new_assets_dict[asset_id] = asset_info
        new_assets_dict[asset_id]['associated_assets'] = {}

    new_model_dict['assets'] = new_assets_dict

    # Reconstruct the associations dict in new format
    for assocs_dict in model_dict.get('associations', []):

        assert len(assocs_dict.keys()) == 1, (
            "Only one key per association in model file allowed"
        )

        assoc_name = list(assocs_dict.keys())[0]
        assoc_dict = assocs_dict[assoc_name]
        left_field_name = list(assoc_dict.keys())[0]
        right_field_name = list(assoc_dict.keys())[1]

        for l_asset_id in assoc_dict[left_field_name]:
            l_asset_id = int(l_asset_id)  # json compatibility
            for r_asset_id in assoc_dict[right_field_name]:
                r_asset_id = int(r_asset_id)  # json compatibility
                l_asset_dict = new_model_dict['assets'][l_asset_id]
                r_asset_dict = new_model_dict['assets'][r_asset_id]

                # Add connections from left to right
                l_asset_dict['associated_assets'].setdefault(
                    right_field_name, {}
                )[r_asset_id] = r_asset_dict['name']

                # And from right to left
                r_asset_dict['associated_assets'].setdefault(
                    left_field_name, {}
                )[l_asset_id] = l_asset_dict['name']

    return new_model_dict
