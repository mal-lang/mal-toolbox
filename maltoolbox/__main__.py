"""
MAL-Toolbox Main Module
"""

import sys

import logging
import json

from . import cl_parser, log_configs, neo4j_configs
from .language import LanguageClassesFactory, specification
from .model import Model
from .attackgraph import AttackGraph
from .attackgraph.analyzers.apriori import *
from .ingestors import neo4j
from .exceptions import AttackGraphStepExpressionError

logger = logging.getLogger(__name__)

args = cl_parser.parse_args(sys.argv[1:])
cmd_params = vars(args)
logger.info('Received the following command line parameters:\n' +
    json.dumps(cmd_params, indent = 2))

match(cmd_params['command']):
    case 'gen_ag':
        model_filename = cmd_params['model']
        langspec_filename = cmd_params['language']

        # Load language specification and generate classes based on it.
        lang_spec = specification. \
            load_language_specification_from_mar(langspec_filename)
        if log_configs['langspec_file']:
            specification.save_language_specification_to_json(lang_spec,
                log_configs['langspec_file'])
        lang_classes_factory = LanguageClassesFactory(lang_spec)
        lang_classes_factory.create_classes()

        # Load instance model.
        instance_model = Model('Test model', lang_spec,
            lang_classes_factory)
        instance_model.load_from_file(model_filename)
        if log_configs['model_file']:
            instance_model.save_to_file( \
                log_configs['model_file'])

        try:
            graph = AttackGraph(lang_spec, instance_model)
        except AttackGraphStepExpressionError:
            logger.error('Attack graph generation failed when attempting ' \
                'to resolve attack step expression!')
            sys.exit(1)

        calculate_viability_and_necessity(graph)

        graph.attach_attackers(instance_model)

        if log_configs['attackgraph_file']:
            graph.save_to_file(
                log_configs['attackgraph_file'])

        if cmd_params['neo4j']:
            # Injest instance model and attack graph into Neo4J.
            logger.debug('Ingest model graph into Neo4J database.')
            neo4j.ingest_model(instance_model,
                neo4j_configs['uri'],
                neo4j_configs['username'],
                neo4j_configs['password'],
                neo4j_configs['dbname'],
                delete=True)
            logger.debug('Ingest attack graph into Neo4J database.')
            neo4j.ingest_attack_graph(graph,
                neo4j_configs['uri'],
                neo4j_configs['username'],
                neo4j_configs['password'],
                neo4j_configs['dbname'],
                delete=False)

    case _:
        logger.error(f'Received unknown command: {cmd_params["command"]}.')
        sys.exit(1)
