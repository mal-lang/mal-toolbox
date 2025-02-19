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
        entry_points = set(),
        reached_attack_steps = set()
    )
    attack_graph.add_attacker(attacker)

    # Node 3 should not be traversable since node has type AND and it has two
    # parents that are not compromised by attacker
    node1 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node2 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node3 = attack_graph.add_node(
        lg_attack_step = dummy_and_attack_step
    )
    node3.parents = {node1, node2}
    node2.children = {node3}
    node1.children = {node3}
    traversable = is_node_traversable_by_attacker(node3, attacker)
    assert not traversable

    # After compromising one of its parents it should still be untraversable
    # as the other parent has not been compromised.
    attacker.compromise(node1)
    traversable = is_node_traversable_by_attacker(node3, attacker)
    assert not traversable

    # After compromising both of its parents it should be traversable.
    attacker.compromise(node2)
    traversable = is_node_traversable_by_attacker(node3, attacker)
    assert traversable

    # Node 6 should not be traversable since node has type OR and neither of
    # its two parents are not compromised by attacker
    node4 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node5 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node6 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node6.parents = {node4, node5}
    node4.children = {node6}
    node5.children = {node6}
    traversable = is_node_traversable_by_attacker(node6, attacker)
    assert not traversable

    # After compromising one of its parents it should still be traversable.
    attacker.compromise(node4)
    traversable = is_node_traversable_by_attacker(node6, attacker)
    assert traversable
