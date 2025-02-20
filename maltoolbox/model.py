"""
MAL-Toolbox Model Module
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import logging
from typing import TYPE_CHECKING
import math

from .file_utils import (
    load_dict_from_json_file,
    load_dict_from_yaml_file,
    save_dict_to_file
)

from . import __version__
from .exceptions import ModelException

if TYPE_CHECKING:
    from typing import Any, Optional
    from .language import (
        LanguageGraph,
        LanguageGraphAsset,
    )

logger = logging.getLogger(__name__)

@dataclass
class AttackerAttachment:
    """Used to attach attackers to attack step entry points of assets"""
    id: Optional[int] = None
    name: Optional[str] = None
    entry_points: list[tuple[ModelAsset, list[str]]] = \
        field(default_factory=lambda: [])


    def get_entry_point_tuple(
            self,
            asset: ModelAsset
        ) -> Optional[tuple[ModelAsset, list[str]]]:
        """Return an entry point tuple of an AttackerAttachment matching the
        asset provided.


        Arguments:
        asset           - the asset to add entry point to

        Return:
        The entry point tuple containing the asset and the list of attack
        steps if the asset has any entry points defined for this attacker
        attachemnt.
        None, otherwise.
        """
        return next((ep_tuple for ep_tuple in self.entry_points
                                 if ep_tuple[0] == asset), None)


    def add_entry_point(
            self, asset: ModelAsset, attackstep_name: str):
        """Add an entry point to an AttackerAttachment

        self.entry_points contain tuples, first element of each tuple
        is an asset, second element is a list of attack step names that
        are entry points for the attacker.

        Arguments:
        asset           - the asset to add the entry point to
        attackstep_name - the name of the attack step to add as an entry point
        """

        logger.debug(
            f'Add entry point "{attackstep_name}" on asset "{asset.name}" '
            f'to AttackerAttachment "{self.name}".'
        )

        # Get the entry point tuple for the asset if it already exists
        entry_point_tuple = self.get_entry_point_tuple(asset)

        if entry_point_tuple:
            if attackstep_name not in entry_point_tuple[1]:
                # If it exists and does not already have the attack step,
                # add it
                entry_point_tuple[1].append(attackstep_name)
            else:
                logger.info(
                    f'Entry point "{attackstep_name}" on asset "{asset.name}"'
                    f' already existed for AttackerAttachment "{self.name}".'
                )
        else:
            # Otherwise, create the entry point tuple and the initial entry
            # point
            self.entry_points.append((asset, [attackstep_name]))


    def remove_entry_point(
            self, asset: ModelAsset, attackstep_name: str):
        """Remove an entry point from an AttackerAttachment if it exists

        Arguments:
        asset           - the asset to remove the entry point from
        """

        logger.debug(
            f'Remove entry point "{attackstep_name}" on asset "{asset.name}" '
            f'from AttackerAttachment "{self.name}".'
        )

        # Get the entry point tuple for the asset if it exists
        entry_point_tuple = self.get_entry_point_tuple(asset)

        if entry_point_tuple:
            if attackstep_name in entry_point_tuple[1]:
                # If it exists and not already has the attack step, add it
                entry_point_tuple[1].remove(attackstep_name)
            else:
                logger.warning(
                    f'Failed to find entry point "{attackstep_name}" on '
                    f'asset "{asset.name}" for AttackerAttachment '
                    f'"{self.name}". Nothing to remove.'
                )

            if not entry_point_tuple[1]:
                self.entry_points.remove(entry_point_tuple)
        else:
            logger.warning(
                f'Failed to find entry points on asset "{asset.name}" '
                f'for AttackerAttachment "{self.name}". Nothing to remove.'
            )


class Model():
    """An implementation of a MAL language model containing assets"""
    next_id: int = 0

    def __repr__(self) -> str:
        return f'Model(name: "{self.name}", language: {self.lang_graph})'


    def __init__(
            self,
            name: str,
            lang_graph: LanguageGraph,
            mt_version: str = __version__
        ):

        self.name = name
        self.assets: dict[int, ModelAsset] = {}
        self._name_to_asset:dict[str, ModelAsset] = {} # optimization
        self.attackers: list[AttackerAttachment] = []
        self.lang_graph = lang_graph
        self.maltoolbox_version: str = mt_version


    def add_asset(
            self,
            asset_type: str,
            name: Optional[str] = None,
            asset_id: Optional[int] = None,
            defenses: Optional[dict[str, float]] = None,
            extras: Optional[dict] = None,
            allow_duplicate_names: bool = True
        ) -> ModelAsset:
        """
        Create an asset based on the provided parameters and add it to the
        model.

        Arguments:
        asset_type              - string containing the asset type name
        name                    - string containing the asset name. If not
                                  provided the concatenated asset type and id
                                  will be used as a name.
        asset_id                - id to assign to this asset, usually from an
                                  instance model file. If not provided the id
                                  will be set to the next highest id
                                  available.
        defeses                 - dictionary of defense values
        extras                  - dictionary of extras
        allow_duplicate_name    - allow duplicate names to be used. If allowed
                                  and a duplicate is encountered the name will
                                  be appended with the id.

        Return:
        The newly created asset.
        """

        # Set asset ID and check for duplicates
        asset_id = asset_id or self.next_id
        if asset_id in self.assets:
            raise ValueError(f'Asset index {asset_id} already in use.')

        self.next_id = max(asset_id + 1, self.next_id)

        if not name:
            name = asset_type + ':' + str(asset_id)
        else:
            if name in self._name_to_asset:
                if allow_duplicate_names:
                    name = name + ':' + str(asset_id)
                else:
                    raise ValueError(
                        f'Asset name {name} is a duplicate'
                        ' and we do not allow duplicates.'
                    )

        lg_asset = self.lang_graph.assets[asset_type]

        asset = ModelAsset(
            name = name,
            asset_id = asset_id,
            lg_asset = lg_asset,
            defenses = defenses,
            extras = extras)

        logger.debug(
            'Add "%s"(%d) to model "%s".', name, asset_id, self.name
        )
        self.assets[asset_id] = asset
        self._name_to_asset[name] = asset

        return asset


    def remove_attacker(self, attacker: AttackerAttachment) -> None:
        """Remove attacker"""
        self.attackers.remove(attacker)


    def remove_asset(self, asset: ModelAsset) -> None:
        """Remove an asset from the model.

        Arguments:
        asset     - the asset to remove
        """

        logger.debug(
            'Remove "%s"(%d) from model "%s".',
            asset.name, asset.id, self.name
        )
        if asset.id not in self.assets:
            raise LookupError(
                f'Asset "{asset.name}"({asset.id}) is not part'
                f' of model"{self.name}".'
            )

        # First remove all of the associated assets
        # We can not remove from the dict while iterating over it
        # so we first have to copy the keys and then remove those assets
        associated_fieldnames = dict(asset.associated_assets)
        for fieldname, assoc_assets in associated_fieldnames.items():
            asset.remove_associated_assets(fieldname, assoc_assets)

        # Also remove all of the entry points
        for attacker in self.attackers:
            entry_point_tuple = attacker.get_entry_point_tuple(asset)
            if entry_point_tuple:
                attacker.entry_points.remove(entry_point_tuple)

        del self.assets[asset.id]
        del self._name_to_asset[asset.name]


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
        ) -> Optional[ModelAsset]:
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
        return self.assets.get(asset_id, None)


    def get_asset_by_name(
            self, asset_name: str
        ) -> Optional[ModelAsset]:
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
        return self._name_to_asset.get(asset_name, None)


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


    def attacker_to_dict(
            self, attacker: AttackerAttachment
        ) -> tuple[Optional[int], dict]:
        """Get dictionary representation of the attacker.

        Arguments:
        attacker    - attacker to get dictionary representation of
        """

        logger.debug('Translating %s to dictionary.', attacker.name)
        attacker_dict: dict[str, Any] = {
            'name': attacker.name,
            'entry_points': {},
        }
        for (asset, attack_steps) in attacker.entry_points:
            attacker_dict['entry_points'][asset.name] = {
                'asset_id': asset.id,
                'attack_steps' : attack_steps
            }
        return (attacker.id, attacker_dict)


    def _to_dict(self) -> dict:
        """Get dictionary representation of the model."""
        logger.debug('Translating model to dict.')
        contents: dict[str, Any] = {
            'metadata': {},
            'assets': {},
            'attackers' : {}
        }
        contents['metadata'] = {
            'name': self.name,
            'langVersion': self.lang_graph.metadata['version'],
            'langID': self.lang_graph.metadata['id'],
            'malVersion': '0.1.0-SNAPSHOT',
            'MAL-Toolbox Version': __version__,
            'info': 'Created by the mal-toolbox model python module.'
        }

        logger.debug('Translating assets to dictionary.')
        for asset in self.assets.values():
            contents['assets'].update(asset._to_dict())

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
        lang_graph: LanguageGraph,
        ) -> Model:
        """Create a model from dict representation

        Arguments:
        serialized_object    - Model in dict format
        lang_graph -
        """

        maltoolbox_version = serialized_object['metadata']['MAL Toolbox Version'] \
            if 'MAL Toolbox Version' in serialized_object['metadata'] \
            else __version__
        model = Model(
            serialized_object['metadata']['name'],
            lang_graph,
            mt_version = maltoolbox_version)

        # Reconstruct the assets
        for asset_id, asset_dict in serialized_object['assets'].items():

            if logger.isEnabledFor(logging.DEBUG):
                # Avoid running json.dumps when not in debug
                logger.debug(
                    "Loading asset:\n%s", json.dumps(asset_dict, indent=2)
                )

            # Allow defining an asset via type only.
            asset_dict = (
                asset_dict
                if isinstance(asset_dict, dict)
                else {
                    'type': asset_dict,
                    'name': f"{asset_dict}:{asset_id}"
                }
            )

            model.add_asset(
                asset_type = asset_dict['type'],
                name = asset_dict['name'],
                defenses = {defense: float(value) for defense, value in \
                    asset_dict.get('defenses', {}).items()},
                extras = asset_dict.get('extras', {}),
                asset_id = int(asset_id))

        # Reconstruct the association links
        for asset_id, asset_dict in serialized_object['assets'].items():
            asset = model.assets[int(asset_id)]
            assoc_assets_dict = asset_dict['associated_assets'].items()
            for fieldname, assoc_assets in assoc_assets_dict:
                asset.add_associated_assets(
                    fieldname,
                    {model.assets[int(assoc_asset_id)]
                        for assoc_asset_id in assoc_assets}
                )

        # Reconstruct the attackers
        if 'attackers' in serialized_object:
            attackers_info = serialized_object['attackers']
            for attacker_id in attackers_info:
                attacker = AttackerAttachment(name = attackers_info[attacker_id]['name'])
                attacker.entry_points = []
                for asset_name, entry_points_dict in \
                        attackers_info[attacker_id]['entry_points'].items():
                    target_asset = model.get_asset_by_id(
                        entry_points_dict['asset_id'])
                    if target_asset is None:
                        raise LookupError(
                            'Asset "%s"(%d) is not part of model "%s".' % (
                                asset_name,
                                entry_points_dict['asset_id'],
                                model.name)
                        )
                    attacker.entry_points.append(
                            (
                                target_asset,
                                entry_points_dict['attack_steps']
                            )
                        )
                model.add_attacker(attacker, attacker_id = int(attacker_id))
        return model


    @classmethod
    def load_from_file(
        cls,
        filename: str,
        lang_graph: LanguageGraph,
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
        try:
            return cls._from_dict(serialized_model, lang_graph)
        except Exception as e:
            raise ModelException(
                "Could not load model. It might be of an older version. "
                "Try to upgrade it with 'maltoolbox upgrade-model'"
            ) from e


class ModelAsset:
    def __init__(
        self,
        name: str,
        asset_id: int,
        lg_asset: LanguageGraphAsset,
        defenses: Optional[dict[str, float]] = None,
        extras: Optional[dict] = None
    ):

        self.name: str = name
        self._id: int = asset_id
        self.lg_asset: LanguageGraphAsset = lg_asset
        self.type = self.lg_asset.name
        self.defenses: dict[str, float] = defenses or {}
        self.extras: dict = extras or {}
        self._associated_assets: dict[str, set[ModelAsset]] = {}
        self.attack_step_nodes: list = []

        for step in self.lg_asset.attack_steps.values():
            if step.type == 'defense' and step.name not in self.defenses:
                self.defenses[step.name] = 1.0 if step.ttc and \
                    step.ttc['name'] == 'Enabled' else 0.0


    def _to_dict(self):
        """Get dictionary representation of the asset."""

        logger.debug(
            'Translating "%s"(%d) to dictionary.', self.name, self.id)

        asset_dict: dict[str, Any] = {
            'name': self.name,
            'type': self.type,
            'defenses': {},
            'associated_assets': {}
        }

        # Only add non-default values for defenses to improve legibility of
        # the model format
        for defense, defense_value in self.defenses.items():
            lg_step = self.lg_asset.attack_steps[defense]
            default_defval = 1.0 if lg_step.ttc and \
                    lg_step.ttc['name'] == 'Enabled' else 0.0
            if defense_value != default_defval:
                asset_dict['defenses'][defense] = defense_value

        for fieldname, assets in self.associated_assets.items():
            asset_dict['associated_assets'][fieldname] = {asset.id: asset.name
                for asset in assets}

        if len(asset_dict['defenses']) == 0:
            # Do not include an empty defenses dictionary
            del asset_dict['defenses']

        if self.extras != {}:
            # Add optional metadata to dict
            asset_dict['extras'] = self.extras

        return {self.id: asset_dict}


    def __repr__(self):
        return (f'ModelAsset(name: "{self.name}", id: {self.id}, '
            f'type: {self.type})')


    def validate_associated_assets(
            self, fieldname: str, assets_to_add: set[ModelAsset]
        ):
        """
        Validate an association we want to add (through `fieldname`)
        is valid with the assets given in param `assets_to_add`:
        - fieldname is valid for the asset type of this ModelAsset
        - type of `assets_to_add` is valid for the association
        - no more assets than 'field.maximum' are added to the field

        Raises:
            LookupError - fieldname can not be found for this ModelAsset
            ValueError - there will be too many assets in the field
                         if we add this association
            TypeError - if the asset type of `assets_to_add` is not valid
        """

        # Validate that the field name is allowed for this asset type
        if fieldname not in self.lg_asset.associations:
            accepted_fieldnames = list(self.lg_asset.associations.keys())
            raise LookupError(
                f"Fieldname '{fieldname}' is not an accepted association "
                f"fieldname from asset type {self.lg_asset.name}. "
                f"Did you mean one of {accepted_fieldnames}?"
            )

        lg_assoc = self.lg_asset.associations[fieldname]
        assoc_field = lg_assoc.get_field(fieldname)

        # Validate that the asset to add association to is of correct type
        for asset_to_add in assets_to_add:
            if not asset_to_add.lg_asset.is_subasset_of(assoc_field.asset):
                raise TypeError(
                    f"Asset '{asset_to_add.name}' of type "
                    f"'{asset_to_add.type}' can not be added to association "
                    f"'{self.name}.{fieldname}'. Expected type of "
                    f"'{fieldname}' is {assoc_field.asset.name}."
            )

        # Validate that there will not be too many assets in field
        assets_in_field_before = self.associated_assets.get(fieldname, set())
        assets_in_field_after = assets_in_field_before | set(assets_to_add)
        max_assets_in_field = assoc_field.maximum or math.inf

        if len(assets_in_field_after) > max_assets_in_field:
            raise ValueError(
                f"You can have maximum {assoc_field.maximum} "
                f"assets for association field {fieldname}"
            )

    def add_associated_assets(self, fieldname: str, assets: set[ModelAsset]):
        """
        Add the assets provided as a parameter to the set of associated
        assets dictionary entry corresponding to the given fieldname.
        """

        lg_assoc = self.lg_asset.associations[fieldname]
        other_fieldname = lg_assoc.get_opposite_fieldname(fieldname)

        # Validation from both sides
        self.validate_associated_assets(fieldname, assets)
        for asset in assets:
            asset.validate_associated_assets(other_fieldname, {self})

        # Add the associated assets to this asset's dictionary
        self._associated_assets.setdefault(
            fieldname, set()
        ).update(assets)

        # Add this asset to the associated assets' corresponding dictionaries
        for asset in assets:
            asset._associated_assets.setdefault(
                other_fieldname, set()
            ).add(self)

    def remove_associated_assets(
            self, fieldname: str, assets: set[ModelAsset]):
        """ Remove the assets provided as a parameter from the set of
        associated assets dictionary entry corresponding to the fieldname
        parameter.
        """
        # Remove this asset from its associated assets' dictionaries
        lg_assoc = self.lg_asset.associations[fieldname]
        other_fieldname = lg_assoc.get_opposite_fieldname(fieldname)
        for asset in assets:
            asset._associated_assets[other_fieldname].remove(self)
            if len(asset._associated_assets[other_fieldname]) == 0:
                del asset._associated_assets[other_fieldname]

        # Remove associated assets from this asset
        self._associated_assets[fieldname] -= set(assets)
        if len(self._associated_assets[fieldname]) == 0:
            del self._associated_assets[fieldname]


    @property
    def associated_assets(self):
        return self._associated_assets


    @property
    def id(self):
        return self._id
