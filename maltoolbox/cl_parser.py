"""
MAL-Toolbox Command Line Parsing Module
"""

import sys
import argparse
import logging
from typing import Sequence

from maltoolbox import __version__

logger = logging.getLogger(__name__)

def parse_args(args: Sequence[str]) -> argparse.Namespace:
    """
    This function parses the arguments which have been passed from the command
    line. It returns an argparse parser object.

    Arguments:
    args - the list of arguments passed from the command line in the sys.argv
           format

    Return:
    A parser with the provided arguments, which can be used in a simpler format
    """
    parser = argparse.ArgumentParser(
        prog='maltoolbox',
        description='Generate Attack Graphs from MAL specifications')

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}')

    subparsers = parser.add_subparsers(help='commands', dest='command')
    subparsers.required = True

    gen_ag_parser = subparsers.add_parser(
        'gen_ag',
        help='Generate an attack graph from an instance model from a json ' \
            'file and language specification from a mar archive.')
    help_parser = subparsers.add_parser(
        'help', help='Show help for a particular command')

    gen_ag_parser.add_argument(
        'model',
        help='Path to the instance model json file',
        type=str,
    )

    gen_ag_parser.add_argument(
        'language',
        help='Path to the language specification ".mar" archive',
        type=str,
    )

    gen_ag_parser.add_argument(
        '--neo4j',
        help='Injest attack graph and instance model into a local Neo4j ' \
            'instance',
        action='store_true'
    )

    help_parser.add_argument(
        'cmd',
        help='Name of command to get help for',
        nargs='?')

    if len(args) == 0:
        parser.print_help(sys.stderr)
        logger.error('Received no arugments will print help and exit.')
        sys.exit(1)

    parsed_args = parser.parse_args()
    if parsed_args.command == 'help':
        if not parsed_args.cmd:
            parser.print_help(sys.stderr)
        else:
            try:
                subparsers.choices[parsed_args.cmd].print_help()
            except KeyError:
                logger.error(f'Unknown command name {parsed_args.cmd}')
                print(f'Unknown command name {parsed_args.cmd}')
                print(
                    f'Valid commands are: {", ".join(subparsers.choices.keys())}')

        sys.exit(1)

    return parsed_args
