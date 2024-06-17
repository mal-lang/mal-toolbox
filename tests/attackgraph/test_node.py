"""Unit tests for AttackGraphNode functionality"""

from maltoolbox.attackgraph.node import AttackGraphNode
from maltoolbox.attackgraph.attacker import Attacker

def test_attackgraphnode():
    """Create a graph from nodes

            node1
            /    \
        node2    node3
        /   \   /    \
    node4  node5    node6
    """

    # Create a graph of nodes according to above diagram
    node1 = AttackGraphNode("1", "or", "node1", ttc=None, tags=[])
    node2 = AttackGraphNode(
        "2", "defense", "node2", ttc=None, tags=[], defense_status=1.0)
    node3 = AttackGraphNode(
        "3", "defense", "node3", ttc=None, tags=[], defense_status=0.0)
    node4 = AttackGraphNode("4", "or", "node4", ttc=None, tags=[])
    node5 = AttackGraphNode("5", "and", "node5", ttc=None, tags=[])
    node6 = AttackGraphNode("6", "or", "node6", ttc=None, tags=[])

    node1.children = [node2, node3]
    node2.children = [node4, node5]
    node3.children = [node5, node6]

    node2.parents = [node1]
    node4.parents = [node2]
    node5.parents = [node2, node3]
    node6.parents = [node3]

    # Make sure compromised node has attacker added to it
    attacker = Attacker(
        "1", entry_points=[node1], reached_attack_steps=[]
    )
    node6.compromise(attacker)
    assert node6.compromised_by == [attacker]
    assert node6.is_compromised()
    assert node6.is_compromised_by(attacker)

    # Make sure uncompromise will remove the attacker
    node6.undo_compromise(attacker)
    assert node6.compromised_by == []
    assert not node6.is_compromised()

    # Node 3 is disabled defense
    assert node3.is_available_defense()
    assert not node3.is_enabled_defense()

    # Node 2 is enabled defense
    assert not node2.is_available_defense()
    assert node2.is_enabled_defense()

    # Node 1 is not a defense
    assert not node1.is_available_defense()
    assert not node1.is_enabled_defense()
