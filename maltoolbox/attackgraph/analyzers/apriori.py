"""
MAL-Toolbox Attack Graph Apriori Analyzer Submodule

This submodule contains analyzers that are relevant before attackers are even
connected to the attack graph.
Currently these are:
- Viability = Determine if a node can be traversed under any circumstances or
  if the model structure makes it unviable.
- Necessity = Determine if a node is necessary for the attacker or if the
  model structure means it is not needed(it behaves as if it were already
  compromised) to compromise children attack steps.
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..attackgraph import AttackGraph
    from ..node import AttackGraphNode

logger = logging.getLogger(__name__)

def propagate_viability_from_node(node: AttackGraphNode) -> None:
    """
    Arguments:
    node        - the attack graph node from which to propagate the viable
                  status
    """
    logger.debug(
        'Propagate viability from "%s"(%d) with viability status %s.',
        node.full_name, node.id, node.is_viable
    )
    for child in node.children:
        original_value = child.is_viable
        if child.type == 'or':
            child.is_viable = False
            for parent in child.parents:
                child.is_viable = child.is_viable or parent.is_viable
        if child.type == 'and':
            child.is_viable = False

        if child.is_viable != original_value:
            propagate_viability_from_node(child)


def propagate_necessity_from_node(node: AttackGraphNode) -> None:
    """
    Arguments:
    node        - the attack graph node from which to propagate the necessary
                  status
    """
    logger.debug(
        'Propagate necessity from "%s"(%d) with necessity status %s.',
        node.full_name, node.id, node.is_necessary
    )

    for child in node.children:
        if child.ttc and child.ttc.get('name', None) not in ['Enabled',
                'Disabled', 'Instant']:
            # Do not propagate unnecessary state from nodes that have a TTC
            # probability distribution associated with them.
            # TODO: Evaluate this more carefully, how do we want to have TTCs
            # impact necessity and viability.
            # TODO: Have this condition be any probability that has a
            # Bernoulli component
            continue
        original_value = child.is_necessary
        if child.type == 'or':
            child.is_necessary = False
        if child.type == 'and':
            child.is_necessary = False
            for parent in child.parents:
                child.is_necessary = child.is_necessary or parent.is_necessary

        # TODO: Update TTC for child attack step before if it is not necessary
        # before propagating it further.
        if child.is_necessary != original_value:
            propagate_necessity_from_node(child)


def evaluate_viability(node: AttackGraphNode) -> None:
    """
    Arguments:
    graph       - the node to evaluate viability for.
    """
    match (node.type):
        case 'exist':
            assert isinstance(node.existence_status, bool), \
                f'Existence status not defined for {node.full_name}.'
            node.is_viable = node.existence_status
        case 'notExist':
            assert isinstance(node.existence_status, bool), \
                f'Existence status not defined for {node.full_name}.'
            node.is_viable = not node.existence_status
        case 'defense':
            assert node.defense_status is not None and \
                   0.0 <= node.defense_status <= 1.0, \
                f'{node.full_name} defense status invalid: {node.defense_status}.'
            node.is_viable = node.defense_status != 1.0
        case 'or':
            node.is_viable = False
            for parent in node.parents:
                node.is_viable = node.is_viable or parent.is_viable
        case 'and':
            node.is_viable = True
            for parent in node.parents:
                node.is_viable = node.is_viable and parent.is_viable
        case _:
            msg = ('Evaluate viability was provided node "%s"(%d) which '
                   'is of unknown type "%s"')
            logger.error(msg, node.full_name, node.id, node.type)
            raise ValueError(msg % (node.full_name, node.id, node.type))


def evaluate_necessity(node: AttackGraphNode) -> None:
    """
    Arguments:
    graph       - the node to evaluate necessity for.
    """
    match (node.type):
        case 'exist':
            assert isinstance(node.existence_status, bool), \
                f'Existence status not defined for {node.full_name}.'
            node.is_necessary = not node.existence_status
        case 'notExist':
            assert isinstance(node.existence_status, bool), \
                f'Existence status not defined for {node.full_name}.'
            node.is_necessary = bool(node.existence_status)
        case 'defense':
            assert node.defense_status is not None and \
                   0.0 <= node.defense_status <= 1.0, \
                f'{node.full_name} defense status invalid: {node.defense_status}.'
            node.is_necessary = node.defense_status != 0.0
        case 'or':
            node.is_necessary = True
            for parent in node.parents:
                node.is_necessary = node.is_necessary and parent.is_necessary
        case 'and':
            node.is_necessary = False
            for parent in node.parents:
                node.is_necessary = node.is_necessary or parent.is_necessary
        case _:
            msg = ('Evaluate necessity was provided node "%s"(%d) which '
                   'is of unknown type "%s"')
            logger.error(msg, node.full_name, node.id, node.type)
            raise ValueError(msg % (node.full_name, node.id, node.type))


def evaluate_viability_and_necessity(node: AttackGraphNode) -> None:
    """
    Arguments:
    graph       - the node to evaluate viability and necessity for.
    """
    evaluate_viability(node)
    evaluate_necessity(node)


def calculate_viability_and_necessity(graph: AttackGraph) -> None:
    """
    Arguments:
    graph       - the attack graph for which we wish to determine the
                  viability and necessity statuses for the nodes.
    """
    for node in graph.nodes.values():
        if node.type in ['exist', 'notExist', 'defense']:
            evaluate_viability_and_necessity(node)
            if not node.is_viable:
                propagate_viability_from_node(node)
            if not node.is_necessary:
                propagate_necessity_from_node(node)


def prune_unviable_and_unnecessary_nodes(graph: AttackGraph) -> None:
    """
    Arguments:
    graph       - the attack graph for which we wish to remove the
                  the nodes which are not viable or necessary.
    """
    logger.debug(
        'Prune unviable and unnecessary nodes from the attack graph.')

    nodes_to_remove = set()
    for node in graph.nodes.values():
        if node.type in ('or', 'and') and \
            (not node.is_viable or not node.is_necessary):
            nodes_to_remove.add(node)

    # Do the removal separatly so we don't remove
    # nodes from a set we are looping over
    for node in nodes_to_remove:
        graph.remove_node(node)


def propagate_viability_from_unviable_node(
        unviable_node: AttackGraphNode,
    ) -> set[AttackGraphNode]:
    """
    Update viability of nodes affected by newly enabled defense
    `unviable_node` in the graph and return any attack steps
    that are no longer viable because of it.

    Propagate recursively via children as long as changes occur.

    Arguments:
    unviable_node               - the node to propagate viability from

    Returns:
    attack_steps_made_unviable  - set of the attack steps that have been
                                  made unviable by a defense enabled in the
                                  current step. Builds up recursively.
    """

    attack_steps_made_unviable = set()

    logger.debug(
        'Update viability for node "%s"(%d)',
        unviable_node.full_name,
        unviable_node.id
    )

    assert not unviable_node.is_viable, (
        "propagate_viability_from_unviable_node should not be called"
       f" on viable node {unviable_node.full_name}"
    )

    if unviable_node.type in ('and', 'or'):
        attack_steps_made_unviable.add(unviable_node)

    for child in unviable_node.children:
        original_value = child.is_viable
        if child.type == 'or':
            child.is_viable = False
            for parent in child.parents:
                child.is_viable = child.is_viable or parent.is_viable
        if child.type == 'and':
            child.is_viable = False

        if child.is_viable != original_value:
            attack_steps_made_unviable |= \
                propagate_viability_from_unviable_node(child)

    return attack_steps_made_unviable
