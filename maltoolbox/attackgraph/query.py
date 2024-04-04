"""
MAL-Toolbox Attack Graph Query Submodule

This submodule contains functions that analyze the information present in the
attack graph, but do not alter the structure or nodes in any way.
"""

import logging

from .attackgraph import AttackGraph
from .attacker import Attacker

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
                if parent.is_necessary and \
                    not parent.is_compromised_by(attacker):
                    # If the parent is not present in the attacks steps
                    # already reached and is necessary.
                    return False
            return True

        case 'exist' | 'notExist' |  'defense':
            return False

        case _:
            logger.error(f'Unknown node type {node.type}.')
            return False

def get_attack_surface(graph: AttackGraph,
    attacker: Attacker):
    """
    Get the current attack surface of an attacker. This includes all of the
    viable children nodes of already reached attack steps that are of 'or'
    type and the 'and' type children nodes which have all of their necessary
    parents in the attack steps reached.

    Arguments:
    graph       - the attack graph
    attacker    - the Attacker whose attack surface is sought
    """
    logger.debug(f'Get the attack surface for Attacker \"{attacker.id}\".')
    attack_surface = []
    for attack_step in attacker.reached_attack_steps:
        logger.debug('Determine attack surface stemming from '
            f'\"{attack_step.id}\" for Attacker \"{attacker.id}\".')
        for child in attack_step.children:
            if is_node_traversable_by_attacker(child, attacker) and \
                    child not in attack_surface:
                attack_surface.append(child)
    return attack_surface

def update_attack_surface_add_nodes(
    graph: AttackGraph,
    attacker: Attacker,
    current_attack_surface,
    nodes):
    """
    Update the attack surface of an attacker with the new attack step nodes
    provided to see if any of their children can be added.

    Arguments:
    graph                   - the attack graph
    attacker                - the Attacker whose attack surface is sought
    current_attack_surface  - the current attack surface that we wish to
                              expand
    nodes                   - the newly compromised attack step nodes that we
                              wish to see if any of their children should be
                              added to the attack surface
    """
    logger.debug(f'Update the attack surface for Attacker \"{attacker.id}\".')
    attack_surface = current_attack_surface
    for attack_step in nodes:
        logger.debug('Determine attack surface stemming from '
            f'\"{attack_step.id}\" for Attacker \"{attacker.id}\".')
        for child in attack_step.children:
            is_traversable = is_node_traversable_by_attacker(child, attacker)
            if is_traversable and child not in attack_surface:
                attack_surface.append(child)
    return attack_surface

def update_attack_surface_remove_nodes(
    graph: AttackGraph,
    attacker: Attacker,
    current_attack_surface,
    nodes):
    """
    Update the attack surface of an attacker to see if any of the descendants
    of the nodes provided should be removed from it.

    Arguments:
    graph                   - the attack graph
    attacker                - the Attacker whose attack surface is sought
    current_attack_surface  - the current attack surface that we wish to
                              restrict
    nodes                   - the nodes that we wish to see if any of their
                              descendants should be removed from the attack
                              surface
    """
    logger.debug(f'Update the attack surface for Attacker \"{attacker.id}\".')
    attack_surface = current_attack_surface
    for step in nodes:
        logger.debug('Determine for potential removal attack surface '
            f'stemming from \"{step.id}\" for Attacker \"{attacker.id}\".')
        for child in step.children:
            is_traversable = is_node_traversable_by_attacker(child, attacker)
            if not is_traversable and child in attack_surface:
                attack_surface.remove(child)
                attack_surface = update_attack_surface_remove_nodes(
                    graph,
                    attacker,
                    attack_surface,
                    [child]
                )
    return attack_surface

def get_defense_surface(graph: AttackGraph):
    """
    Get the defense surface. All non-suppressed defense steps that are not
    already fully enabled.

    Arguments:
    graph       - the attack graph
    """
    logger.debug(f'Get the defense surface.')
    return [node for node in graph.nodes if node.is_available_defense()]

def get_enabled_defenses(graph: AttackGraph):
    """
    Get the defenses already enabled. All non-suppressed defense steps that
    are already fully enabled.

    Arguments:
    graph       - the attack graph
    """
    logger.debug(f'Get the enabled defenses.')
    return [node for node in graph.nodes if node.is_enabled_defense()]

