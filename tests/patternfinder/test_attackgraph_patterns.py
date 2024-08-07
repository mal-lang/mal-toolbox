"""Tests for attack graph pattern matching"""
import pytest
from maltoolbox.model import Model, AttackerAttachment
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode
import math

from maltoolbox.patternfinder.attackgraph_patterns import (
    SearchPattern, SearchCondition
)

from test_model import create_application_asset, create_association

@pytest.fixture
def example_attackgraph(corelang_lang_graph, model: Model):
    """Fixture that generates an example attack graph
    
    Uses coreLang specification and model with two applications
    with an association and an attacker to create and return
    an AttackGraph object
    """

    # Create 2 assets
    app1 = create_application_asset(model, "Application 1")
    app2 = create_application_asset(model, "Application 2")
    model.add_asset(app1)
    model.add_asset(app2)

    # Create association between app1 and app2
    assoc = create_association(model, left_assets=[app1], right_assets=[app2])
    model.add_association(assoc)

    attacker = AttackerAttachment()
    attacker.entry_points = [
        (app1, ['attemptCredentialsReuse'])
    ]
    model.add_attacker(attacker)

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
    assert paths
    for path in paths:
        conditions = list(pattern.conditions)
        num_matches_curr_condition = 0
        curr_condition = conditions.pop(0)
        curr_node = path.pop(0)

        while path or conditions:

            if curr_condition.matches(curr_node):
                num_matches_curr_condition += 1
                curr_node = path.pop(0)

            elif not curr_condition.must_match_again(
                    num_matches_curr_condition
                ):
                curr_condition = conditions.pop(0)
                num_matches_curr_condition = 0

            else:
                assert False, "Chain does not match pattern conditions"


def test_attackgraph_find_multiple():
    """Create a simple AttackGraph, find pattern with more than one match
    
                            Node1
                          /       \
                      Node2       Node3
                      /            /   \
                   Node4        Node5  Node6
                    /
                 Node7
    """
    attack_graph = AttackGraph()

    # Create the graph
    node1 = AttackGraphNode("and", "Node1", {})
    node2 = AttackGraphNode("and", "Node2", {}, parents=[node1])
    node3 = AttackGraphNode("and", "Node3", {}, parents=[node1])
    node1.children = [node2, node3]
    node4 = AttackGraphNode("and", "Node4", {}, parents=[node2])
    node2.children = [node4]
    node5 = AttackGraphNode("and", "Node5", {}, parents=[node3])
    node6 = AttackGraphNode("and", "Node6", {}, parents=[node3])
    node3.children = [node5, node6]
    node7 = AttackGraphNode("and", "Node7", {}, parents=[node4])
    node4.children = [node7]
    attack_graph.nodes = [node1, node2, node3, node4, node5, node6, node7]
    
    # Create the search pattern from Node1 to either Node6 or Node7
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda node: node.name == "Node1"
            ),
            SearchCondition(
                SearchCondition.ANY, # Match any node
                max_repeated=math.inf # Any number of times
            ),
            SearchCondition(
                lambda node: node.name in ("Node6", "Node7")
            )
        ]
    )
    paths = pattern.find_matches(attack_graph)

    # Make sure we find two paths: (Node1->Node7) and (Node1->Node6)
    assert len(paths) == 2

    assert [node1, node2, node4, node7] in paths
    assert [node1, node3, node6] in paths


def test_attackgraph_find_multiple_same_subpath():
    """Create a simple AttackGraph, find paths which match pattern
       where several matching paths share same subpath in the graph
    
                            Node1
                          /       \
                      Node2       Node3
                       /             \
                   Node4             Node5
    """
    attack_graph = AttackGraph()

    # Create the graph
    node1 = AttackGraphNode("and", "Node1", {})
    node2 = AttackGraphNode(
        "and", "Node2", {}, parents=[node1])
    node3 = AttackGraphNode(
        "and", "Node3", {}, parents=[node1])
    node1.children = [node2, node3]
    node4 = AttackGraphNode(
        "and", "Node4", {}, parents=[node2])
    node2.children = [node4]
    node5 = AttackGraphNode(
        "and", "Node5", {}, parents=[node3])
    node3.children = [node5]
    attack_graph.nodes = [node1, node2, node3, node4, node5]

    # Create the search pattern to find paths from Node1 to any node
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda node: node.name == "Node1"
            ),
            SearchCondition(
                lambda node: True,
                max_repeated=math.inf,
                min_repeated=0,
            ),
            SearchCondition(
                lambda node: node.name in ("Node2", "Node3", "Node4", "Node5")
            )
        ]
    )
    paths = pattern.find_matches(attack_graph)

    # Make sure we find all paths
    assert [node1, node2, node4] in paths
    assert [node1, node3, node5] in paths
    assert [node1, node2] in paths
    assert [node1, node3] in paths
