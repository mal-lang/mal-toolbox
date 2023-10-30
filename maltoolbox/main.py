"""
MAL-Toolbox Main Module
"""

import sys

import logging
import json

import maltoolbox
import maltoolbox.cl_parser
from maltoolbox.language import classes_factory
from maltoolbox.language import specification
from maltoolbox.model import model
from maltoolbox.attackgraph import attackgraph
from maltoolbox.attackgraph.analyzers import apriori
from maltoolbox.ingestors import neo4j

logger = logging.getLogger(__name__)

def main():
    """Main routine of maltoolbox command line interface."""
    args = maltoolbox.cl_parser.parse_args(sys.argv[1:])
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
            if maltoolbox.log_configs['langspec_file']:
                specification.save_language_specification_to_json(lang_spec,
                    maltoolbox.log_configs['langspec_file'])
            lang_classes_factory = \
                classes_factory.LanguageClassesFactory(lang_spec)
            lang_classes_factory.create_classes()

            # Load instance model.
            instance_model = model.Model('Test model', lang_spec,
                lang_classes_factory)
            instance_model.load_from_file(model_filename)
            if maltoolbox.log_configs['model_file']:
                instance_model.save_to_file( \
                    maltoolbox.log_configs['model_file'])

            graph = attackgraph.AttackGraph()
            result = graph.generate_graph(lang_spec, instance_model)
            if result > 0:
                logger.error('Attack graph generation failed!')
                print('Attack graph generation failed!')
                exit(result)

            apriori.calculate_viability_and_necessity(graph)

            graph.attach_attackers(instance_model)

            if maltoolbox.log_configs['attackgraph_file']:
                graph.save_to_file(
                    maltoolbox.log_configs['attackgraph_file'])

            if cmd_params['neo4j']:
                # Injest instance model and attack graph into Neo4J.
                logger.debug('Ingest model graph into Neo4J database.')
                neo4j.ingest_model(instance_model,
                    maltoolbox.neo4j_configs['uri'],
                    maltoolbox.neo4j_configs['username'],
                    maltoolbox.neo4j_configs['password'],
                    maltoolbox.neo4j_configs['dbname'],
                    delete=True)
                logger.debug('Ingest attack graph into Neo4J database.')
                neo4j.ingest_attack_graph(graph,
                    maltoolbox.neo4j_configs['uri'],
                    maltoolbox.neo4j_configs['username'],
                    maltoolbox.neo4j_configs['password'],
                    maltoolbox.neo4j_configs['dbname'],
                    delete=False)

        case _:
            logger.error(f'Received unknown command: {cmd_params["command"]}.')
