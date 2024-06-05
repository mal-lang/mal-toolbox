"""Unit tests for AttackGraphNode functionality"""

from maltoolbox.attackgraph.node import AttackGraphNode
from maltoolbox.attackgraph.attacker import Attacker

def test_attacker_to_dict():
    """Test Attacker to dict conversion"""
    node1 = AttackGraphNode("1", "or", "node1", ttc=None, tags=[])
    attacker = Attacker(1, [], [node1])
    assert attacker.to_dict() == {
        "id": 1,
        "entry_points": [],
        "reached_attack_steps": [node1.id]
    }

def test_attacker_compromise():
    """Attack a node and see expected behavior"""
    node1 = AttackGraphNode("1", "or", "node1", ttc=None, tags=[])
    attacker = Attacker("attacker1", [], [])
    attacker.compromise(node1)
    assert attacker.reached_attack_steps == [node1]
    attacker.compromise(node1) # Compromise same node again not a problem
    assert attacker.reached_attack_steps == [node1]
    assert node1.compromised_by == [attacker]

def test_attacker_undo_compromise():
    """Make sure undo compromise removes attacker/node"""
    node1 = AttackGraphNode("1", "or", "node1", ttc=None, tags=[])
    attacker = Attacker("attacker1", [], [])
    attacker.compromise(node1)
    attacker.compromise(node1) # Compromise same node again not a problem
    attacker.undo_compromise(node1)

    # Make sure attacker/node  was removed
    assert attacker.reached_attack_steps == []
    assert node1.compromised_by == []
