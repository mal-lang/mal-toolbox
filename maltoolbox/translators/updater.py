import json
import logging

import yaml

from ..model import Model, AttackerAttachment
from ..language import LanguageClassesFactory

logger = logging.getLogger(__name__)

def load_model_from_older_version(
        filename: str,
        lang_classes_factory: LanguageClassesFactory,
    ) -> Model:

    model_dict = load_from_file(filename)
    version = (
        model_dict.get('metadata', {}).get('MAL-Toolbox Version', None)
    )

    if version is None:
        # Backwards compatibility
        version = (
            model_dict.get('metadata', {}).get('MAL Toolbox Version', None)
        )

    if version is None:
        version = "0.0."  # Try it!

    match (version):
        case x if '0.1.' in x:
            return load_model_from_version_0_1(
                filename,
                lang_classes_factory
            )
        case x if '0.0.' in x:
            return load_model_from_version_0_0(
                filename,
                lang_classes_factory
            )
        case _:
            msg = ('Unknown version "%s" format. Could not '
            'load model from file "%s"')
            logger.error(msg % (version, filename))
            raise ValueError(msg % (version, filename))

def load_from_file(
    filename: str,
    ) -> dict:
    """Load a json or yaml file to dict"""

    model_dict = {}
    if filename.endswith('.yml') or filename.endswith('.yaml'):
        model_dict = load_from_yaml(filename)
    elif filename.endswith('.json'):
        model_dict = load_from_json(filename)
    else:
        msg = 'Unknown file extension for model file to load from.'
        logger.error(msg)
        raise ValueError(msg)

    return model_dict


def load_from_json(
        filename: str,
    ) -> dict:
    """
    Load model from a json file.

    Arguments:
    filename        - the name of the input file
    """
    with open(filename, 'r', encoding='utf-8') as model_file:
        model_dict = json.loads(model_file.read())
    return model_dict


def load_from_yaml(
        filename: str,
    ) -> dict:
    """
    Load model from a yaml file.

    Arguments:
    filename        - the name of the input file
    """
    with open(filename, 'r', encoding='utf-8') as model_file:
        model_dict = yaml.safe_load(model_file)
    return model_dict


def load_model_from_version_0_0(
        filename: str,
        lang_classes_factory: LanguageClassesFactory
    ) -> Model:
    """
    Load model from file from mal-toolbox 0.0.

    Arguments:
    filename                - the name of the input file
    lang_classes_factory    - the language classes factory that defines the
                              classes needed to build the model
    """

    def _process_model(model_dict, lang_classes_factory) -> Model:
        model = Model(model_dict['metadata']['name'], lang_classes_factory)

        # Reconstruct the assets
        for asset_id, asset_object in model_dict['assets'].items():
            logger.debug(f"Loading asset:\n{json.dumps(asset_object, indent=2)}")

            # Allow defining an asset via the metaconcept only.
            asset_object = (
                asset_object
                if isinstance(asset_object, dict)
                else {'metaconcept': asset_object, 'name': f"{asset_object}:{asset_id}"}
            )

            asset_class = model.lang_classes_factory.get_asset_class(
                asset_object['metaconcept']
            )

            if not asset_class:
                raise LookupError(f"Could not find asset type {asset_object['metaconcept']}")

            asset = asset_class(name = asset_object['name'])
            for defense in (defenses:=asset_object.get('defenses', [])):
                setattr(asset, defense, float(defenses[defense]))

            model.add_asset(asset, asset_id = int(asset_id))

        # Reconstruct the associations
        for assoc_dict in model_dict.get('associations', []):
            assoc_name = assoc_dict['metaconcept'].split('_')[0]


            field_names = list(assoc_dict['association'].keys())
            # If that fails, try by field names
            association_class = (
                model.lang_classes_factory.get_association_class_by_fieldnames(
                    assoc_name,
                    *field_names
                )
            )

            if association_class is None:
                raise LookupError(f"Could not find association {assoc_dict['metaconcept']}")

            association = association_class()

            # compatibility with old format
            assoc_dict = assoc_dict.get('association', assoc_dict)

            for field, targets in assoc_dict.items():
                targets = targets if isinstance(targets, list) else [targets]
                setattr(
                    association,
                    field,
                    [model.get_asset_by_id(int(id)) for id in targets]
                )
            model.add_association(association)

        # Reconstruct the attackers
        if 'attackers' in model_dict:
            attackers_info = model_dict['attackers']
            for attacker_id in attackers_info:
                attacker = AttackerAttachment(
                    name = attackers_info[attacker_id]['name']
                )
                attacker.entry_points = []
                for asset_id in attackers_info[attacker_id]['entry_points']:
                    attacker.entry_points.append(
                        (model.get_asset_by_id(int(asset_id)),
                        attackers_info[attacker_id]['entry_points']\
                            [asset_id]['attack_steps']))
                model.add_attacker(attacker, attacker_id = int(attacker_id))
        return model

    logger.info(f'Loading model from {filename} file.')
    model_dict = load_from_file(filename)
    return _process_model(model_dict, lang_classes_factory)


def load_model_from_version_0_1(
        filename: str,
        lang_classes_factory: LanguageClassesFactory
    ) -> Model:
    """
    Load model from file.

    Arguments:
    filename                - the name of the input file
    lang_classes_factory    - the language classes factory that defines the
                              classes needed to build the model
    """

    model_dict = load_from_yaml(filename)
    new_model_dict = {}

    # Meta data and assets format did not change from version 0.1
    new_model_dict['metadata'] = model_dict['metadata']
    new_model_dict['assets'] = model_dict['assets']

    # Remember asset ids for attackers dict construction later
    asset_id_to_name = {}
    for asset_id, asset_info in new_model_dict['assets'].items():
        asset_id_to_name[asset_id] = asset_info['name']

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

        new_attackers_dict[attacker_id] = {}
        new_attackers_dict[attacker_id]['name'] = attacker_dict['name']
        new_entry_points_dict = {}

        entry_points_dict = attacker_dict['entry_points']
        for asset_id, attack_steps in entry_points_dict.items():
                asset_name = asset_id_to_name[asset_id]
                new_entry_points_dict[asset_name] = {
                    'asset_id': asset_id,
                    'attack_steps': attack_steps['attack_steps']
                }

        new_attackers_dict[attacker_id]['entry_points'] = new_entry_points_dict

    # Add new attackers dict to new model dict
    new_model_dict['attackers'] = new_attackers_dict
    model = Model._from_dict(new_model_dict, lang_classes_factory)
    return model
