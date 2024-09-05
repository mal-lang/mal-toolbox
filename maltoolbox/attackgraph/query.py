"""
MAL-Toolbox Attack Graph Query Submodule

This submodule contains functions that analyze the information present in the
attack graph, but do not alter the structure or nodes in any way.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from .attackgraph import AttackGraph, Attacker

if TYPE_CHECKING:
    from .attackgraph import AttackGraphNode

logger = logging.getLogger(__name__)

def is_node_traversable_by_attacker(
        node: AttackGraphNode, attacker: Attacker
    ) -> bool:
    """
    Return True or False depending if the node specified is traversable
    for the attacker given.

    Arguments:
    node        - the node we wish to evalute
    attacker    - the attacker whose traversability we are interested in
    """

    logger.debug(
        'Evaluate if "%s"(%d), of type "%s", is traversable by Attacker '
            '"%s"(%d)',
        node.full_name,
        node.id,
        node.type,
        attacker.name,
        attacker.id
    )
    if not node.is_viable:
        logger.debug(
            '"%s"(%d) is not traversable because it is non-viable',
            node.full_name,
            node.id,
        )
        return False

    match(node.type):
        case 'or':
            logger.debug(
                '"%s"(%d) is traversable because it is viable and '
                'of type "or".',
                node.full_name,
                node.id
            )
            return True

        case 'and':
            for parent in node.parents:
                if parent.is_necessary and \
                    not parent.is_compromised_by(attacker):
                    # If the parent is not present in the attacks steps
                    # already reached and is necessary.
                    logger.debug(
                        '"%s"(%d) is not traversable because while it is '
                        'viable, and of type "and", its necessary parent '
                        '"%s(%d)" has not already been compromised.',
                        node.full_name,
                        node.id,
                        parent.full_name,
                        parent.id
                    )
                    return False
            logger.debug(
                '"%s"(%d) is traversable because it is viable, '
                'of type "and", and all of its necessary parents have '
                'already been compromised.',
                node.full_name,
                node.id
            )
            return True

        case 'exist' | 'notExist' | 'defense':
            logger.warning(
                'Nodes of type "exist", "notExist", and "defense" are never '
                'marked as traversable. However, we do not normally check '
                'if they are traversable. Node "%s"(%d) of type "%s" was '
                'checked for traversability.',
                node.full_name,
                node.id,
                node.type
            )
            return False

        case _:
            logger.error(
                'Node "%s"(%d) has an unknown type "%s".',
                node.full_name,
                node.id,
                node.type
            )
            return False

def get_attack_surface(
        attacker: Attacker
    ) -> list[AttackGraphNode]:
    """
    Get the current attack surface of an attacker. This includes all of the
    viable children nodes of already reached attack steps that are of 'or'
    type and the 'and' type children nodes which have all of their necessary
    parents in the attack steps reached.

    Arguments:
    attacker    - the Attacker whose attack surface is sought
    """
    logger.debug(
        'Get the attack surface for Attacker "%s"(%d).',
        attacker.name,
        attacker.id
    )
    attack_surface = []
    for attack_step in attacker.reached_attack_steps:
        logger.debug(
            'Determine attack surface stemming from '
            '"%s"(%d) for Attacker "%s"(%d).',
            attack_step.full_name,
            attack_step.id,
            attacker.name,
            attacker.id
        )
        for child in attack_step.children:
            if is_node_traversable_by_attacker(child, attacker) and \
                    child not in attack_surface:
                attack_surface.append(child)
    return attack_surface

def update_attack_surface_add_nodes(
        attacker: Attacker,
        current_attack_surface: list[AttackGraphNode],
        nodes: list[AttackGraphNode]
    ) -> list[AttackGraphNode]:
    """
    Update the attack surface of an attacker with the new attack step nodes
    provided to see if any of their children can be added.

    Arguments:
    attacker                - the Attacker whose attack surface is sought
    current_attack_surface  - the current attack surface that we wish to
                              expand
    nodes                   - the newly compromised attack step nodes that we
                              wish to see if any of their children should be
                              added to the attack surface
    """
    logger.debug('Update the attack surface for Attacker "%s"(%d).',
        attacker.name,
        attacker.id)
    attack_surface = current_attack_surface
    for attack_step in nodes:
        logger.debug(
            'Determine attack surface stemming from "%s"(%d) '
            'for Attacker "%s"(%d).',
            attack_step.full_name,
            attack_step.id,
            attacker.name,
            attacker.id
        )
        for child in attack_step.children:
            is_traversable = is_node_traversable_by_attacker(child, attacker)
            if is_traversable and child not in attack_surface:
                logger.debug(
                    'Add node "%s"(%d) to the attack surface of '
                    'Attacker "%s"(%d).',
                    child.full_name,
                    child.id,
                    attacker.name,
                    attacker.id
                )
                attack_surface.append(child)
    return attack_surface

def get_defense_surface(graph: AttackGraph) -> list[AttackGraphNode]:
    """
    Get the defense surface. All non-suppressed defense steps that are not
    already fully enabled.

    Arguments:
    graph       - the attack graph
    """
    logger.debug('Get the defense surface.')
    return [node for node in graph.nodes if node.is_available_defense()]

def get_enabled_defenses(graph: AttackGraph) -> list[AttackGraphNode]:
    """
    Get the defenses already enabled. All non-suppressed defense steps that
    are already fully enabled.

    Arguments:
    graph       - the attack graph
    """
    logger.debug('Get the enabled defenses.')
    return [node for node in graph.nodes if node.is_enabled_defense()]
