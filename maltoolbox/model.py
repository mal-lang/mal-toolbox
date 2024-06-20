"""
MAL-Toolbox Model Module
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import logging
from typing import TYPE_CHECKING

from .file_utils import (
    load_dict_from_json_file,
    load_dict_from_yaml_file,
    save_dict_to_file
)

from . import __version__
from .exceptions import DuplicateModelAssociationError, ModelAssociationException

if TYPE_CHECKING:
    from typing import Any, Optional, TypeAlias
    from .language import LanguageClassesFactory
    from python_jsonschema_objects.classbuilder import ProtocolBase

    SchemaGeneratedClass: TypeAlias = ProtocolBase

logger = logging.getLogger(__name__)

@dataclass
class AttackerAttachment:
    """Used to attach attackers to attack step entrypoints of assets"""
    id: Optional[int] = None
    name: Optional[str] = None
    entry_points: list[tuple] = field(default_factory=lambda: [])

class Model():
    """An implementation of a MAL language with assets and associations"""
    next_id: int = 0

    def __repr__(self) -> str:
        return f'Model {self.name}'

    def __init__(
            self,
            name: str,
            lang_classes_factory: LanguageClassesFactory,
            mt_version: str = __version__
        ):

        self.name = name
        self.assets: list[SchemaGeneratedClass] = []
        self.associations: list[SchemaGeneratedClass] = []
        self._type_to_association:dict = {} # optimization
        self.attackers: list[AttackerAttachment] = []
        self.lang_classes_factory: LanguageClassesFactory = lang_classes_factory
        self.maltoolbox_version: str = mt_version

        # Below sets used to check for duplicate names or ids,
        # better for optimization than iterating over all assets
        self.asset_ids: set[int] = set()
        self.asset_names: set[str] = set()

    def add_asset(
            self,
            asset: SchemaGeneratedClass,
            asset_id: Optional[int] = None,
            allow_duplicate_names: bool = True
        ) -> None:
        """Add an asset to the model.

        Arguments:
        asset                   - the asset to add to the model
        asset_id                - the id to assign to this asset, usually
                                  from an instance model file
        allow_duplicate_name    - allow duplicate names to be used. If allowed
                                  and a duplicate is encountered the name will
                                  be appended with the id.

        Return:
        An asset matching the name if it exists in the model.
        """

        # Set asset ID and check for duplicates
        asset.id = asset_id or self.next_id
        if asset.id in self.asset_ids:
            raise ValueError(f'Asset index {asset_id} already in use.')
        self.asset_ids.add(asset.id)

        self.next_id = max(asset.id + 1, self.next_id)

        asset.associations = []

        if not hasattr(asset, 'name'):
            asset.name = asset.type + ':' + str(asset.id)
        else:
            if asset.name in self.asset_names:
                if allow_duplicate_names:
                    asset.name = asset.name + ':' + str(asset.id)
                else:
                    raise ValueError(
                        f'Asset name {asset.name} is a duplicate'
                        ' and we do not allow duplicates.'
                    )
        self.asset_names.add(asset.name)

        # Optional field for extra asset data
        asset.extras = {}

        logger.debug(
            'Add "%s"(%d) to model "%s".', asset.name, asset.id, self.name
        )
        self.assets.append(asset)

    def remove_asset(self, asset: SchemaGeneratedClass) -> None:
        """Remove an asset from the model.

        Arguments:
        asset     - the asset to remove
        """

        logger.debug(
            'Remove "%s"(%d) from model "%s".',
            asset.name, asset.id, self.name
        )
        if asset not in self.assets:
            raise LookupError(
                f'Asset "{asset.name}"({asset.id}) is not part'
                f' of model"{self.name}".'
            )

        # First remove all of the associations
        for association in asset.associations:
            self.remove_asset_from_association(asset, association)

        self.assets.remove(asset)

    def remove_asset_from_association(
            self,
            asset: SchemaGeneratedClass,
            association: SchemaGeneratedClass
        ) -> None:
        """Remove an asset from an association and remove the association
        if any of the two sides is now empty.

        Arguments:
        asset           - the asset to remove from the given association
        association     - the association to remove the asset from
        """

        logger.debug(
            'Remove "%s"(%d) from association of type "%s".',
            asset.name, asset.id, type(association)
        )

        if asset not in self.assets:
            raise LookupError(
                f'Asset "{asset.name}"({asset.id}) is not part of model '
                f'"{self.name}".'
            )
        if association not in self.associations:
            raise LookupError(
                f'Association is not part of model "{self.name}".'
            )

        first_field_name, second_field_name = association._properties.keys()
        first_field = getattr(association, first_field_name)
        second_field = getattr(association, second_field_name)
        found = False
        for field in [first_field, second_field]:
            if asset in field:
                found = True
                if len(field) == 1:
                    # There are no other assets on this side,
                    # so we should remove the entire association.
                    self.remove_association(association)
                    return
                field.remove(asset)

        if not found:
            raise LookupError(f'Asset "{asset.name}"({asset.id}) is not '
                'part of the association provided.')

    def _validate_association(self, association: SchemaGeneratedClass) -> None:
        """Raise error if association is invalid or already part of the Model.

        Raises:
            DuplicateAssociationError - same association already exists
            ModelAssociationException - association is not valid
        """

        # Optimization: only look for duplicates in associations of same type
        association_type = association.__class__.__name__
        associations_same_type = self._type_to_association.get(
            association_type, []
        )

        # Check if identical association already exists
        if association in associations_same_type:
            raise DuplicateModelAssociationError(
                f"Identical association {association_type} already exists"
            )


        # Check for duplicate assets in each field
        left_field_name, right_field_name = association._properties.keys()

        for field_name in (left_field_name, right_field_name):
            field_assets = getattr(association, field_name)

            unique_field_asset_names = {a.name for a in field_assets}
            if len(field_assets) > len(unique_field_asset_names):
                raise ModelAssociationException(
                    "More than one asset share same name in field"
                    f"{association_type}.{field_name}"
                )

        # For each asset in left field, go through each assets in right field
        # to find all unique connections. Raise error if a connection between
        # two assets already exist in a previously added association.
        for left_asset in getattr(association, left_field_name):
            for right_asset in getattr(association, right_field_name):

                if self.association_exists_between_assets(
                    association_type, left_asset, right_asset
                ):
                    # Assets already have the connection in another
                    # association with same type
                    raise DuplicateModelAssociationError(
                        f"Association type {association_type} already exists"
                        f" between {left_asset.name} and {right_asset.name}"
                    )

    def add_association(self, association: SchemaGeneratedClass) -> None:
        """Add an association to the model.

        An association will have 2 field names, each
        potentially containing several assets.

        Arguments:
        association     - the association to add to the model

        Raises:
        DuplicateAssociationError - same association already exists
        ModelAssociationException - association is not valid

        """

        # Check association is valid and not duplicate
        self._validate_association(association)

        # Optional field for extra association data
        association.extras = {}

        # Field names are the two first values in _properties
        field_names = list(vars(association)['_properties'])[0:2]

        # Add the association to all of the included assets
        for field_name in field_names:
            for asset in getattr(association, field_name):
                asset_assocs = list(asset.associations)
                asset_assocs.append(association)
                asset.associations = asset_assocs

        self.associations.append(association)

        # Add association to type->association mapping
        association_type = association.__class__.__name__
        self._type_to_association.setdefault(
                association_type, []
            ).append(association)


    def remove_association(self, association: SchemaGeneratedClass) -> None:
        """Remove an association from the model.

        Arguments:
        association     - the association to remove from the model
        """

        if association not in self.associations:
            raise LookupError(
                f'Association is not part of model "{self.name}".'
            )

        # An assocation goes from one field to another,
        # both fields has a field_name and a list of assets
        first_field_name, second_field_name = association._properties.keys()
        first_field = getattr(association, first_field_name)
        second_field = getattr(association, second_field_name)

        for asset in first_field:
            assocs = list(asset.associations)
            assocs.remove(association)
            asset.associations = assocs

        for asset in second_field:
            # In fringe cases we may have reflexive associations where the
            # first element was removed  from the association already. But
            # generally the association should exist for the second element
            # too.
            if association in asset.associations:
                assocs = list(asset.associations)
                assocs.remove(association)
                asset.associations = assocs

        self.associations.remove(association)

        # Remove association from type->association mapping
        association_type = association.__class__.__name__
        self._type_to_association[association_type].remove(
            association
        )
        # Remove type from type->association mapping if mapping empty
        if len(self._type_to_association[association_type]) == 0:
            del self._type_to_association[association_type]

    def add_attacker(
            self,
            attacker: AttackerAttachment,
            attacker_id: Optional[int] = None
        ) -> None:
        """Add an attacker to the model.

        Arguments:
        attacker        - the attacker to add
        attacker_id     - optional id for the attacker
        """

        if attacker_id is not None:
            attacker.id = attacker_id
        else:
            attacker.id = self.next_id
        self.next_id = max(attacker.id + 1, self.next_id)

        if not hasattr(attacker, 'name') or not attacker.name:
            attacker.name = 'Attacker:' + str(attacker.id)
        self.attackers.append(attacker)

    def get_asset_by_id(
            self, asset_id: int
        ) -> Optional[SchemaGeneratedClass]:
        """
        Find an asset in the model based on its id.

        Arguments:
        asset_id        - the id of the asset we are looking for

        Return:
        An asset matching the id if it exists in the model.
        """
        logger.debug(
            'Get asset with id %d from model "%s".',
            asset_id, self.name
        )
        return next(
                (asset for asset in self.assets
                if asset.id == asset_id), None
             )

    def get_asset_by_name(
            self, asset_name: str
        ) -> Optional[SchemaGeneratedClass]:
        """
        Find an asset in the model based on its name.

        Arguments:
        asset_name        - the name of the asset we are looking for

        Return:
        An asset matching the name if it exists in the model.
        """
        logger.debug(
            'Get asset with name "%s" from model "%s".',
            asset_name, self.name
        )
        return next(
                (asset for asset in self.assets
                if asset.name == asset_name), None
             )

    def get_attacker_by_id(
            self, attacker_id: int
        ) -> Optional[AttackerAttachment]:
        """
        Find an attacker in the model based on its id.

        Arguments:
        attacker_id     - the id of the attacker we are looking for

        Return:
        An attacker matching the id if it exists in the model.
        """
        logger.debug(
            'Get attacker with id %d from model "%s".',
            attacker_id, self.name
        )
        return next(
                (attacker for attacker in self.attackers
                if attacker.id == attacker_id), None
            )

    def association_exists_between_assets(
            self, association_type, left_asset, right_asset
        ):
        """Return True if the association already exists between the assets"""
        associations = self._type_to_association.get(association_type, [])
        for association in associations:
            field_name1, field_name2 = association._properties.keys()
            if left_asset in getattr(association, field_name1):
                if right_asset in getattr(association, field_name2):
                    return True
            return False

    def get_associated_assets_by_field_name(
            self,
            asset: SchemaGeneratedClass,
            field_name: str
        ) -> list[SchemaGeneratedClass]:
        """
        Get a list of associated assets for an asset given a field name.

        Arguments:
        asset           - the asset whose fields we are interested in
        field_name       - the field name we are looking for

        Return:
        A list of assets associated with the asset given that match the
        field_name.
        """

        logger.debug(
            'Get associated assets for asset "%s"(%d) by field name %s.',
            asset.name, asset.id, field_name
        )
        associated_assets = []
        for association in asset.associations:
            # Determine which two of the fields leads away from the asset.
            # This is particularly relevant for associations between two
            # assets of the same type.
            field_name1, field_name2 = association._properties.keys()

            if asset in getattr(association, field_name1):
                # If the asset is in the first field,
                # the second one must lead away from it
                field_name_away = field_name2
            else:
                # otherwise the first field must lead away
                field_name_away = field_name1

            if field_name_away == field_name:
                associated_assets.extend(
                    getattr(association, field_name_away)
                )

        return associated_assets

    def asset_to_dict(self, asset: SchemaGeneratedClass) -> tuple[str, dict]:
        """Get dictionary representation of the asset.

        Arguments:
        asset       - asset to get dictionary representation of

        Return: tuple with name of asset and the asset as dict
        """

        defenses = {}
        logger.debug(
            'Translating "%s"(%d) to dictionary.',
            asset.name,
            asset.id
        )

        for key, value in asset._properties.items():
            property_schema = (
                self.lang_classes_factory.json_schema['definitions']['LanguageAsset']
                ['definitions'][asset.type]['properties'][key]
            )

            if "maximum" not in property_schema:
                # Check if property is a defense by looking up defense
                # specific key. Skip if it is not a defense.
                continue

            logger.debug('Translating %s: %s defense to dictionary.', key, value)

            if value == value.default():
                # Skip the defense values if they are the default ones.
                continue

            defenses[key] = float(value)

        asset_dict: dict[str, Any] = {
            'name': str(asset.name),
            'type': str(asset.type)
        }

        if defenses:
            asset_dict['defenses'] = defenses

        if asset.extras:
            # Add optional metadata to dict
            asset_dict['extras'] = asset.extras

        return (asset.id, asset_dict)


    def association_to_dict(self, association: SchemaGeneratedClass) -> dict:
        """Get dictionary representation of the association.

        Arguments:
        association     - association to get dictionary representation of

        Returns the association serialized to a dict
        """

        first_field_name, second_field_name = association._properties.keys()
        first_field = getattr(association, first_field_name)
        second_field = getattr(association, second_field_name)

        association_dict = {
            association.__class__.__name__ :
            {
                str(first_field_name):
                    [int(asset.id) for asset in first_field],
                str(second_field_name):
                    [int(asset.id) for asset in second_field]
            }
        }

        if association.extras:
            # Add optional metadata to dict
            association_dict['extras'] = association.extras

        return association_dict

    def attacker_to_dict(
            self, attacker: AttackerAttachment
        ) -> tuple[Optional[int], dict]:
        """Get dictionary representation of the attacker.

        Arguments:
        attacker    - attacker to get dictionary representation of
        """

        logger.debug('Translating %s to dictionary.', attacker.name)
        attacker_dict: dict[str, Any] = {
            'name': str(attacker.name),
            'entry_points': {},
        }
        for (asset, attack_steps) in attacker.entry_points:
            attacker_dict['entry_points'][int(asset.id)] = {
                'attack_steps' : attack_steps
            }
        return (attacker.id, attacker_dict)

    def _to_dict(self) -> dict:
        """Get dictionary representation of the model."""
        logger.debug('Translating model to dict.')
        contents: dict[str, Any] = {
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
            'MAL-Toolbox Version': __version__,
            'info': 'Created by the mal-toolbox model python module.'
        }

        logger.debug('Translating assets to dictionary.')
        for asset in self.assets:
            (asset_id, asset_dict) = self.asset_to_dict(asset)
            contents['assets'][int(asset_id)] = asset_dict

        logger.debug('Translating associations to dictionary.')
        for association in self.associations:
            assoc_dict = self.association_to_dict(association)
            contents['associations'].append(assoc_dict)

        logger.debug('Translating attackers to dictionary.')
        for attacker in self.attackers:
            (attacker_id, attacker_dict) = self.attacker_to_dict(attacker)
            contents['attackers'][attacker_id] = attacker_dict
        return contents

    def save_to_file(self, filename: str) -> None:
        """Save to json/yml depending on extension"""
        logger.debug('Save instance model to file "%s".', filename)
        return save_dict_to_file(filename, self._to_dict())

    @classmethod
    def _from_dict(
        cls,
        serialized_object: dict,
        lang_classes_factory: LanguageClassesFactory
        ) -> Model:
        """Create a model from dict representation

        Arguments:
        serialized_object    - Model in dict format
        lang_classes_factory -
        """

        maltoolbox_version = serialized_object['metadata']['MAL Toolbox Version'] \
            if 'MAL Toolbox Version' in serialized_object['metadata'] \
            else __version__
        model = Model(
            serialized_object['metadata']['name'],
            lang_classes_factory,
            mt_version = maltoolbox_version)

        # Reconstruct the assets
        for asset_id, asset_object in serialized_object['assets'].items():

            if logger.isEnabledFor(logging.DEBUG):
                # Avoid running json.dumps when not in debug
                logger.debug(
                    "Loading asset:\n%s", json.dumps(asset_object, indent=2)
                )

            # Allow defining an asset via type only.
            asset_object = (
                asset_object
                if isinstance(asset_object, dict)
                else {
                    'type': asset_object,
                    'name': f"{asset_object}:{asset_id}"
                }
            )

            asset = getattr(model.lang_classes_factory.ns,
                asset_object['type'])(name = asset_object['name'])

            for defense in (defenses:=asset_object.get('defenses', [])):
                setattr(asset, defense, float(defenses[defense]))

            model.add_asset(asset, asset_id = int(asset_id))

        # Reconstruct the associations
        for assoc_entry in serialized_object.get('associations', []):
            assoc = list(assoc_entry.keys())[0]
            assoc_fields = assoc_entry[assoc]
            association = getattr(model.lang_classes_factory.ns, assoc)()

            for field, targets in assoc_fields.items():
                targets = targets if isinstance(targets, list) else [targets]
                setattr(
                    association,
                    field,
                    [model.get_asset_by_id(int(id)) for id in targets]
                )
            model.add_association(association)

        # Reconstruct the attackers
        if 'attackers' in serialized_object:
            attackers_info = serialized_object['attackers']
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

    @classmethod
    def load_from_file(
        cls,
        filename: str,
        lang_classes_factory: LanguageClassesFactory
        ) -> Model:
        """Create from json or yaml file depending on file extension"""
        logger.debug('Load instance model from file "%s".', filename)
        serialized_model = None
        if filename.endswith(('.yml', '.yaml')):
            serialized_model = load_dict_from_yaml_file(filename)
        elif filename.endswith('.json'):
            serialized_model = load_dict_from_json_file(filename)
        else:
            raise ValueError('Unknown file extension, expected json/yml/yaml')
        return cls._from_dict(serialized_model, lang_classes_factory)
