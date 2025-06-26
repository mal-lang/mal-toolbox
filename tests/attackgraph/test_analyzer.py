"""Tests for analyzers"""

from maltoolbox.attackgraph import AttackGraph
from maltoolbox.attackgraph.analyzers import apriori
from maltoolbox.attackgraph.analyzers.apriori import (
    propagate_viability_from_unviable_node,
    prune_unviable_and_unnecessary_nodes,
)
from maltoolbox.language import LanguageGraph

# Tests


def test_viability_viable_nodes(dummy_lang_graph):
    """Make sure expected viable nodes are actually viable"""

    attack_graph = AttackGraph(dummy_lang_graph)
    dummy_attack_steps = dummy_lang_graph.assets['DummyAsset'].attack_steps

    # Exists + existance -> viable
    exist_attack_step_type = dummy_attack_steps['DummyExistAttackStep']
    exist_node = attack_graph.add_node(exist_attack_step_type)
    exist_node.existence_status = True

    # NotExists + nonexistance -> viable
    not_exist_attack_step_type = dummy_attack_steps['DummyNotExistAttackStep']
    not_exist_node = attack_graph.add_node(not_exist_attack_step_type)
    not_exist_node.existence_status = False

    # defense status = false -> viable
    defense_step_type = dummy_attack_steps['DummyDefenseAttackStep']
    defense_step_node = attack_graph.add_node(defense_step_type)
    defense_step_node.defense_status = False

    # or-node with viable parent -> viable
    or_attack_step_type = dummy_attack_steps['DummyOrAttackStep']
    or_node = attack_graph.add_node(or_attack_step_type)
    or_node_parent = attack_graph.add_node(or_attack_step_type)
    or_node.parents.add(or_node_parent)

    # and-node with no parents -> viable
    and_attack_step_type = dummy_attack_steps['DummyAndAttackStep']
    and_node = attack_graph.add_node(and_attack_step_type)

    # and-node with viable parents -> viable
    and_node2 = attack_graph.add_node(and_attack_step_type)
    and_node_parent1 = attack_graph.add_node(and_attack_step_type)
    and_node_parent2 = attack_graph.add_node(and_attack_step_type)
    and_node2.parents = {and_node_parent1, and_node_parent2}

    # Make sure viable
    apriori.evaluate_viability(exist_node)
    assert exist_node.is_viable
    apriori.evaluate_viability(not_exist_node)
    assert not_exist_node.is_viable
    apriori.evaluate_viability(defense_step_node)
    assert defense_step_node.is_viable
    apriori.evaluate_viability(or_node)
    assert or_node.is_viable
    apriori.evaluate_viability(and_node)
    assert and_node.is_viable
    apriori.evaluate_viability(and_node2)
    assert and_node2.is_viable


def test_viability_unviable_nodes(dummy_lang_graph):
    """Make sure expected unviable nodes are actually unviable"""

    attack_graph = AttackGraph(dummy_lang_graph)
    dummy_attack_steps = dummy_lang_graph.assets['DummyAsset'].attack_steps

    # exists, existance_status = False -> not viable
    exist_attack_step_type = dummy_attack_steps['DummyExistAttackStep']
    exist_node = attack_graph.add_node(exist_attack_step_type)
    exist_node.existence_status = False

    # notExists, existence_status = True -> not viable
    not_exist_attack_step_type = dummy_attack_steps['DummyNotExistAttackStep']
    not_exist_node = attack_graph.add_node(not_exist_attack_step_type)
    not_exist_node.existence_status = True

    # Defense status on -> not viable
    defense_step_type = dummy_attack_steps['DummyDefenseAttackStep']
    defense_step_node = attack_graph.add_node(defense_step_type)
    defense_step_node.defense_status = True

    # or-node with no viable parent -> non viable
    or_attack_step_type = dummy_attack_steps['DummyOrAttackStep']
    or_node = attack_graph.add_node(or_attack_step_type)
    or_node_parent = attack_graph.add_node(or_attack_step_type)
    or_node_parent.is_viable = False
    or_node.parents.add(or_node_parent)

    # and-node with two non-viable parents -> non viable
    and_attack_step_type = dummy_attack_steps['DummyAndAttackStep']
    and_node = attack_graph.add_node(and_attack_step_type)

    and_node_parent1 = attack_graph.add_node(and_attack_step_type)
    and_node_parent1.is_viable = False

    and_node_parent2 = attack_graph.add_node(and_attack_step_type)
    and_node_parent2.is_viable = False

    and_node.parents = {and_node_parent1, and_node_parent2}
    and_node.parents = {and_node_parent1, and_node_parent2}

    # Calculate viability and make sure unviable
    apriori.evaluate_viability(exist_node)
    assert not exist_node.is_viable
    apriori.evaluate_viability(not_exist_node)
    assert not not_exist_node.is_viable
    apriori.evaluate_viability(defense_step_node)
    assert not defense_step_node.is_viable
    apriori.evaluate_viability(or_node)
    assert not or_node.is_viable
    apriori.evaluate_viability(and_node)
    assert not and_node.is_viable


