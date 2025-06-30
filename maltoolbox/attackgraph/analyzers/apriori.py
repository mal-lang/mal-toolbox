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

def propagate_viability_from_node(node: AttackGraphNode) -> set[AttackGraphNode]:
    """
    Update viability of children of node givein as parameter. Propagate
    recursively via children as long as changes occur. Return all nodes which
    have changed viability.

    Arguments:
    node            - the attack graph node from which to propagate the
                      viability status

    Returns:
    changed_nodes   - set of nodes that have changed viability
    """
    logger.debug(
        'Propagate viability from "%s"(%d) with viability status %s.',
        node.full_name, node.id, node.is_viable
    )
    changed_nodes = set()
    for child in node.children:
        original_value = child.is_viable
        if child.type == 'or':
            child.is_viable = any(
                parent.is_viable for parent in child.parents)

        elif child.type == 'and':
            child.is_viable = all(
                parent.is_viable for parent in child.parents)

        if child.is_viable != original_value:
            changed_nodes |= ({child} |
                propagate_viability_from_node(child))

    return changed_nodes


def propagate_necessity_from_node(node: AttackGraphNode) -> set[AttackGraphNode]:
    """
    Update necessity of children of node givein as parameter. Propagate
    recursively via children as long as changes occur. Return all nodes which
    have changed necessity.

    Arguments:
    node            - the attack graph node from which to propagate the
                      necessity status

    Returns:
    changed_nodes   - set of nodes that have changed necessity
    """
    logger.debug(
        'Propagate necessity from "%s"(%d) with necessity status %s.',
        node.full_name, node.id, node.is_necessary
    )
    changed_nodes = set()
    for child in node.children:
        original_value = child.is_necessary
        if child.type == 'or':
            child.is_necessary = all(
                parent.is_necessary for parent in child.parents)

        elif child.type == 'and':
            child.is_necessary = any(
                parent.is_necessary for parent in child.parents)

        if child.is_necessary != original_value:
            changed_nodes |= ({child} |
                propagate_necessity_from_node(child))

    return changed_nodes


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


def calculate_viability_and_necessity(graph: AttackGraph) -> None:
    """
    Arguments:
    graph       - the attack graph for which we wish to determine the
                  viability and necessity statuses for the nodes.
    """
    for node in graph.nodes.values():
        if node.type in ['exist', 'notExist', 'defense']:
            evaluate_viability(node)
            propagate_viability_from_node(node)
            evaluate_necessity(node)
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

