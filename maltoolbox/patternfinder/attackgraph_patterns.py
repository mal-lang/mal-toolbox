"""Utilities for finding patterns in the AttackGraph"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode

class SearchPattern:
    """A pattern consists of conditions, the conditions are used
    to find all matching sequences of nodes in an AttackGraph."""
    conditions: list[SearchCondition]

    def __init__(self, conditions):
        self.conditions = conditions

    def find_matches(self, graph: AttackGraph):
        """Search through a graph for a pattern using
        its conditions, and return sequences of nodes
        that match all the conditions in the pattern

        Args:
        graph   - The AttackGraph to search in
    
        Return: list[list[AttackGraphNode]] matching paths of Nodes
        """

        # Find the starting nodes which match the first condition
        condition = self.conditions[0]
        matching_paths = []
        for node in graph.nodes.values():
            if condition.matches(node):
                matching_paths.extend(
                    find_matches_recursively(node, self.conditions)
                )
        return matching_paths

@dataclass
class SearchCondition:
    """A condition that has to be true for a node to match"""

    # Predefined search conditions
    ANY = lambda _: True

    # `matches` should be a lambda that takes node as input and returns bool
    # If lamdba returns True for a node, the node matches
    # If the lamdba returns False for a node, the node does not match
    matches: Callable[[AttackGraphNode], bool]
    greedy: bool = False

    # It is possible to require/allow a Condition to repeat
    min_repeated: int = 1
    max_repeated: int = 1

    def can_match_again(self, num_matches):
        """Returns true if condition can be used again"""
        return num_matches < self.max_repeated

    def must_match_again(self, num_matches):
        """Returns true if condition must match again to be fulfilled"""
        return num_matches < self.min_repeated


def find_matches_recursively(
        node: AttackGraphNode,
        condition_list: list[SearchCondition],
        current_path: list[AttackGraphNode] | None = None,
        matching_paths: set[tuple[AttackGraphNode,...]] | None = None,
        condition_match_count: int = 0
    ):
    """Find all paths of nodes that match the list of conditions.
    When a sequence of conditions is fulfilled for a path of nodes,
    add the path of nodes to the returned `matching_paths`
    The function runs recursively down all paths of children nodes.

    Args:
    node                  - node to check if current `condition` matches for
    condition_list        - first condition in list will attempt match `node`
    current_path          - list of matched nodes so far (recursively built)
    matching_paths        - set of matched paths so far (recursively built)
    condition_match_count - number of matches on current condition so far

    Return: set of tuples (paths) of AttackGraphNodes that match the condition
    """

    # Init path lists if None, or copy/init into new lists for each iteration
    current_path = [] if current_path is None else list(current_path)
    matching_paths = set() if matching_paths is None else matching_paths

    curr_cond, *next_conds = condition_list

    if node in current_path:
        # Stop the chain, infinite loop
        return matching_paths

    if next_conds and not curr_cond.must_match_again(condition_match_count):
        # Try next condition for current node if there are more and
        # current condition is already fulfilled.
        matching_paths = find_matches_recursively(
            node,
            next_conds,
            current_path=current_path,
            matching_paths=matching_paths
        )

    if curr_cond.matches(node):
        # Current node matches, add to current_path and increment match_count
        current_path.append(node)
        condition_match_count += 1

        if next_conds:
            # If there are more conditions, try next one for all children
            for child in node.children:
                matching_paths = find_matches_recursively(
                    child,
                    next_conds,
                    current_path=current_path,
                    matching_paths=matching_paths,
                )
        if curr_cond.can_match_again(condition_match_count):
            # If we can match current condition again, try for all children
            for child in node.children:
                matching_paths = find_matches_recursively(
                    child,
                    [curr_cond] + next_conds,
                    current_path=current_path,
                    matching_paths=matching_paths,
                    condition_match_count=condition_match_count
                )

        if not next_conds:
            # Congrats - matched a full unique search pattern!
            matching_paths.add(tuple(current_path)) # tuple is hashable

    return matching_paths
