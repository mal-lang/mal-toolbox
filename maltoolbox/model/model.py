"""
MAL-Toolbox Model Module
"""

import json
import logging

from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

@dataclass
class Attacker:
    id: str = None
    name: str = None
    entry_points: List[tuple] = None

class Model:
    latestId = 0

    def __init__(self, name, lang_spec, lang_classes_factory):
        self.name = name
        self.assets = []
        self.associations = []
        self.attackers = []
        self.lang_spec = lang_spec
        self.lang_classes_factory = lang_classes_factory

    def add_asset(self, asset, asset_id: int = None):
        """
        Add an asset to the model.
        """
        if asset_id:
            asset.id = asset_id
        else:
            asset.id = self.latestId
        self.latestId = max(asset.id + 1, self.latestId)

        asset.associations = []
        if not hasattr(asset, 'name'):
            asset.name = asset.metaconcept + ':' + str(asset.id)
        self.assets.append(asset)

    def add_association(self, association):
        """
        Add an association to the model.
        """
        for prop in range(0, 2):
            for asset in getattr(association,
                list(vars(association)['_properties'])[prop]):
                assocs = list(asset.associations)
                assocs.append(association)
                asset.associations = assocs
        self.associations.append(association)

    def add_attacker(self, attacker, attacker_id: int = None):
        """
        Add an attacker to the model.
        """
        if attacker_id:
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
        return next((asset for asset in self.assets if asset.id == asset_id),
            None)

    def get_attacker_by_id(self, attacker_id):
        """
        Find an attacker in the model based on its id.

        Arguments:
        attacker_id     - the id of the attacker we are looking for

        Return:
        An attacker matching the id if it exists in the model.
        """
        return next((attacker for attacker in self.attackers \
            if attacker.id == attacker_id), None)

    def get_associated_assets_by_field_name(self, asset, field_name):
        """
        Get a list of associated assets for an asset given a fieldname.

        Arguments:
        asset           - the asset whose fields we are interested in
        fieldname       - the field name we are looking for

        Return:
        A list of assets associated with the asset given that match the
        fieldname.
        """
        logger.debug(f'Get associated assets for asset '
            f'{asset.name}(id:{asset.id}) by field name {field_name}.')
        associated_assets = []
        for association in asset.associations:
            # Determine which two of the end points leads away from the asset.
            # This is particularly relevant for associations between two
            # assets of the same type.
            if asset in getattr(association,
                list(vars(association)['_properties'])[0]):
                elementName = list(vars(association)['_properties'])[1]
            else:
                elementName = list(vars(association)['_properties'])[0]

            if elementName == field_name:
                associated_assets.extend(getattr(association, elementName))

        return associated_assets

    def asset_to_json(self, asset):
        """
        Convert an asset to its JSON format.
        """
        defenses = {}
        logger.debug(f'Translating {asset.name} to json.')
        for defense in list(vars(asset)['_properties'])[1:]:
            defenseValue = getattr(asset, defense)
            logger.debug(f'Translating {defense}: {defenseValue} defense '\
                'to json.')
            if defenseValue != getattr(asset, defense).default():
            # Save the default values that are not the default ones.
                defenses[str(defense)] = str(defenseValue)
        return (str(asset.id), {
                'name': str(asset.name),
                'metaconcept': str(asset.metaconcept),
                'eid': str(asset.id),
                'defenses': defenses
                }
            )

    def association_to_json(self, association):
        """
        Convert an association to its JSON format.
        """
        firstElementName = list(vars(association)['_properties'])[0]
        secondElementName = list(vars(association)['_properties'])[1]
        firstElements = getattr(association, firstElementName)
        secondElements = getattr(association, secondElementName)
        json_association = {
            'metaconcept': type(association).__name__,
            'association': {
                str(firstElementName): [str(asset.id) for asset in firstElements],
                str(secondElementName): [str(asset.id) for asset in secondElements]
            }
        }
        return json_association

    def attacker_to_json(self, attacker):
        """
        Convert an attacker to its JSON format.
        """
        logger.debug(f'Translating {attacker.name} to json.')
        json_attacker = {
            'name': str(attacker.name),
            'entry_points': {},
        }
        for (asset, attack_steps) in attacker.entry_points:
            json_attacker['entry_points'][str(asset.id)] = {
                'attack_steps' : attack_steps
            }
        return (str(attacker.id), json_attacker)

    def model_to_json(self):
        """
        Convert the model to its JSON format.
        """
        logger.debug(f'Converting model to JSON format.')
        contents = {
            'metadata': {},
            'assets': {},
            'associations': [],
            'attackers' : {}
        }
        contents['metadata'] = {
            'name': self.name,
            'langVersion': self.lang_spec['defines']['version'],
            'langID': self.lang_spec['defines']['id'],
            'malVersion': '0.1.0-SNAPSHOT',
            'info': 'Created by the mal-toolbox model python module.'
        }

        logger.debug('Translating assets to json.')
        for asset in self.assets:
            (asset_id, asset_json) = self.asset_to_json(asset)
            contents['assets'][asset_id] = asset_json

        logger.debug('Translating associations to json.')
        for association in self.associations:
            assoc_json = self.association_to_json(association)
            contents['associations'].append(assoc_json)

        logger.debug('Translating attackers to json.')
        for attacker in self.attackers:
            (attacker_id, attacker_json) = self.attacker_to_json(attacker)
            contents['attackers'][attacker_id] = attacker_json
        return contents

    def save_to_file(self, filename):
        """
        Save model to a json file.

        Arguments:
        filename        - the name of the output file
        """

        logger.info(f'Saving model to {filename} file.')
        contents = self.model_to_json()
        fp = open(filename, 'w')
        json.dump(contents, fp, indent = 2)

    def load_from_file(self, filename):
        """
        Load model from a json file.

        Arguments:
        filename        - the name of the input file
        """
        logger.info(f'Loading model from {filename} file.')
        with open(filename, 'r', encoding='utf-8') as model_file:
            json_model = json.loads(model_file.read())

        self.name = json_model['metadata']['name']

        # Reconstruct the assets
        for asset_id in json_model['assets']:
            asset_object = json_model['assets'][asset_id]
            logger.debug(f'Loading asset from {filename}:\n' \
                + json.dumps(asset_object, indent = 2))
            asset = getattr(self.lang_classes_factory.ns,
                asset_object['metaconcept'])(name = asset_object['name'])
            for defense in asset_object['defenses']:
                setattr(asset, defense,
                    float(asset_object['defenses'][defense]))
            self.add_asset(asset, asset_id = int(asset_id))

        # Reconstruct the associations
        if 'associations' in json_model:
            for association_object in json_model['associations']:
                association = getattr(self.lang_classes_factory.ns,
                    association_object['metaconcept'])()
                for field in association_object['association']:
                    asset_list = []
                    for asset_id in association_object['association'][field]:
                        asset_list.append(self.get_asset_by_id(int(asset_id)))
                    setattr(association, field, asset_list)
                self.add_association(association)

        # Reconstruct the attackers
        if 'attackers' in json_model:
            attackers_info = json_model['attackers']
            for attacker_id in attackers_info:
                attacker = Attacker(name = attackers_info[attacker_id]['name'])
                attacker.entry_points = []
                for asset_id in attackers_info[attacker_id]['entry_points']:
                    attacker.entry_points.append(
                        (self.get_asset_by_id(int(asset_id)),
                        attackers_info[attacker_id]['entry_points']\
                            [asset_id]['attack_steps']))
                self.add_attacker(attacker, attacker_id = int(attacker_id))
