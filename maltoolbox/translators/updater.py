import json
import logging

import yaml

from ..model import Model, AttackerAttachment
from ..language import LanguageClassesFactory

logger = logging.getLogger(__name__)

def load_model_from_older_version(
        filename: str,
        lang_classes_factory: LanguageClassesFactory,
        version: str
    ) -> Model:
    match (version):
        case '0.0.39':
            return load_model_from_version_0_0_39(filename,
                lang_classes_factory)
        case _:
            msg = ('Unknown version "%s" format. Could not '
            'load model from file "%s"')
            logger.error(msg % (version, filename))
            raise ValueError(msg % (version, filename))

def load_model_from_version_0_0_39(
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

            asset = getattr(model.lang_classes_factory.ns,
                asset_object['metaconcept'])(name = asset_object['name'])

            for defense in (defenses:=asset_object.get('defenses', [])):
                setattr(asset, defense, float(defenses[defense]))

            model.add_asset(asset, asset_id = int(asset_id))

        # Reconstruct the associations
        for assoc_dict in model_dict.get('associations', []):
            association = getattr(model.lang_classes_factory.ns, assoc_dict.pop('metaconcept'))()

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

    def load_from_json(
            filename: str,
            lang_classes_factory: LanguageClassesFactory
        ) -> Model:
        """
        Load model from a json file.

        Arguments:
        filename        - the name of the input file
        """
        with open(filename, 'r', encoding='utf-8') as model_file:
            model_dict = json.loads(model_file.read())

        return _process_model(model_dict, lang_classes_factory)

    def load_from_yaml(
            filename: str,
            lang_classes_factory: LanguageClassesFactory
        ) -> Model:
        """
        Load model from a yaml file.

        Arguments:
        filename        - the name of the input file
        """
        with open(filename, 'r', encoding='utf-8') as model_file:
            model_dict = yaml.safe_load(model_file)

        return _process_model(model_dict, lang_classes_factory)

    logger.info(f'Loading model from {filename} file.')
    if filename.endswith('.yml') or filename.endswith('.yaml'):
        return load_from_yaml(filename, lang_classes_factory)
    elif filename.endswith('.json'):
        return load_from_json(filename, lang_classes_factory)
    else:
        msg = 'Unknown file extension for model file to load from.'
        logger.error(msg)
        raise ValueError(msg)
    return None
