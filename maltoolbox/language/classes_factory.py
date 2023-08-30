"""
MAL-Toolbox Language Classes Factory Module
"""

import python_jsonschema_objects as pjs
import json
import logging

logger = logging.getLogger(__name__)

class LanguageClassesFactory:
    def __init__(self, langspec):
        self.langspec = langspec
        self.json_schema = {}

    def generate_assets(self):
        """
        Generate JSON Schema for the assets in the language specification.
        """
        for asset in self.langspec['assets']:
            logger.debug(f'Creating {asset["name"]} asset JSON '\
            'schema entry.')
            asset_json_entry = {'title': asset['name'], 'type': 'object',
                'properties': {}}
            asset_json_entry['properties']['metaconcept'] = \
                {
                    'type' : 'string',
                    'default': asset['name']
                }
            if asset['superAsset']:
                asset_json_entry['allOf'] = [{
                    '$ref': '#/definitions/LanguageAsset/definitions/' + asset['superAsset']
                }]
            for defense in filter(lambda item: item['type'] == 'defense',
                asset['attackSteps']):
                if defense['ttc'] and defense['ttc']['name'] == 'Enabled':
                    default_defense_value = 1.0
                else:
                    default_defense_value = 0.0
                asset_json_entry['properties'][defense['name']] = \
                    {
                        'type' : 'number',
                        'minimum' : 0,
                        'maximum' : 1,
                        'default': default_defense_value
                    }
            self.json_schema['definitions']['LanguageAsset']['definitions']\
                [asset['name']] = asset_json_entry
            self.json_schema['definitions']['LanguageAsset']['oneOf'].\
                append({'$ref': '#/definitions/LanguageAsset/definitions/'
                + asset['name']})

    def generate_associations(self):
        """
        Generate JSON Schema for the associations in the language specification.
        """
        def create_association_entry(assoc):
            logger.debug(f'Creating {assoc["name"]} association JSON '\
            'schema entry.')
            assoc_json_entry = {'title': assoc['name'], 'type': 'object',
                'properties': {}}

            create_association_field(assoc, assoc_json_entry, 'left')
            create_association_field(assoc, assoc_json_entry, 'right')
            return assoc_json_entry

        def create_association_with_subentries(assoc):
            if (assoc['name'] not in self.json_schema['definitions']\
                ['LanguageAssociation']['definitions']):
                logger.info('Multiple associations with the same '\
                    f'name, {assoc["name"]}, exist. '\
                    'Creating subentries for each one.')
                self.json_schema['definitions']['LanguageAssociation']\
                ['definitions'][assoc['name']] =\
                    {
                        'title': assoc['name'],
                        'type': 'object',
                        'oneOf': [],
                        'definitions': {}
                    }
                self.json_schema['definitions']['LanguageAssociation']['oneOf'].\
                    append({'$ref': '#/definitions/LanguageAssociation/definitions/'
                    + assoc['name']})

            assoc_json_subentry = create_association_entry(assoc)
            subentry_name = assoc['name'] + '_' + assoc['leftAsset'] + '_' \
                + assoc['rightAsset']

            logger.info(f'Creating {subentry_name} subentry association.')
            assoc_json_subentry['title'] = subentry_name
            self.json_schema['definitions']['LanguageAssociation']\
                ['definitions'][assoc['name']]['definitions'][subentry_name] = assoc_json_subentry
            self.json_schema['definitions']['LanguageAssociation']\
                ['definitions'][assoc['name']]['oneOf'].append(
                    {'$ref': '#/definitions/LanguageAssociation/definitions/' \
                    + assoc['name'] + '/definitions/' + subentry_name})

        def create_association_field(assoc, assoc_json_entry, position):
            assoc_json_entry['properties'][assoc[position + 'Field']] = \
                {
                    'type' : 'array',
                    'items' :
                        {
                        '$ref':
                        '#/definitions/LanguageAsset/definitions/' +
                            assoc[position + 'Asset']
                        }
                }
            if assoc[position + 'Multiplicity']['max']:
                assoc_json_entry['properties'][assoc[position + 'Field']]\
                    ['maxItems'] = assoc[position + 'Multiplicity']['max']


        for assoc in self.langspec['associations']:
            count = len(list(filter(lambda temp_assoc: temp_assoc['name'] ==
                assoc['name'], self.langspec['associations'])))
            if count > 1:
                # If there are multiple associations with the same name we
                # will need to create separate entries for each using their
                # fieldnames.
                assoc_json_entry = create_association_with_subentries(assoc)
            else:
                assoc_json_entry = create_association_entry(assoc)
                self.json_schema['definitions']['LanguageAssociation']\
                    ['definitions'][assoc['name']] = assoc_json_entry
                self.json_schema['definitions']['LanguageAssociation']['oneOf'].\
                    append({'$ref': '#/definitions/LanguageAssociation/' +
                    'definitions/' + assoc['name']})

    def create_classes(self):
        """
        Create classes based on the language specification.
        """

        # First, we have to translate the language specification into a JSON
        # schema. Initialize the overall JSON schema structure.
        self.json_schema = {
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

        self.generate_assets()
        self.generate_associations()
        logger.debug(json.dumps(self.json_schema, indent = 2))

        # Once we have the JSON schema we create the actual classes.
        builder = pjs.ObjectBuilder(self.json_schema)
        self.ns = builder.build_classes(standardize_names=False)
