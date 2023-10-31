"""
MAL-Toolbox Attack Graph Query Submodule

This submodule contains functions that analyze the information present in the
attack graph, but do not alter the structure or nodes in any way.
"""

import logging

from maltoolbox.attackgraph import attackgraph
from maltoolbox.attackgraph import attacker

logger = logging.getLogger(__name__)

def is_node_traversable_by_attacker(node, attacker) -> bool:
    """
    Return True or False depending if the node specified is traversable
    for the attacker given.

    Arguments:
    node        - the node we wish to evalute
    attacker    - the attacker whose traversability we are interested in
    """

    logger.debug(f'Evaluate if {node.id}, of type \'{node.type}\', is '\
        f'traversable by Attacker {attacker.id}')
    if not node.is_viable:
        return False

    match(node.type):
        case 'or':
            return True

        case 'and':
            for parent in node.parents:
                if parent not in attacker.reached_attack_steps and \
                     parent.is_necessary:
                    # If the parent is not present in the attacks steps
                    # already reached and is necessary.
                    return False
            return True

        case 'exist' | 'notExist' |  'defense':
            return False

        case _:
            logger.error(f'Unknown node type {node.type}.')
            return False

def get_attack_surface(graph: attackgraph.AttackGraph,
    attacker: attacker.Attacker):
    """
    Get the current attack surface of an attacker. This includes all of the
    viable children nodes of already reached attack steps that are of 'or'
    type and the 'and' type children nodes which have all of their necessary
    parents in the attack steps reached.

    Arguments:
    graph       - the attack graph
    attacker    - the Attacker whose attack surface is sought
    """
    logger.debug(f'Get the attack surface for Attacker {attacker.id}.')
    attack_surface = []
    for attack_step in attacker.reached_attack_steps:
        logger.debug('Determine attack surface stemming from '
            f'{attack_step.id} for Attacker {attacker.id}.')
        for child in attack_step.children:
            if is_node_traversable_by_attacker(child, attacker):
                attack_surface.append(child)
    return attack_surface

def get_defense_surface(graph: attackgraph.AttackGraph):
    """
    Get the defense surface. All non-suppressed defense steps that are not
    already fully enabled.

    Arguments:
    graph       - the attack graph
    """
    logger.debug(f'Get the defense surface.')
    return (node for node in graph.nodes if node.type == 'defense' and \
        'suppress' not in node.tags and \
        node.defense_status != 1.0)

def get_enabled_defenses(graph: attackgraph.AttackGraph):
    """
    Get the defenses already enabled. All non-suppressed defense steps that
    are already fully enabled.

    Arguments:
    graph       - the attack graph
    """
    logger.debug(f'Get the enabled defenses.')
    return (node for node in graph.nodes if node.type == 'defense' and \
        'suppress' not in node.tags and \
        node.defense_status == 1.0)

