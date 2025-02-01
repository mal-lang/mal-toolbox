"""Tests for analyzers."""

from maltoolbox.attackgraph import AttackGraphNode
from maltoolbox.attackgraph.analyzers.apriori import (
    propagate_viability_from_unviable_node,
)

# Apriori analyzer
# TODO: Add apriori analyzer test implementations


def test_analyzers_apriori_propagate_viability_from_node() -> None:
    """See if viability is propagated correctly."""


def test_analyzers_apriori_propagate_necessity_from_node() -> None:
    """See if necessity is propagated correctly."""


def test_analyzers_apriori_evaluate_viability() -> None:
    pass


def test_analyzers_apriori_evaluate_necessity() -> None:
    pass


def test_analyzers_apriori_evaluate_viability_and_necessity() -> None:
    pass


def test_analyzers_apriori_calculate_viability_and_necessity() -> None:
    pass


def test_analyzers_apriori_prune_unviable_and_unnecessary_nodes() -> None:
    pass


def test_analyzers_apriori_propagate_viability_from_unviable_node() -> None:
    r"""Create a graph from nodes.

        node1
        /    \
        node2    node3
    /   \   /    \
    node4  node5    node6
    """
    # Create a graph of nodes according to above diagram
    node1 = AttackGraphNode(
        type='defense',
        name='node1',
        lang_graph_attack_step=None,
    )
    node2 = AttackGraphNode(
        type='or',
        name='node2',
        lang_graph_attack_step=None,
    )
    node3 = AttackGraphNode(
        type='or', name='node3', lang_graph_attack_step=None, defense_status=0.0
    )
    node4 = AttackGraphNode(
        type='or',
        name='node4',
        lang_graph_attack_step=None,
    )
    node5 = AttackGraphNode(
        type='or',
        name='node5',
        lang_graph_attack_step=None,
    )
    node6 = AttackGraphNode(
        type='or',
        name='node6',
        lang_graph_attack_step=None,
    )

    node1.id = 1
    node2.id = 2
    node3.id = 3
    node4.id = 4
    node5.id = 5
    node6.id = 6

    node1.children = [node2, node3]
    node2.children = [node4, node5]
    node3.children = [node5, node6]

    node2.parents = [node1]
    node4.parents = [node2]
    node5.parents = [node2, node3]
    node6.parents = [node3]

    node1.defense_status = 1.0
    node1.is_viable = False
    unviable_nodes = propagate_viability_from_unviable_node(node1)
    unviable_node_names = {node.name for node in unviable_nodes}
    expected_unviable_node_names = {
        node2.name,
        node3.name,
        node4.name,
        node5.name,
        node6.name,
    }
    assert unviable_node_names == expected_unviable_node_names
