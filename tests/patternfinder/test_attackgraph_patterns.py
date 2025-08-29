"""Tests for attack graph pattern matching"""

import math
import pytest

from maltoolbox.model import Model
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode

from maltoolbox.patternfinder.attackgraph_patterns import (
    SearchPattern, SearchCondition
)


@pytest.fixture
def example_attackgraph(corelang_lang_graph, model: Model):
    """Fixture that generates an example attack graph
    
    Uses coreLang specification and model with two applications
    with an association and an attacker to create and return
    an AttackGraph object
    """

    # Create 2 assets
    app1 = model.add_asset("Application", "Application 1")
    app2 = model.add_asset("Application", "Application 2")

    # Create association between app1 and app2
    app1.add_associated_assets('appExecutedApps', {app2})

    return AttackGraph(lang_graph=corelang_lang_graph, model=model)


def test_attackgraph_find_pattern_example_graph(example_attackgraph):
    """Test a simple pattern"""
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda n : n.name == "attemptRead"
            ),
            SearchCondition(
                lambda n : n.name == "successfulRead"
            ),
            SearchCondition(
                lambda n : n.name == "read"
            )
        ]
    )

    paths = pattern.find_matches(example_attackgraph)
    # Make sure the paths match the pattern
    for path in paths:
        assert [n.name for n in path] == ['attemptRead', 'successfulRead', 'read']


def test_attackgraph_find_multiple(dummy_lang_graph):
    """Create a simple AttackGraph, find pattern with more than one match
    
                            Node1
                          /       \
                      Node2       Node3
                      /            /   \
                   Node4        Node5  Node6
                    /
                 Node7
    """
    attack_graph = AttackGraph(
        dummy_lang_graph, Model("hej", dummy_lang_graph)
    )

    # Create the graph
    dummy_and_step = dummy_lang_graph.assets['DummyAsset'].attack_steps['DummyAndAttackStep']
    node1 = AttackGraphNode(1, dummy_and_step, dummy_lang_graph.assets['DummyAsset'])
    node2 = AttackGraphNode(2, dummy_and_step, dummy_lang_graph.assets['DummyAsset'])
    node2.parents = {node1}
    node3 = AttackGraphNode(3, dummy_and_step, dummy_lang_graph.assets['DummyAsset'])
    node3.parents = {node1}
    node1.children = {node2, node3}
    node4 = AttackGraphNode(4, dummy_and_step, dummy_lang_graph.assets['DummyAsset'])
    node4.parents = {node2}
    node2.children = {node4}
    node5 = AttackGraphNode(5, dummy_and_step, dummy_lang_graph.assets['DummyAsset'])
    node5.parents = {node3}
    node6 = AttackGraphNode(6, dummy_and_step, dummy_lang_graph.assets['DummyAsset'])
    node6.parents = {node3}
    node3.children = {node5, node6}
    node7 = AttackGraphNode(7, dummy_and_step, dummy_lang_graph.assets['DummyAsset'])
    node7.parents = {node4}
    node4.children = {node7}

    attack_graph.nodes = {
        node1.id: node1,
        node2.id: node2,
        node3.id: node3,
        node4.id: node4,
        node5.id: node5,
        node6.id: node6,
        node7.id: node7
    }

    # Create the search pattern from Node1 to either Node6 or Node7
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda node: node.id == 1
            ),
            SearchCondition(
                SearchCondition.ANY, # Match any node
                max_repeated=math.inf # Any number of times
            ),
            SearchCondition(
                lambda node: node.id in (6, 7)
            )
        ]
    )
    paths = pattern.find_matches(attack_graph)

    # Make sure we find two paths: (Node1->Node7) and (Node1->Node6)
    assert len(paths) == 2

    assert (node1, node2, node4, node7) in paths
    assert (node1, node3, node6) in paths


def test_attackgraph_find_multiple_same_subpath(dummy_lang_graph):
    """Create a simple AttackGraph, find paths which match pattern
       where several matching paths share same subpath in the graph
    
                            Node1
                          /       \
                      Node2       Node3
                       /             \
                   Node4             Node5
    """
    attack_graph = AttackGraph(None)

    # Create the graph
    dummy_asset = dummy_lang_graph.assets['DummyAsset']
    dummy_and_step = (
        dummy_asset.attack_steps['DummyAndAttackStep']
    )
    node1 = AttackGraphNode(1, dummy_and_step, dummy_asset)
    node2 = AttackGraphNode(2, dummy_and_step, dummy_asset)
    node2.parents = {node1}
    node3 = AttackGraphNode(3, dummy_and_step, dummy_asset)
    node3.parents = {node1}
    node1.children = {node2, node3}
    node4 = AttackGraphNode(4, dummy_and_step, dummy_asset)
    node4.parents = {node2}
    node2.children = {node4}
    node5 = AttackGraphNode(5, dummy_and_step, dummy_asset)
    node5.parents = {node3}
    node3.children = {node5}
    attack_graph.nodes = {
        node1.id: node1,
        node2.id: node2,
        node3.id: node3,
        node4.id: node4,
        node5.id: node5
    }

    # Create the search pattern to find paths from Node1 to any node
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda node: node.id == 1
            ),
            SearchCondition(
                lambda node: True,
                max_repeated=math.inf,
                min_repeated=0,
            ),
            SearchCondition(
                lambda node: node.id in (2, 3, 4, 5)
            )
        ]
    )
    paths = pattern.find_matches(attack_graph)

    # Make sure we find all paths
    assert (node1, node2, node4) in paths
    assert (node1, node3, node5) in paths
    assert (node1, node2) in paths
    assert (node1, node3) in paths


def test_attackgraph_two_same_start_end_node(dummy_lang_graph):
    """Create a simple AttackGraph, find paths which match pattern
       where both matching paths start and end att the same node
    
                            Node1
                          /       \
                      Node2       Node3
                          \        /
                             Node4
    """
    attack_graph = AttackGraph(None)

    # Create the graph
    dummy_asset = dummy_lang_graph.assets['DummyAsset']
    dummy_and_step = (
        dummy_asset.attack_steps['DummyAndAttackStep']
    )

    node1 = AttackGraphNode(1, dummy_and_step, dummy_asset)
    node2 = AttackGraphNode(2, dummy_and_step, dummy_asset)
    node2.parents = {node1}
    node3 = AttackGraphNode(3, dummy_and_step, dummy_asset)
    node3.parents = {node1}
    node1.children = {node2, node3}
    node4 = AttackGraphNode(4, dummy_and_step, dummy_asset)
    node2.children = {node4}
    node3.children = {node4}
    node4.parents = {node2, node3}

    attack_graph.nodes = {
        node1.id: node1,
        node2.id: node2,
        node3.id: node3,
        node4.id: node4
    }

    # Create the search pattern to find paths from Node1 to any node
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda node: node.id == 1
            ),
            SearchCondition(
                SearchCondition.ANY
            ),
            SearchCondition(
                lambda node: node.id == 4
            )
        ]
    )
    paths = pattern.find_matches(attack_graph)

    # Make sure we find expected paths
    assert (node1, node2, node4) in paths
    assert (node1, node3, node4) in paths
