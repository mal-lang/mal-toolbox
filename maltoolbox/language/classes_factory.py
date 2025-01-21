"""
MAL-Toolbox Language Classes Factory Module
Uses python_jsonschema_objects to generate python classes from a MAL language
"""
from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING

import python_jsonschema_objects as pjs

if TYPE_CHECKING:
    from typing import Literal, Optional, TypeAlias
    from maltoolbox.language import LanguageGraph
    from python_jsonschema_objects.classbuilder import ProtocolBase

    SchemaGeneratedClass: TypeAlias = ProtocolBase

logger = logging.getLogger(__name__)

class LanguageClassesFactory:
    def __init__(self, lang_graph: LanguageGraph):
        self.lang_graph: LanguageGraph = lang_graph
        self.json_schema: dict = {}
        self._create_classes()

    def _generate_assets(self) -> None:
        """
        Generate JSON Schema for asset types in the language specification.
        """
        for asset_name, asset in self.lang_graph.assets.items():
            logger.debug('Creating %s asset JSON schema entry.', asset.name)
            asset_json_entry = {
                'title': 'Asset_' + asset.name,
                'type': 'object',
                'properties': {},
            }
            asset_json_entry['properties']['id'] = {
                'type' : 'integer',
            }
            asset_json_entry['properties']['type'] = \
                {
                    'type' : 'string',
                    'default': asset_name
                }
            if asset.own_super_asset:
                asset_json_entry['allOf'] = [
                    {'$ref': '#/definitions/LanguageAsset/definitions/Asset_'\
                        + asset.own_super_asset.name}
                ]
            for step_name, step in asset.attack_steps.items():
                if step.type == 'defense':
                    if step.ttc and step.ttc['name'] == 'Enabled':
                        default_defense_value = 1.0
                    else:
                        default_defense_value = 0.0
                    asset_json_entry['properties'][step_name] = \
                        {
                            'type' : 'number',
                            'minimum' : 0,
                            'maximum' : 1,
                            'default': default_defense_value
                        }
            self.json_schema['definitions']['LanguageAsset']['definitions']\
                ['Asset_' + asset_name] = asset_json_entry
            self.json_schema['definitions']['LanguageAsset']['oneOf'].append(
                {'$ref': '#/definitions/LanguageAsset/definitions/Asset_' + asset_name}
            )

    def _generate_associations(self) -> None:
        """
        Generate JSON Schema for association types in the language specification.
        """
        def create_association_entry(assoc: SchemaGeneratedClass):
            logger.debug('Creating %s association JSON schema entry.', assoc.name)
            assoc_json_entry = {
                'title': 'Association_' + assoc.full_name,
                'type': 'object',
                'properties': {}
            }
            assoc_json_entry['properties']['type'] = \
                {
                    'type' : 'string',
                    'default': assoc.name
                }

            create_association_field(assoc, assoc_json_entry, 'left')
            create_association_field(assoc, assoc_json_entry, 'right')
            return assoc_json_entry

        def create_association_field(
                assoc: SchemaGeneratedClass,
                assoc_json_entry: dict,
                position: Literal['left', 'right']
            ) -> None:
            field = getattr(assoc, position + "_field")
            assoc_json_entry['properties'][field.fieldname] = \
                {
                    'type' : 'array',
                    'items' :
                        {
                        '$ref':
                        '#/definitions/LanguageAsset/definitions/Asset_' +
                            field.asset.name
                        }
                }
            if field.maximum:
                assoc_json_entry['properties'][field.fieldname]\
                    ['maxItems'] = field.maximum

        for asset_name, asset in self.lang_graph.assets.items():
            for assoc_name, assoc in asset.associations.items():
                if assoc_name not in self.json_schema['definitions']\
                        ['LanguageAssociation']['definitions']:
                    assoc_json_entry = create_association_entry(assoc)
                    self.json_schema['definitions']['LanguageAssociation']\
                        ['definitions']['Association_' + assoc_name] = \
                            assoc_json_entry
                    self.json_schema['definitions']['LanguageAssociation']['oneOf'].\
                        append({'$ref': '#/definitions/LanguageAssociation/' +
                        'definitions/Association_' + assoc_name})

    def _create_classes(self) -> None:
        """
        Create classes based on the language specification.
        """

        # First, we have to translate the language specification into a JSON
        # schema. Initialize the overall JSON schema structure.
        self.json_schema = {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'id': f"urn:mal:{__name__.replace('.', ':')}",
            'title': 'LanguageObject',
            'type': 'object',
            'oneOf':[
                {'$ref': '#/definitions/LanguageAsset'},
                {'$ref': '#/definitions/LanguageAssociation'}
            ],
            'definitions': {}}
        self.json_schema['definitions']['LanguageAsset'] = {
            'title': 'LanguageAsset',
            'type': 'object',
            'oneOf': [],
            'definitions': {}}
        self.json_schema['definitions']['LanguageAssociation'] = {
            'title': 'LanguageAssociation',
            'type': 'object',
            'oneOf': [],
            'definitions': {}}

        self._generate_assets()
        self._generate_associations()

        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(json.dumps(self.json_schema, indent = 2))

        # Once we have the JSON schema we create the actual classes.
        builder = pjs.ObjectBuilder(self.json_schema)
        self.ns = builder.build_classes(standardize_names=False)

    def get_association_by_signature(
        self,
        assoc_name: str,
        left_asset: str,
        right_asset: str
    ) -> Optional[str]:
        """
        Get association name based on its signature. This is primarily
        relevant for getting the exact association full name when multiple
        associations with the same name exist.

        Arguments:
        assoc_name          - the association name
        left_asset          - the name of the left asset type
        right_asset         - the name of the right asset type

        Return: The matching association name if a match is found.
        None if there is no match.
        """
        lang_assocs_entries = self.json_schema['definitions']\
                ['LanguageAssociation']['definitions']
        if not assoc_name in lang_assocs_entries:
            raise LookupError(
                'Failed to find "%s" association in the language json '
                'schema.' % assoc_name
            )
        assoc_entry = lang_assocs_entries[assoc_name]
        # If the association has a oneOf property it should always have more
        # than just one alternative, but check just in case
        if 'definitions' in assoc_entry and \
                len(assoc_entry['definitions']) > 1:
            full_name = '%s_%s_%s' % (
                assoc_name,
                left_asset,
                right_asset
            )
            full_name_flipped = '%s_%s_%s' % (
                assoc_name,
                right_asset,
                left_asset
            )
            if not full_name in assoc_entry['definitions']:
                if not full_name_flipped in assoc_entry['definitions']:
                    raise LookupError(
                        'Failed to find "%s" or "%s" association in the '
                        'language json schema.'
                        % (full_name,
                        full_name_flipped)
                    )
                else:
                    return full_name_flipped
            else:
                return full_name
        else:
            return assoc_name

    def get_asset_class(self,
            asset_name: str
        ) -> Optional[SchemaGeneratedClass]:
        class_name = 'Asset_' + asset_name
        if hasattr(self.ns, class_name):
            class_obj = getattr(self.ns, class_name)
            class_obj.__hash__ = lambda self: hash(self.name)
            return class_obj
        else:
            logger.warning('Could not find Asset "%s" in classes factory.' %
                asset_name)
            return None

    def get_association_class(self,
            assoc_name: str
        ) -> Optional[SchemaGeneratedClass]:
        class_name = 'Association_' + assoc_name
        if hasattr(self.ns, class_name):
            return getattr(self.ns, class_name)
        else:
            logger.warning('Could not find Association "%s" in classes factory.' %
                assoc_name)
            return None

    def get_association_class_by_fieldnames(self,
            assoc_name: str,
            fieldname1: str,
            fieldname2: str
        ) -> Optional[SchemaGeneratedClass]:
        class_name = 'Association_%s_%s_%s' % (assoc_name,
            fieldname1, fieldname2)
        class_name_alt = 'Association_%s_%s_%s' % (assoc_name,
            fieldname2, fieldname1)

        if hasattr(self.ns, class_name):
            return getattr(self.ns, class_name)
        elif hasattr(self.ns, class_name_alt):
            return getattr(self.ns, class_name_alt)
        else:
            logger.warning('Could not find Association "%s" or "%s" in '
                'classes factory.' % (class_name, class_name_alt))
            return None
