"""Unit tests for AttackGraphNode functionality"""

from maltoolbox.attackgraph.node import AttackGraphNode
from maltoolbox.attackgraph.attacker import Attacker
from maltoolbox.attackgraph.attackgraph import AttackGraph

def test_attacker_to_dict():
    """Test Attacker to dict conversion"""
    node1 = AttackGraphNode(
        type = "or",
        name = "node1"
    )
    attacker = Attacker("Test Attacker", [], [node1])
    assert attacker.to_dict() == {
        "id": None,
        "name": "Test Attacker",
        "entry_points": {},
        "reached_attack_steps": {
            node1.id : str(node1.id) + ':' + node1.name
        }
    }

def test_attacker_compromise():
    """Attack a node and see expected behavior"""
    node1 = AttackGraphNode(
        type = "or",
        name = "node1"
    )
    attacker = Attacker("Test Attacker", [], [])
    assert not attacker.entry_points
    attack_graph = AttackGraph()
    attack_graph.add_node(node1)
    attack_graph.add_attacker(attacker)

    attacker.compromise(node1)
    assert attacker.reached_attack_steps == [node1]
    assert not attacker.entry_points

    assert node1.compromised_by == [attacker]

    attacker.compromise(node1) # Compromise same node again not a problem
    assert attacker.reached_attack_steps == [node1]
    assert node1.compromised_by == [attacker]

def test_attacker_undo_compromise():
    """Make sure undo compromise removes attacker/node"""
    node1 = AttackGraphNode(
        type = "or",
        name = "node1"
    )
    attacker = Attacker("attacker1", [], [])
    attack_graph = AttackGraph()
    attack_graph.add_node(node1)
    attack_graph.add_attacker(attacker)

    attacker.compromise(node1)
    assert attacker.reached_attack_steps == [node1]
    assert node1.compromised_by == [attacker]
    attacker.compromise(node1) # Compromise same node again not a problem
    assert attacker.reached_attack_steps == [node1]
    assert node1.compromised_by == [attacker]

    attacker.undo_compromise(node1)
    # Make sure attacker/node  was removed
    assert attacker.reached_attack_steps == []
    assert node1.compromised_by == []
