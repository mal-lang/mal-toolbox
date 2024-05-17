"""Utilities for finding patterns in the AttackGraph"""

from __future__ import annotations
from dataclasses import dataclass, field
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode
from typing import Callable
class SearchPattern:
    """A pattern consists of conditions, the conditions are used
    to find matching paths in an attack graph"""
    conditions: list[Condition]

    def __init__(self, conditions):
        self.conditions = conditions

    def find_matches(self, graph: AttackGraph):
        """Search through a graph for a pattern using
        its conditions, and return matching paths of nodes

        Args:
        graph   - The graph to search in
    
        Return: list[list[AttackGraphNode]] of matching paths
        """

        # Find the starting nodes
        condition = self.conditions[0]
        starting_nodes = []
        for node in graph.nodes:
            if condition.matches(node):
                starting_nodes.append(node)

        matching_paths = []
        for node in starting_nodes:
            matching_paths.extend(
                find_matches_recursively(node, self.conditions)
            )

        return matching_paths

@dataclass
class SearchCondition:
    """A filter has a condition that has to be true for a node to match"""

    # `matches` should be a lambda that takes node as input and returns bool
    # If lamdba returns True for a node, the node matches
    # If the lamdba returns False for a node, the node does not match
    matches: Callable[[AttackGraphNode], bool]

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
        condition_list: list[Condition],
        current_path=None,
        matching_paths=None,
        condition_match_count=0
    ):
    """Find all paths of nodes that match the list of conditions.
    When a sequence of conditions is fulfilled for a path of nodes,
    add the path of nodes to the returned `matching_paths`

    Args:
    node                - node to check if current `condition` matches for
    condition_list     - first condition in list will attempt match `node`
    matching_nodes      - list of matched nodes so far (builds up recursively)
    condition_match_count - the number of matches on current condition so far

    Return: list of lists of AttackGraphNodes that match the condition
    """
    # Init path lists if None
    current_path = [] if current_path is None else current_path
    matching_paths = [] if matching_paths is None else matching_paths

    current_exp = condition_list[0]

    if current_exp.matches(node):
        # Current node matches, add to current_path and increment match_count
        current_path.append(node)
        condition_match_count += 1

        if len(condition_list) == 1 \
            and not current_exp.must_match_again(condition_match_count):
            # This is the last condition in the path,
            # and the current path is matching
            matching_paths.append(current_path)

        elif current_exp.can_match_again(condition_match_count):
            # Pattern has matches left, run recursively with current condition
            for child in node.children:
                matching_paths = find_matches_recursively(
                    child,
                    condition_list,
                    current_path=current_path,
                    matching_paths=matching_paths,
                    condition_match_count=condition_match_count
                )
        else:
            # Pattern has run out of matches, must move on to next condition
            for child in node.children:
                matching_paths = find_matches_recursively(
                    child,
                    condition_list[1:],
                    current_path=current_path,
                    matching_paths=matching_paths
                )
    else:
        if not current_exp.must_match_again(condition_match_count)\
            and len(condition_list) > 1:
            # Node did not match current condition, but we can try with
            # the next condition since current one is 'fulfilled'
            matching_paths = find_matches_recursively(
                node,
                condition_list[1:],
                current_path=current_path,
                matching_paths=matching_paths
            )

    return matching_paths
