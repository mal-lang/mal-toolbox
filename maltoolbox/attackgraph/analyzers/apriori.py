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

import logging

from maltoolbox.attackgraph import attackgraph
from maltoolbox.attackgraph import attacker
from maltoolbox.attackgraph import node

logger = logging.getLogger(__name__)

def propagate_viability_from_node(node: node.AttackGraphNode):
    """
    Arguments:
    node        - the attack graph node from which to propagate the viable
                  status
    """
    logger.debug(f'Propagate viability from {node.id} with viability'
        f' status {node.is_viable}.')
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

def propagate_necessity_from_node(node: node.AttackGraphNode):
    """
    Arguments:
    node        - the attack graph node from which to propagate the necessary
                  status
    """
    logger.debug(f'Propagate necessity from {node.id} with necessity'
        f' status {node.is_necessary}.')
    for child in node.children:
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

def calculate_viability_and_necessity(graph: attackgraph.AttackGraph):
    """
    Arguments:
    node        - the attack graph for which we wish to determine the
                  viability and necessity statuses for the nodes.
    """
    for node in graph.nodes:
        match (node.type):
            case 'exist':
                node.is_viable = node.existence_status
                node.is_necessary = not node.existence_status
            case 'notExist':
                node.is_viable = not node.existence_status
                node.is_necessary = node.existence_status
            case 'defense':
                node.is_viable = node.defense_status != 1.0
                node.is_necessary = node.defense_status != 0.0
            case _:
                pass

        if not node.is_viable:
            propagate_viability_from_node(node)
        if not node.is_necessary:
            propagate_necessity_from_node(node)
