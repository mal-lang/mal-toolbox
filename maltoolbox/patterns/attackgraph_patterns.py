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

    def is_last_pattern_in_chain(self):
        """Returns true if no more patterns to match after this"""
        return self.next_pattern is None


def find_in_graph(graph: AttackGraph, pattern: AttackGraphPattern):
    """Query a graph for a pattern of attributes"""

    # Find the starting nodes
    attribute = pattern.attributes[0]
    starting_nodes = graph.get_nodes_by_attribute_value(
         attribute[0], attribute[1]
    )

    matching_chains = []
    for node in starting_nodes:
        matching_chains += find_matches_recursively(
            node,
            pattern
        )
    return matching_chains


def find_matches_recursively(
        node: AttackGraphNode,
        pattern: AttackGraphPattern,
        current_chain=None,
        matching_chains=None,
        pattern_match_count=0
    ):
    """Follow a chain of attack graph nodes, check if they follow the pattern.
    When a sequence of patterns is fulfilled for a sequence of nodes,
    add the list of nodes to the returned `matching_chains`

    Args:
    node                - node to check if current `pattern` matches for
    pattern             - pattern to match against `node`
    matching_nodes      - list of matched nodes so far (builds up recursively)
    pattern_match_count  - the number of matches on current pattern so far

    Return: list of lists of AttackGraphNodes that match the pattern
    """

    # Init chain lists if None
    current_chain = [] if current_chain is None else current_chain
    matching_chains = [] if matching_chains is None else matching_chains


    if pattern.matches(node):
        # Current node matches, add to current_chain and increment match_count
        current_chain.append(node)
        pattern_match_count += 1

        if pattern.is_last_pattern_in_chain() and \
        not pattern.must_match_again(pattern_match_count):
            # This is the last pattern in the chain,
            #the current chain is matching
            matching_chains.append(current_chain)

        elif pattern.can_match_again(pattern_match_count):
            # Pattern has matches left, run recursively with current pattern
            for child in node.children:
                matching_chains = find_matches_recursively(
                    child,
                    pattern,
                    current_chain=current_chain,
                    matching_chains=matching_chains,
                    pattern_match_count=pattern_match_count
                )
        else:
            # Pattern has run out of matches, must move on to next pattern
            for child in node.children:
                matching_chains = find_matches_recursively(
                    child,
                    pattern.next_pattern,
                    current_chain=current_chain,
                    matching_chains=matching_chains
                )
    else:
        if not pattern.must_match_again(pattern_match_count)\
            and not pattern.is_last_pattern_in_chain():
            # Node did not match current pattern, but we can try with
            # the next pattern since current one is 'fulfilled'
            matching_chains = find_matches_recursively(
                node,
                pattern.next_pattern,
                current_chain=current_chain,
                matching_chains=matching_chains
            )

    return matching_chains
