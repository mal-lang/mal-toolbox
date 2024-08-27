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
            logger.error('Unknown node type %s.', node.type)
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


def calculate_reachability_for_attacker(attacker: Attacker) -> None:
    """Calculate the reachability for an attacker to all attack steps
    starting from the reached attack steps and propagating to descendants

    Args:
    attacker - the attacker to calculate reachability for
    """

    def attack_step_reachable_by(
            node_with_reachable_parent: AttackGraphNode,
            attacker: Attacker
        ) -> bool:
        """
        Decide if attack step node with at least one reachable parent
        is reachable by attacker based on its viability, type and parents
        """

        if not node_with_reachable_parent.is_viable:
            return False

        if node_with_reachable_parent.type == "or":
            # OR-Node is reachable if any parent is reachable
            return True
        if node_with_reachable_parent.type == "and":
            # Node is reachable only if all parents are reachable
            return all(
                parent.is_reachable_by(attacker)
                for parent in node_with_reachable_parent.parents
            )

        # Not an attack step -> Not reachable
        return False

    def propagate_reachable(
        reachable_node: AttackGraphNode, attacker: Attacker) -> None:
        """
        Mark node reachable for attacker and propagate to 
        reachable children recursively.
        """

        if attacker in reachable_node.reachable_by:
            # Already visited/calculated for attacker
            return

        reachable_node.reachable_by.add(attacker)
        attacker.reachable_attack_steps.add(reachable_node)

        for child in reachable_node.children:
            if attack_step_reachable_by(child, attacker):
                propagate_reachable(child, attacker)

    # All reached attack_steps are reachable,
    # propagate reachability to their children
    for reached_node in attacker.reached_attack_steps:
        propagate_reachable(reached_node, attacker)


def calculate_reachability(graph: AttackGraph) -> None:
    """Mark reachable nodes reachable by each attacker

    For each attacker, calculate which nodes they can reach and
    update values in node.reachable_by and attacker.reachable_attack_steps
    """

    for node in graph.nodes:
        # clear reachable_by for each node
        node.reachable_by.clear()

    for attacker in graph.attackers:
        # clear attacker reachable attack steps
        attacker.reachable_attack_steps.clear()
        calculate_reachability_for_attacker(attacker)


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
