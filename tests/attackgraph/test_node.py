"""Unit tests for AttackGraphNode functionality"""

from maltoolbox.attackgraph.attacker import Attacker
from maltoolbox.attackgraph.attackgraph import AttackGraph
from maltoolbox.language import LanguageGraph


def test_attackgraphnode(dummy_lang_graph: LanguageGraph):
    r"""Create a graph from nodes

            node1
            /    \
        node2    node3
        /   \   /    \
    node4  node5    node6
    """

    dummy_or_attack_step = dummy_lang_graph.assets['DummyAsset'].attack_steps[
        'DummyOrAttackStep'
    ]
    dummy_defense_attack_step = dummy_lang_graph.assets['DummyAsset'].attack_steps[
        'DummyDefenseAttackStep'
    ]
    attack_graph = AttackGraph(dummy_lang_graph)

    # Create a graph of nodes according to above diagram
    node1 = attack_graph.add_node(lg_attack_step=dummy_or_attack_step)
    node2 = attack_graph.add_node(lg_attack_step=dummy_defense_attack_step)
    node2.defense_status = 1.0
    node3 = attack_graph.add_node(lg_attack_step=dummy_defense_attack_step)
    node3.defense_status = 0.0
    node4 = attack_graph.add_node(lg_attack_step=dummy_or_attack_step)
    node5 = attack_graph.add_node(lg_attack_step=dummy_or_attack_step)
    node6 = attack_graph.add_node(lg_attack_step=dummy_or_attack_step)

    node1.children = {node2, node3}
    node2.children = {node4, node5}
    node3.children = {node5, node6}

    node2.parents = {node1}
    node4.parents = {node2}
    node5.parents = {node2, node3}
    node6.parents = {node3}

    # Make sure compromised node has attacker added to it
    attacker = Attacker(
        name='Test Attacker',
        entry_points={node1},
    )

    attack_graph.add_attacker(attacker)

    node6.compromise(attacker)
    assert node6.compromised_by == {attacker}
    assert node6.is_compromised()
    assert node6.is_compromised_by(attacker)

    # Make sure uncompromise will remove the attacker
    node6.undo_compromise(attacker)
    assert node6.compromised_by == set()
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
