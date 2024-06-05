"""Unit tests for AttackGraph functionality"""

from maltoolbox.attackgraph import AttackGraphNode, Attacker
from maltoolbox.attackgraph.query import (
    is_node_traversable_by_attacker,
)

def test_query_is_node_traversable_by_attacker():
    """Make sure it returns True or False when expected"""
    # An attacker with no meaningful data
    attacker = Attacker("attackerid", [], [])

    # Node1 should be traversable since node type is OR
    node1 = AttackGraphNode("Node1", "or", "name", {})
    traversable = is_node_traversable_by_attacker(node1, attacker)
    assert traversable

    # Node2 should be traversable since node has no parents
    node2 = AttackGraphNode("Node2", "and", "name", {})
    traversable = is_node_traversable_by_attacker(node2, attacker)
    assert traversable

    # Node 4 should not be traversable since node has type AND
    # and it has two parents that are not compromised by attacker
    node3 = AttackGraphNode("Node3", "and", "name", {})
    node4 = AttackGraphNode("Node4", "and", "name", {})
    node4.parents = [node2, node3]
    node2.children = [node4]
    node3.children = [node4]
    traversable = is_node_traversable_by_attacker(node4, attacker)
    assert not traversable
