"""Functions for searching for patterns in the AttackGraph"""

from __future__ import annotations
from dataclasses import dataclass
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode


@dataclass
class AttackGraphPattern:
    """A pattern to search for in a graph"""
    attributes: dict
    next_pattern: AttackGraphPattern | None = None
    min_repeated: int = 1
    max_repeated: int = 1


def find_in_graph(graph: AttackGraph, pattern: AttackGraphPattern):
    """Query a graph for a pattern of attributes"""

    # Find the starting nodes
    attribute = pattern.attributes[0]
    starting_nodes = graph.get_nodes_by_attribute_value(
         attribute[0], attribute[1]
    )

    matching_chains = []
    for node in starting_nodes:
        matching_chains += find_recursively(
            node,
            pattern
        )
    return matching_chains


def find_recursively(
        node: AttackGraphNode,
        pattern: AttackGraphPattern,
        current_chain=None,
        matching_chains=None,
        pattern_match_count=0
    ):
    """Follow a chain of attack graph nodes, check if they follow the pattern
    and if they do, add them to the returned list of matching nodes

    Args:
    node                - node to check if current `pattern` matches for
    pattern             - pattern to match against `node`
    matching_nodes      - list of matched nodes so far (builds up recursively)
    pattern_match_count  - the number of matches on current pattern so far

    Return: list of AttackGraphNodes that match the pattern
    """

    # Init chain lists if None
    current_chain = [] if current_chain is None else current_chain
    matching_chains = [] if matching_chains is None else matching_chains

    # See if current node matches pattern
    node_matches_pattern = True
    for attr, value in pattern.attributes:
        if getattr(node, attr) != value:
            node_matches_pattern = False
            break

    if node_matches_pattern:
        # Current node matches, add to current_chain and increment match_count
        current_chain.append(node)
        pattern_match_count += 1

    # See if current pattern is fulfilled
    pattern_fulfilled = pattern_match_count >= pattern.min_repeated
    pattern_can_be_used_again = pattern_match_count < pattern.max_repeated

    if pattern_fulfilled and pattern.next_pattern is None:
        # This is the last pattern in the chain
        # If it is fulfilled the current chain is done
        matching_chains.append(current_chain)

    elif node_matches_pattern and pattern_can_be_used_again:
        # Pattern has matches left
        for child in node.children:
            matching_chains = find_recursively(
                child,
                pattern,
                current_chain=current_chain,
                matching_chains=matching_chains,
                pattern_match_count=pattern_match_count
            )

    elif node_matches_pattern and not pattern_can_be_used_again:
        # Pattern has run out of matches, must move to next pattern
        for child in node.children:
            matching_chains = find_recursively(
                child,
                pattern.next_pattern,
                current_chain=current_chain,
                matching_chains=matching_chains
            )

    elif not node_matches_pattern and pattern_fulfilled:
        # Node did not match current pattern, but we can try with
        # the next pattern since current one is fulfilled
        matching_chains = find_recursively(
            node,
            pattern.next_pattern,
            current_chain=current_chain,
            matching_chains=matching_chains
        )

    return matching_chains
