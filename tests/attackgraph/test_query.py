"""Unit tests for AttackGraph functionality"""

from maltoolbox.attackgraph import AttackGraphNode, Attacker, AttackGraph
from maltoolbox.language import LanguageGraph
from maltoolbox.attackgraph.query import (
    is_node_traversable_by_attacker,
)

def test_query_is_node_traversable_by_attacker(dummy_lang_graph: LanguageGraph):
    """Make sure it returns True or False when expected"""

    dummy_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyAttackStep']

    # An attacker with no meaningful data
    attacker = Attacker(
        name = "Test Attacker",
        entry_points = [],
        reached_attack_steps = []
    )

    # Node1 should be traversable since node type is OR
    node1 = AttackGraphNode(
        type = "or",
        name = "node1",
        lang_graph_attack_step = dummy_attack_step,
    )

    attack_graph = AttackGraph(dummy_lang_graph)
    attack_graph.add_node(node1)
    attack_graph.add_attacker(attacker)
    traversable = is_node_traversable_by_attacker(node1, attacker)
    assert traversable

    # Node2 should be traversable since node has no parents
    node2 = AttackGraphNode(
        type = "and",
        name = "node2",
        lang_graph_attack_step = dummy_attack_step,
    )
    attack_graph.add_node(node2)
    traversable = is_node_traversable_by_attacker(node2, attacker)
    assert traversable

    # Node 4 should not be traversable since node has type AND
    # and it has two parents that are not compromised by attacker
    node3 = AttackGraphNode(
        type = "and",
        name = "node3",
        lang_graph_attack_step = dummy_attack_step,
    )
    node4 = AttackGraphNode(
        type = "and",
        name = "node4",
        lang_graph_attack_step = dummy_attack_step,
    )
    node4.parents = [node2, node3]
    node2.children = [node4]
    node3.children = [node4]
    attack_graph.add_node(node3)
    attack_graph.add_node(node4)
    traversable = is_node_traversable_by_attacker(node4, attacker)
    assert not traversable
