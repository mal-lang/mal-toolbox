"""
MAL-Toolbox Model Module
"""

import json
import yaml
import logging

from dataclasses import dataclass
from python_jsonschema_objects.literals import LiteralValue

logger = logging.getLogger(__name__)

@dataclass
class AttackerAttachment:
    """Used to attach attackers to attack step entrypoints of assets"""
    id: int = None
    name: str = None
    entry_points: list[tuple] = None

class Model:
    latestId = 0

    def __repr__(self) -> str:
        return f'Model {self.name}'

    def __init__(self, name, lang_classes_factory):
        self.name = name
        self.assets = []
        self.associations = []
        self.attackers = []
        self.lang_classes_factory = lang_classes_factory

    def add_asset(
            self,
            asset,
            asset_id: int = None,
            allow_duplicate_names = True
        ):
        """Add an asset to the model.

        Arguments:
        asset                   - the asset to add to the model
        asset_id                - the id to assign to this asset, usually
                                  from an instance model file
        allow_duplicate_name    - allow duplicate names to be used. If allowed
                                  and a duplicate is encountered the name will
                                  be prefixed with the id.

        Return:
        An asset matching the name if it exists in the model.
        """
        if asset_id is not None:
            for existing_asset in self.assets:
                if asset_id == existing_asset.id:
                    raise ValueError(f'Asset index {asset_id} already in use.')
            asset.id = asset_id
        else:
            asset.id = self.latestId
        self.latestId = max(asset.id + 1, self.latestId)

        asset.associations = []

        if not hasattr(asset, 'name'):
            asset.name = asset.metaconcept + ':' + str(asset.id)
        else:
            for ex_asset in self.assets:
                if ex_asset.name == asset.name:
                    if allow_duplicate_names:
                        asset.name = asset.name + ':' + str(asset.id)
                        break
                    else:
                        raise ValueError(f'Asset name {asset.name} is a '
                        'duplicate and we do not allow duplicates.')

        logger.debug(f'Add {asset.name}(id:{asset.id}) to model '
            f'\"{self.name}\".')
        self.assets.append(asset)

    def remove_asset(self, asset):
        """Remove an asset from the model.

        Arguments:
        asset     - the asset to remove
        """
        logger.debug(f'Remove {asset.name}(id:{asset.id}) from model '
            f'\"{self.name}\".')
        if asset not in self.assets:
            raise LookupError(f'Asset {asset.id} is not part of model '
                f'\"{self.model}\".')

        # First remove all of the associations
        for association in asset.associations:
            self.remove_asset_from_association(asset, association)

        self.assets.remove(asset)

    def remove_asset_from_association(self, asset, association):
        """Remove an asset from an association and remove the association if any
        of the two sides is now empty.

        Arguments:
        asset           - the asset to remove from the given association
        association     - the association to remove the asset from
        """
        logger.debug(f'Remove {asset.name}(id:{asset.id}) from association '
            f'of type \"{type(association)}\".')
        if asset not in self.assets:
            raise LookupError(f'Asset {asset.id} is not part of model '
                f'\"{self.model}\".')
        if association not in self.associations:
            raise LookupError(f'Association is not part of model '
                f'\"{self.model}\".')

        firstElementName, secondElementName = association._properties.keys()
        firstElements = getattr(association, firstElementName)
        secondElements = getattr(association, secondElementName)
        found = False
        for field in [firstElements, secondElements]:
            if asset in field:
                found = True
                if len(field) == 1:
                    # There are no other assets on this side,
                    # so we should remove the entire association.
                    self.remove_association(association)
                    return
                field.remove(asset)

        if not found:
            raise LookupError(f'Asset {asset.id} is not part of the '
                'association provided.')


    def add_association(self, association):
        """Add an association to the model.

        An association will have 2 field names, each
        potentially containing several assets.

        Arguments:
        association     - the association to add to the model
        """
        for prop in range(0, 2):
            for asset in getattr(association, list(association._properties)[prop]):
                assocs = list(asset.associations)
                assocs.append(association)
                asset.associations = assocs
        self.associations.append(association)

    def remove_association(self, association):
        """Remove an association from the model.

        Arguments:
        association     - the association to remove from the model
        """
        if association not in self.associations:
            raise LookupError(f'Association is not part of model '
                f'\"{self.model}\".')

        firstElementName, secondElementName = association._properties.keys()
        firstElements = getattr(association, firstElementName)
        secondElements = getattr(association, secondElementName)
        for asset in firstElements:
            assocs = list(asset.associations)
            assocs.remove(association)
            asset.associations = assocs
        for asset in secondElements:
            # In fringe cases we may have reflexive associations where the
            # first element removed the association already. But generally the
            # association should exist for the second element too.
            if association in asset.associations:
                assocs = list(asset.associations)
                assocs.remove(association)
                asset.associations = assocs

        self.associations.remove(association)

    def add_attacker(self, attacker, attacker_id: int = None):
        """Add an attacker to the model.

        Arguments:
        attacker        - the attacker to add
        attacker_id     - optional id for the attacker
        """
        if attacker_id is not None:
            attacker.id = attacker_id
        else:
            attacker.id = self.latestId
        self.latestId = max(attacker.id + 1, self.latestId)

        if not hasattr(attacker, 'name') or not attacker.name:
            attacker.name = 'Attacker:' + str(attacker.id)
        self.attackers.append(attacker)

    def get_asset_by_id(self, asset_id):
        """
        Find an asset in the model based on its id.

        Arguments:
        asset_id        - the id of the asset we are looking for

        Return:
        An asset matching the id if it exists in the model.
        """
        logger.debug(f'Get asset with id \"{asset_id}\" from model '
            f'\"{self.name}\".')
        return next(
                (asset for asset in self.assets
                if asset.id == asset_id), None
             )

    def get_asset_by_name(self, asset_name):
        """
        Find an asset in the model based on its name.

        Arguments:
        asset_name        - the name of the asset we are looking for

        Return:
        An asset matching the name if it exists in the model.
        """
        logger.debug(f'Get asset with name \"{asset_name}\" from model '
            f'\"{self.name}\".')
        return next(
                (asset for asset in self.assets
                if asset.name == asset_name), None
             )


    def get_attacker_by_id(self, attacker_id):
        """
        Find an attacker in the model based on its id.

        Arguments:
        attacker_id     - the id of the attacker we are looking for

        Return:
        An attacker matching the id if it exists in the model.
        """
        logger.debug(f'Get attacker with id \"{attacker_id}\" from model '
            f'\"{self.name}\".')
        return next(
                (attacker for attacker in self.attackers
                if attacker.id == attacker_id), None
            )

    def get_associated_assets_by_field_name(self, asset, field_name):
        """
        Get a list of associated assets for an asset given a field name.

        Arguments:
        asset           - the asset whose fields we are interested in
        field_name       - the field name we are looking for

        Return:
        A list of assets associated with the asset given that match the
        field_name.
        """
        logger.debug(f'Get associated assets for asset '
            f'{asset.name}(id:{asset.id}) by field name {field_name}.')
        associated_assets = []
        for association in asset.associations:
            # Determine which two of the end points leads away from the asset.
            # This is particularly relevant for associations between two
            # assets of the same type.
            prop1, prop2 = association._properties.keys()
            if asset in getattr(association, prop1):
                associated_asset = prop2
            else:
                associated_asset = prop1

            if associated_asset == field_name:
                associated_assets.extend(getattr(association, associated_asset))

        return associated_assets

    def asset_to_dict(self, asset):
        """
        Convert an asset to its JSON format.
        """
        defenses = {}
        logger.debug(f'Translating {asset.name} to json.')

        for key, value in asset._properties.items():
            property_schema = (
                self.lang_classes_factory.json_schema['definitions']['LanguageAsset']
                ['definitions'][asset.metaconcept]['properties'][key]
            )

            if "maximum" not in property_schema:
                # Check if property is a defense by looking up defense
                # specific key. Skip if it is not a defense.
                continue

            logger.debug(f'Translating {key}: {value} defense to json.')

            if value == value.default():
                # Skip the defense values if they are the default ones.
                continue

            defenses[key] = float(value)

        ret = (asset.id, {
                'name': str(asset.name),
                'metaconcept': str(asset.metaconcept),
                }
            )
        if defenses:
            ret[1]['defenses'] = defenses

        return ret

    def association_to_dict(self, association):
        """Convert an association to its JSON format.

        Arguments:
        association     - association to convert to JSON
        """
        firstElementName, secondElementName  = association._properties.keys()

        firstElements = getattr(association, firstElementName)
        secondElements = getattr(association, secondElementName)

        json_association = {
            'metaconcept': association.__class__.__name__,
            'association': {
                str(firstElementName):
                    [int(asset.id) for asset in firstElements],
                str(secondElementName):
                    [int(asset.id) for asset in secondElements]
            }
        }
        return json_association

    def attacker_to_dict(self, attacker):
        """Convert an attacker to its JSON format.

        Arguments:
        attacker        - attacker to convert to JSON
        """
        logger.debug(f'Translating {attacker.name} to json.')
        json_attacker = {
            'name': str(attacker.name),
            'entry_points': {},
        }
        for (asset, attack_steps) in attacker.entry_points:
            json_attacker['entry_points'][int(asset.id)] = {
                'attack_steps' : attack_steps
            }
        return (int(attacker.id), json_attacker)

    def model_to_dict(self):
        """Convert the model to its JSON format."""
        logger.debug(f'Converting model to JSON format.')
        contents = {
            'metadata': {},
            'assets': {},
            'associations': [],
            'attackers' : {}
        }
        contents['metadata'] = {
            'name': self.name,
            'langVersion': self.lang_classes_factory.lang_graph.metadata['version'],
            'langID': self.lang_classes_factory.lang_graph.metadata['id'],
            'malVersion': '0.1.0-SNAPSHOT',
            'info': 'Created by the mal-toolbox model python module.'
        }

        logger.debug('Translating assets to json.')
        for asset in self.assets:
            (asset_id, asset_json) = self.asset_to_dict(asset)
            contents['assets'][int(asset_id)] = asset_json

        logger.debug('Translating associations to json.')
        for association in self.associations:
            assoc_json = self.association_to_dict(association)
            contents['associations'].append(assoc_json)

        logger.debug('Translating attackers to json.')
        for attacker in self.attackers:
            (attacker_id, attacker_json) = self.attacker_to_dict(attacker)
            contents['attackers'][attacker_id] = attacker_json
        return contents

    def save_to_file(self, filename):
        """Save model to file.

        Arguments:
        filename        - the name of the output file
        """

        logger.info(f'Saving model to {filename} file.')
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            self.save_to_yaml(filename)
        elif filename.endswith('.json'):
            self.save_to_json(filename)
        else:
            logger.error('Unknown file extension for model file to save to.')

    def save_to_json(self, filename):
        """Save model to a json file.

        Arguments:
        filename        - the name of the output file
        """

        contents = self.model_to_dict()
        fp = open(filename, 'w')
        json.dump(contents, fp, indent = 2)

    def save_to_yaml(self, filename):
        """Save model to a yaml file.

        Arguments:
        filename        - the name of the output file
        """

        contents = self.model_to_dict()

        yaml.add_multi_representer(
            LiteralValue,
            lambda dumper, data: dumper.represent_data(data._value),
            yaml.SafeDumper
        )

        fp = open(filename, 'w')
        yaml.dump(contents, fp, Dumper=yaml.SafeDumper)

    @classmethod
    def load_from_file(cls, filename, lang_classes_factory):
        """
        Load model from file.

        Arguments:
        filename        - the name of the input file
        """
        logger.info(f'Loading model from {filename} file.')
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            return cls.load_from_yaml(filename, lang_classes_factory)
        elif filename.endswith('.json'):
            return cls.load_from_json(filename, lang_classes_factory)
        else:
            logger.error('Unknown file extension for model file to load '
                'from.')

    @classmethod
    def load_from_json(cls, filename, lang_classes_factory):
        """
        Load model from a json file.

        Arguments:
        filename        - the name of the input file
        """
        with open(filename, 'r', encoding='utf-8') as model_file:
            model_dict = json.loads(model_file.read())

        return cls._process_model(model_dict, lang_classes_factory)

    @classmethod
    def load_from_yaml(cls, filename, lang_classes_factory):
        """
        Load model from a yaml file.

        Arguments:
        filename        - the name of the input file
        """
        with open(filename, 'r', encoding='utf-8') as model_file:
            model_dict = yaml.safe_load(model_file)

        return cls._process_model(model_dict, lang_classes_factory)

    @classmethod
    def _process_model(cls, model_dict, lang_classes_factory):
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
            # TODO do we need the above compatibility?

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
                attacker = AttackerAttachment(name = attackers_info[attacker_id]['name'])
                attacker.entry_points = []
                for asset_id in attackers_info[attacker_id]['entry_points']:
                    attacker.entry_points.append(
                        (model.get_asset_by_id(int(asset_id)),
                        attackers_info[attacker_id]['entry_points']\
                            [asset_id]['attack_steps']))
                model.add_attacker(attacker, attacker_id = int(attacker_id))
        return model
