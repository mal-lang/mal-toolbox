"""Unit tests for AttackGraphNode functionality"""

from maltoolbox.attackgraph.node import AttackGraphNode
from maltoolbox.attackgraph.attacker import Attacker
from maltoolbox.attackgraph.attackgraph import AttackGraph
from maltoolbox.language import LanguageGraph

def test_attacker_to_dict(dummy_lang_graph: LanguageGraph):
    """Test Attacker to dict conversion"""

    dummy_or_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyOrAttackStep']
    attack_graph = AttackGraph(dummy_lang_graph)

    node1 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    attacker = Attacker("Test Attacker", set(), {node1}, attacker_id = 100)
    assert attacker.to_dict() == {
        "id": 100,
        "name": "Test Attacker",
        "entry_points": {},
        "reached_attack_steps": {
            node1.id : f"{node1.id}:{node1.name}"
        }
    }

def test_attacker_compromise(dummy_lang_graph: LanguageGraph):
    """Compromise/uncompromise a node and see expected behavior"""

    dummy_or_attack_step = dummy_lang_graph.assets['DummyAsset'].\
        attack_steps['DummyOrAttackStep']
    attack_graph = AttackGraph(dummy_lang_graph)

    node1 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )
    node2 = attack_graph.add_node(
        lg_attack_step = dummy_or_attack_step
    )

    attacker = Attacker("Test Attacker")
    assert not attacker.entry_points
    attack_graph = AttackGraph(dummy_lang_graph)
    attack_graph.add_attacker(attacker)

    attacker.compromise(node1)
    assert attacker.reached_attack_steps == {node1}
    assert attacker.reached_attack_steps_list == [node1]
    assert not attacker.entry_points

    assert node1.compromised_by == {attacker}

    attacker.compromise(node1) # Compromise same node again not a problem
    assert attacker.reached_attack_steps == {node1}
    assert attacker.reached_attack_steps_list == [node1]
    assert node1.compromised_by == {attacker}

    attacker.compromise(node2)
    assert attacker.reached_attack_steps == {node2, node1}
    assert attacker.reached_attack_steps_list == [node1, node2]
    assert node1.compromised_by == {attacker}
    assert node2.compromised_by == {attacker}

    attacker.undo_compromise(node1)
    # Make sure attacker/node  was removed
    assert attacker.reached_attack_steps == {node2}
    assert attacker.reached_attack_steps_list == [node2]
    assert node1.compromised_by == set()
    assert node2.compromised_by == {attacker}