def test_necessity_necessary(dummy_lang_graph):
    """Make sure expected necessary nodes are necessary"""

    attack_graph = AttackGraph(dummy_lang_graph)
    dummy_attack_steps = dummy_lang_graph.assets['DummyAsset'].attack_steps

    # exists node, existance_status = False -> necessary
    exist_attack_step_type = dummy_attack_steps['DummyExistAttackStep']
    exist_node = attack_graph.add_node(exist_attack_step_type)
    exist_node.existence_status = False

    # notExists, existance_status = True -> necessary
    not_exist_attack_step_type = dummy_attack_steps['DummyNotExistAttackStep']
    not_exist_node = attack_graph.add_node(not_exist_attack_step_type)
    not_exist_node.existence_status = True

    # Defense status on -> necessary
    defense_step_type = dummy_attack_steps['DummyDefenseAttackStep']
    defense_step_node = attack_graph.add_node(defense_step_type)
    defense_step_node.defense_status = True

    # or-node with necessary parents -> necessary
    or_attack_step_type = dummy_attack_steps['DummyOrAttackStep']
    or_node = attack_graph.add_node(or_attack_step_type)
    or_node_parent = attack_graph.add_node(or_attack_step_type)
    or_node_parent.is_necessary = True
    or_node.parents.add(or_node_parent)

    # and-node with at least one necessary parents -> necessary
    and_attack_step_type = dummy_attack_steps['DummyAndAttackStep']
    and_node = attack_graph.add_node(and_attack_step_type)

    and_node_parent1 = attack_graph.add_node(and_attack_step_type)
    and_node_parent1.is_necessary = True

    and_node_parent2 = attack_graph.add_node(and_attack_step_type)
    and_node_parent2.is_necessary = False

    and_node.parents = {and_node_parent1, and_node_parent2}
    and_node.parents = {and_node_parent1, and_node_parent2}

    # Calculate necessety and make sure neccessary
    apriori.evaluate_necessity(exist_node)
    assert exist_node.is_necessary
    apriori.evaluate_necessity(not_exist_node)
    assert not_exist_node.is_necessary
    apriori.evaluate_necessity(defense_step_node)
    assert defense_step_node.is_necessary
    apriori.evaluate_necessity(or_node)
    assert or_node.is_necessary
    apriori.evaluate_necessity(and_node)
    assert and_node.is_necessary


# def test_necessity_unnecessary(dummy_lang_graph):
#     """Make sure expected unnecessary nodes are unnecessary"""
#     pass


def test_analyzers_apriori_prune_unviable_and_unnecessary_nodes(
    example_attackgraph: AttackGraph,
):
    # Pick out an or node and make it non-necessary
    node_to_make_non_necessary = next(
        node for node in example_attackgraph.nodes.values() if node.type == 'or'
    )

    node_to_make_non_necessary.is_necessary = False
    prune_unviable_and_unnecessary_nodes(example_attackgraph)

    # Make sure the node was pruned
    assert node_to_make_non_necessary.id not in example_attackgraph.nodes


def test_analyzers_apriori_propagate_viability_from_unviable_node(
    dummy_lang_graph: LanguageGraph,
):
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
    node1 = attack_graph.add_node(lg_attack_step=dummy_defense_attack_step)
    node2 = attack_graph.add_node(lg_attack_step=dummy_or_attack_step)
    node3 = attack_graph.add_node(lg_attack_step=dummy_or_attack_step)
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
