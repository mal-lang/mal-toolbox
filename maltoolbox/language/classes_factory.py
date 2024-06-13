"""
MAL-Toolbox Language Classes Factory Module
"""

import json
import logging
from typing import Any, Literal

import python_jsonschema_objects as pjs # type: ignore

from maltoolbox.language import LanguageGraph

logger = logging.getLogger(__name__)

class LanguageClassesFactory:
    def __init__(self, lang_graph: LanguageGraph):
        self.lang_graph: LanguageGraph = lang_graph
        self.json_schema: dict = {}
        self._create_classes()

    def _generate_assets(self) -> None:
        """
        Generate JSON Schema for the assets in the language specification.
        """
        for asset in self.lang_graph.assets:
            logger.debug(f'Creating {asset.name} asset JSON '\
            'schema entry.')
            asset_json_entry = {
                'title': asset.name,
                'type': 'object',
                'properties': {},
            }
            asset_json_entry['properties']['id'] = {
                'type' : 'integer',
            }
            asset_json_entry['properties']['type'] = \
                {
                    'type' : 'string',
                    'default': asset.name
                }
            if asset.super_assets:
                asset_json_entry['allOf'] = [
                    {'$ref': '#/definitions/LanguageAsset/definitions/' + superasset.name}
                    for superasset in asset.super_assets
                ]
            for defense in filter(lambda step: step.type == 'defense', asset.attack_steps):
                if defense.ttc and defense.ttc['name'] == 'Enabled':
                    default_defense_value = 1.0
                else:
                    default_defense_value = 0.0
                asset_json_entry['properties'][defense.name] = \
                    {
                        'type' : 'number',
                        'minimum' : 0,
                        'maximum' : 1,
                        'default': default_defense_value
                    }
            self.json_schema['definitions']['LanguageAsset']['definitions']\
                [asset.name] = asset_json_entry
            self.json_schema['definitions']['LanguageAsset']['oneOf'].append(
                {'$ref': '#/definitions/LanguageAsset/definitions/' + asset.name}
            )

    def _generate_associations(self) -> None:
        """
        Generate JSON Schema for the associations in the language specification.
        """
        def create_association_entry(assoc: Any):
            logger.debug(f'Creating {assoc.name} association JSON schema entry.')
            assoc_json_entry = {'title': assoc.name, 'type': 'object', 'properties': {}}

            create_association_field(assoc, assoc_json_entry, 'left')
            create_association_field(assoc, assoc_json_entry, 'right')
            return assoc_json_entry

        def create_association_with_subentries(assoc: Any):
            if (assoc.name not in self.json_schema['definitions']\
                ['LanguageAssociation']['definitions']):
                logger.info('Multiple associations with the same '\
                    f'name, {assoc.name}, exist. '\
                    'Creating subentries for each one.')
                self.json_schema['definitions']['LanguageAssociation']\
                ['definitions'][assoc.name] =\
                    {
                        'title': assoc.name,
                        'type': 'object',
                        'oneOf': [],
                        'definitions': {}
                    }
                self.json_schema['definitions']['LanguageAssociation']['oneOf'].\
                    append({'$ref': '#/definitions/LanguageAssociation/definitions/'
                    + assoc.name})

            assoc_json_subentry = create_association_entry(assoc)
            subentry_name = assoc.name + '_' + assoc.left_field.asset.name + '_' \
                + assoc.right_field.asset.name

            logger.info(f'Creating {subentry_name} subentry association.')
            assoc_json_subentry['title'] = subentry_name
            self.json_schema['definitions']['LanguageAssociation']\
                ['definitions'][assoc.name]['definitions'][subentry_name] = assoc_json_subentry
            self.json_schema['definitions']['LanguageAssociation']\
                ['definitions'][assoc.name]['oneOf'].append(
                    {'$ref': '#/definitions/LanguageAssociation/definitions/' \
                    + assoc.name + '/definitions/' + subentry_name})

        def create_association_field(
                assoc: Any,
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
                        '#/definitions/LanguageAsset/definitions/' +
                            field.asset.name
                        }
                }
            if field.maximum:
                assoc_json_entry['properties'][field.fieldname]\
                    ['maxItems'] = field.maximum


        for assoc in self.lang_graph.associations:
            count = len(list(filter(lambda temp_assoc: temp_assoc.name ==
                assoc.name, self.lang_graph.associations)))
            if count > 1:
                # If there are multiple associations with the same name we
                # will need to create separate entries for each using their
                # fieldnames.
                assoc_json_entry = create_association_with_subentries(assoc)
            else:
                assoc_json_entry = create_association_entry(assoc)
                self.json_schema['definitions']['LanguageAssociation']\
                    ['definitions'][assoc.name] = assoc_json_entry
                self.json_schema['definitions']['LanguageAssociation']['oneOf'].\
                    append({'$ref': '#/definitions/LanguageAssociation/' +
                    'definitions/' + assoc.name})

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
