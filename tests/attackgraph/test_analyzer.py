"""Tests for analyzers"""

from maltoolbox.attackgraph.attackgraph import AttackGraph
from maltoolbox.attackgraph.analyzers.apriori import (
    propagate_viability_from_unviable_node,
    prune_unviable_and_unnecessary_nodes,
)
from maltoolbox.language import LanguageGraph

# Apriori analyzer
# TODO: Add apriori analyzer test implementations

# def test_analyzers_apriori_propagate_viability_from_node():
#     """See if viability is propagated correctly"""
#     pass


# def test_analyzers_apriori_propagate_necessity_from_node():
#     """See if necessity is propagated correctly"""
#     pass


# def test_analyzers_apriori_evaluate_viability():
#     pass


# def test_analyzers_apriori_evaluate_necessity():
#     pass


# def test_analyzers_apriori_evaluate_viability_and_necessity():
#     pass


# def test_analyzers_apriori_calculate_viability_and_necessity():
#     pass


def test_analyzers_apriori_prune_unviable_and_unnecessary_nodes(example_attackgraph: AttackGraph):

    # Pick out an or node and make it non-necessary
    node_to_make_non_necessary = next(
        node for node in example_attackgraph.nodes.values()
        if node.type == 'or'
    )

    node_to_make_non_necessary.is_necessary = False
    prune_unviable_and_unnecessary_nodes(example_attackgraph)
    assert node_to_make_non_necessary.id not in example_attackgraph.nodes


def test_analyzers_apriori_propagate_viability_from_unviable_node(dummy_lang_graph: LanguageGraph):
    r"""Create a graph from nodes

            node1
            /    \
        node2    node3
        /   \   /    \
    node4  node5    node6
    """

    dummy_or_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyOrAttackStep']
    dummy_defense_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyDefenseAttackStep']
    attack_graph = AttackGraph(dummy_lang_graph)

    # Create a graph of nodes according to above diagram
    node1 = attack_graph.add_node(
        lg_attack_step = dummy_defense_attack_step
    )
    node2 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node3 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node4 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node5 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node6 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )

    node1.children = {node2, node3}
    node2.children = {node4, node5}
    node3.children = {node5, node6}

    node2.parents = {node1}
    node4.parents = {node2}
    node5.parents = {node2, node3}
    node6.parents = {node3}

    node1.defense_status = 1.0
    node1.is_viable = False
    unviable_nodes = propagate_viability_from_unviable_node(node1)
    unviable_node_names = {node.name for node in unviable_nodes}
    expected_unviable_node_names = {
        node2.name, node3.name, node4.name, node5.name, node6.name
    }
    assert unviable_node_names == expected_unviable_node_names
