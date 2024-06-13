"""
Command-line interface for MAL toolbox operations

Usage:
    maltoolbox attack-graph generate [options] <model> <lang_file>
    maltoolbox compile <lang_file> <output_file>

Arguments:
    <model>         Path to JSON instance model file.
    <lang_file>     Path to .mar or .mal file containing MAL spec.
    <output_file>   Path to write the JSON result of the compilation.

Options:
    --neo4j         Ingest attack graph and instance model into a Neo4j instance

Notes:
    - <lang_file> can be either a .mar file (generated by the older MAL
      compiler) or a .mal file containing the DSL written in MAL.

    - If --neo4j is used, the Neo4j instance should be running. The connection
      parameters required for this app to reach the Neo4j instance should be
      defined in the default.conf file.
"""

import logging
import json
import docopt

from maltoolbox.wrappers import create_attack_graph
from . import log_configs, neo4j_configs
from .language.compiler import MalCompiler # type: ignore
from .ingestors import neo4j

logger = logging.getLogger(__name__)

def generate_attack_graph(
        model_file: str,
        lang_file: str,
        send_to_neo4j: bool
    ) -> None:
    """Create an attack graph and optionally send to neo4j
    
    Args:
    model_file      - path to the model file
    lang_file       - path to the language file
    send_to_neo4j   - whether to ingest into neo4j or not
    """
    attack_graph = create_attack_graph(lang_file, model_file)
    if log_configs['attackgraph_file']:
        attack_graph.save_to_file(
            log_configs['attackgraph_file']
        )

    if send_to_neo4j:
        logger.debug('Ingest model graph into Neo4J database.')
        neo4j.ingest_model(attack_graph.model,
            neo4j_configs['uri'],
            neo4j_configs['username'],
            neo4j_configs['password'],
            neo4j_configs['dbname'],
            delete=True)
        logger.debug('Ingest attack graph into Neo4J database.')
        neo4j.ingest_attack_graph(attack_graph,
            neo4j_configs['uri'],
            neo4j_configs['username'],
            neo4j_configs['password'],
            neo4j_configs['dbname'],
            delete=False)


def compile(lang_file: str, output_file: str) -> None:
    """Compile language and dump into output file"""
    compiler = MalCompiler()
    with open(output_file, "w") as f:
        json.dump(compiler.compile(lang_file), f, indent=2)


args = docopt.docopt(__doc__)

if args['attack-graph'] and args['generate']:
    generate_attack_graph(args['<model>'], args['<lang_file>'], args['--neo4j'])
elif args['compile']:
    compile(args['<lang_file>'], args['<output_file>'])
