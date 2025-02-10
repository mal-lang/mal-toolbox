"""Unit tests for AttackGraph functionality"""

from maltoolbox.attackgraph import AttackGraphNode, Attacker, AttackGraph
from maltoolbox.language import LanguageGraph
from maltoolbox.attackgraph.query import (
    is_node_traversable_by_attacker,
)

def test_query_is_node_traversable_by_attacker(dummy_lang_graph: LanguageGraph):
    """Make sure it returns True or False when expected"""

    dummy_or_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyOrAttackStep']
    dummy_and_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyAndAttackStep']
    attack_graph = AttackGraph(dummy_lang_graph)

    # An attacker with no meaningful data
    attacker = Attacker(
        name = "Test Attacker",
        entry_points = [],
        reached_attack_steps = []
    )
    attack_graph.add_attacker(attacker)

    # Node1 should be traversable since node type is OR
    node1 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    traversable = is_node_traversable_by_attacker(node1, attacker)
    assert traversable

    # Node2 should be traversable since node has no parents
    node2 = attack_graph.add_node(
        lg_attack_step = dummy_and_attack_step
    )
    traversable = is_node_traversable_by_attacker(node2, attacker)
    assert traversable

    # Node 4 should not be traversable since node has type AND
    # and it has two parents that are not compromised by attacker
    node3 = attack_graph.add_node(
        lg_attack_step = dummy_and_attack_step
    )
    node4 = attack_graph.add_node(
        lg_attack_step = dummy_and_attack_step
    )
    node4.parents = [node2, node3]
    node2.children = [node4]
    node3.children = [node4]
    traversable = is_node_traversable_by_attacker(node4, attacker)
    assert not traversable
