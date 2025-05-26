"""Unit tests for AttackGraph functionality"""

from maltoolbox.attackgraph import Attacker, AttackGraph
from maltoolbox.attackgraph.query import (
    calculate_attack_surface,
    is_node_traversable_by_attacker
)
from maltoolbox.language import LanguageGraph

from .node_test_utils import (
    add_viable_and_node,
    add_viable_or_node,
    add_non_viable_and_node,
    add_non_viable_or_node
)

def test_traversability_traversable(dummy_lang_graph):
    """Make sure traversability works as expected"""
    attack_graph = AttackGraph(dummy_lang_graph)
    attacker = Attacker('Attacker1')
    attack_graph.add_attacker(attacker)

    # Viable and-node where all necessary parents are compromised
    viable_and_node = add_viable_and_node(attack_graph)
    for parent in viable_and_node.parents:
        parent.is_necessary = True
        attacker.compromise(parent)
    assert is_node_traversable_by_attacker(viable_and_node, attacker)

    # Viable or-node where at least one parent is compromised
    viable_or_node = add_viable_or_node(attack_graph)
    parent = next(iter(viable_or_node.parents))
    parent.is_necessary = True
    attacker.compromise(parent)
    assert is_node_traversable_by_attacker(viable_or_node, attacker)


def test_traversability_not_traversable(dummy_lang_graph):
    """Make sure nodes that shouldn't be traversable aren't"""
    attack_graph = AttackGraph(dummy_lang_graph)
    attacker = Attacker('Attacker1')
    attack_graph.add_attacker(attacker)

    # Viable and-node where not all necessary parents are compromised
    # -> not traversable
    non_viable_and_node = add_non_viable_and_node(attack_graph)
    assert not is_node_traversable_by_attacker(non_viable_and_node, attacker)

    # Nonviable and-node where all necessary parents are compromised
    # -> not traversabel
    viable_and_node = add_non_viable_and_node(attack_graph)
    for parent in viable_and_node.parents:
        parent.is_necessary = True
        attacker.compromise(parent)
    assert not is_node_traversable_by_attacker(viable_and_node, attacker)

    # Viable or-node where no parent is compromised -> not traversable
    non_viable_or_node = add_non_viable_or_node(attack_graph)
    assert not is_node_traversable_by_attacker(non_viable_or_node, attacker)

    # Nonviable or-node where parent is compromised -> not traversable
    viable_or_node = add_viable_or_node(attack_graph)
    parent = next(iter(viable_or_node.parents))
    parent.is_necessary = True
    attacker.compromise(parent)

    # Fails because the function assumes that one parent is traversable
    # TODO: Should this be changed?
    # assert not is_node_traversable_by_attacker(viable_or_node, attacker)


def test_query_is_node_traversable_by_attacker(dummy_lang_graph: LanguageGraph):
    """Make sure it returns True or False when expected"""

    dummy_or_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyOrAttackStep']
    dummy_and_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyAndAttackStep']
    attack_graph = AttackGraph(dummy_lang_graph)

    # An attacker with no meaningful data
    attacker = Attacker(name = "Test Attacker")
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


def test_get_attack_surface(dummy_lang_graph: LanguageGraph):
    r"""Create a graph from nodes

             ___node0___
            /    \      \
        node1    node2   node3
        /   \        \      \
    node4  node5    node6   node7
    """

    dummy_or_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyOrAttackStep']
    attack_graph = AttackGraph(dummy_lang_graph)

    # Create a graph of nodes according to above diagram
    node0 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)
    node1 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)
    node2 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)
    node3 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)
    node4 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)
    node5 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)
    node6 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)
    node7 = attack_graph.add_node(lg_attack_step = dummy_or_attack_step)

    node0.children = {node1, node2, node3}
    node1.children = {node4, node5}
    node2.children = {node6}
    node3.children = {node7}

    node1.parents = {node0}
    node2.parents = {node0}
    node3.parents = {node0}
    node4.parents = {node1}
    node5.parents = {node1}
    node6.parents = {node2}
    node7.parents = {node3}

    # Make sure compromised node has attacker added to it
    attacker = Attacker(
        name = "Test Attacker",
        reached_attack_steps = {node0, node1, node2},
        attacker_id = 100
    )

    attack_graph.add_attacker(attacker)

    attack_surface = calculate_attack_surface(attacker)
    assert attack_surface == {node1, node2, node3, node4, node5, node6}

    attack_surface = calculate_attack_surface(attacker, skip_compromised=True)
    assert attack_surface == {node3, node4, node5, node6}

    attack_surface = calculate_attack_surface(attacker, from_nodes={node0})
    assert attack_surface == {node1, node2, node3}

    attack_surface = calculate_attack_surface(
        attacker, from_nodes={node0}, skip_compromised=True)
    assert attack_surface == {node3}

    attack_surface = calculate_attack_surface(attacker, from_nodes={node1})
    assert attack_surface == {node4, node5}

    attack_surface = calculate_attack_surface(attacker, from_nodes={node3})
    assert attack_surface == set()
