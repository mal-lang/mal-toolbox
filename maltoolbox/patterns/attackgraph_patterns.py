"""Functions for searching for patterns in the AttackGraph"""

from __future__ import annotations
from dataclasses import dataclass
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode


@dataclass
class AttackGraphPattern:
    """A pattern to search for in a graph"""
    attributes: dict
    min_repeated: int = 1
    max_repeated: int = 1

    def matches(self, node: AttackGraphNode):
        """Returns true if pattern matches node"""
        matches_pattern = True
        for attr, value in self.attributes:
            if getattr(node, attr) != value:
                matches_pattern = False
                break
        return matches_pattern

    def can_match_again(self, num_matches):
        """Returns true if pattern can be used again"""
        return num_matches < self.max_repeated

    def must_match_again(self, num_matches):
        """Returns true if pattern must match again to be fulfilled"""
        return num_matches < self.min_repeated


def find_in_graph(graph: AttackGraph, patterns: list[AttackGraphPattern]):
    """Query a graph for a pattern of attributes"""

    # Find the starting nodes
    attribute = patterns[0].attributes[0]
    starting_nodes = graph.get_nodes_by_attribute_value(
         attribute[0], attribute[1]
    )
    matching_chains = []
    for node in starting_nodes:
        matching_chains += find_matches_recursively(node, patterns)

    return matching_chains


def find_matches_recursively(
        node: AttackGraphNode,
        pattern_list: list[AttackGraphPattern],
        current_chain=None,
        matching_chains=None,
        pattern_match_count=0
    ):
    """Follow a chain of attack graph nodes, check if they follow the pattern.
    When a sequence of patterns is fulfilled for a sequence of nodes,
    add the list of nodes to the returned `matching_chains`

    Args:
    node                - node to check if current `pattern` matches for
    pattern_list        - will attempt to match first pattern against `node`
    matching_nodes      - list of matched nodes so far (builds up recursively)
    pattern_match_count - the number of matches on current pattern so far

    Return: list of lists of AttackGraphNodes that match the pattern
    """
    # Init chain lists if None
    current_chain = [] if current_chain is None else current_chain
    matching_chains = [] if matching_chains is None else matching_chains

    current_pattern = pattern_list[0]

    if current_pattern.matches(node):
        # Current node matches, add to current_chain and increment match_count
        current_chain.append(node)
        pattern_match_count += 1

        if len(pattern_list) == 1 \
            and not current_pattern.must_match_again(pattern_match_count):
            # This is the last pattern in the chain,
            # and the current chain is matching
            matching_chains.append(current_chain)

        elif current_pattern.can_match_again(pattern_match_count):
            # Pattern has matches left, run recursively with current pattern
            for child in node.children:
                matching_chains = find_matches_recursively(
                    child,
                    pattern_list,
                    current_chain=current_chain,
                    matching_chains=matching_chains,
                    pattern_match_count=pattern_match_count
                )
        else:
            # Pattern has run out of matches, must move on to next pattern
            for child in node.children:
                matching_chains = find_matches_recursively(
                    child,
                    pattern_list[1:],
                    current_chain=current_chain,
                    matching_chains=matching_chains
                )
    else:
        if not current_pattern.must_match_again(pattern_match_count)\
            and len(pattern_list) > 1:
            # Node did not match current pattern, but we can try with
            # the next pattern since current one is 'fulfilled'
            matching_chains = find_matches_recursively(
                node,
                pattern_list[1:],
                current_chain=current_chain,
                matching_chains=matching_chains
            )

    return matching_chains
