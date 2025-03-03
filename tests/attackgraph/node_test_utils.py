from maltoolbox.attackgraph import AttackGraph, Attacker
from maltoolbox.attackgraph.analyzers import apriori

def add_viable_and_node(attack_graph: AttackGraph):
    """and-node with viable parents -> viable"""
    dummy_attack_steps = (
        attack_graph.lang_graph.assets['DummyAsset'].attack_steps
    )

    and_node = attack_graph.add_node(dummy_attack_steps['DummyAndAttackStep'])
    and_node.existence_status = True

    and_node_parent1 = (
        attack_graph.add_node(dummy_attack_steps['DummyOrAttackStep'])
    )
    and_node_parent1.children={and_node}
    and_node_parent2 = (
        attack_graph.add_node(dummy_attack_steps['DummyOrAttackStep'])
    )
    and_node_parent2.children={and_node}

    and_node.parents = {and_node_parent1, and_node_parent2}
    apriori.evaluate_viability(and_node)
    return and_node


def add_viable_or_node(attack_graph: AttackGraph):
    """or-node with viable parent -> viable"""
    dummy_attack_steps = (
        attack_graph.lang_graph.assets['DummyAsset'].attack_steps
    )

    or_node = attack_graph.add_node(
        dummy_attack_steps['DummyOrAttackStep'])
    or_node_parent = attack_graph.add_node(
        dummy_attack_steps['DummyOrAttackStep'])
    or_node_parent.children = {or_node}
    or_node.parents = {or_node_parent}
    apriori.evaluate_viability(or_node)
    return or_node


def add_traversable_and_node(attack_graph):
    """Add traversable and node to AG"""
    attacker = Attacker('Attacker1')

    # Viable and-node where all necessary parents are compromised
    viable_and_node = add_viable_and_node(attack_graph)
    for parent in viable_and_node.parents:
        parent.is_necessary = True
        attacker.compromise(parent)
    return viable_and_node


def add_non_viable_and_node(attack_graph):
    """and-node with two non-viable parents -> non viable"""
    dummy_attack_steps = (
        attack_graph.lang_graph.assets['DummyAsset'].attack_steps
    )

    and_node = attack_graph.add_node(dummy_attack_steps['DummyAndAttackStep'])
    and_node.existence_status = True

    and_node_parent1 = (
        attack_graph.add_node(dummy_attack_steps['DummyOrAttackStep'])
    )
    and_node_parent1.children={and_node}
    and_node_parent1.is_viable = False

    and_node_parent2 = (
        attack_graph.add_node(dummy_attack_steps['DummyOrAttackStep'])
    )
    and_node_parent2.children={and_node}
    and_node_parent2.is_viable = False
    and_node.parents = [and_node_parent1, and_node_parent2]
    apriori.evaluate_viability(and_node)

    return and_node


def add_non_viable_or_node(attack_graph):
    """or-node with no viable parent -> non viable"""
    dummy_attack_steps = (
        attack_graph.lang_graph.assets['DummyAsset'].attack_steps
    )

    or_node = attack_graph.add_node(
        dummy_attack_steps['DummyOrAttackStep'])
    or_node_parent = attack_graph.add_node(
        dummy_attack_steps['DummyOrAttackStep'])
    or_node_parent.children = {or_node}
    or_node.parents = {or_node_parent}
    apriori.evaluate_viability(or_node)
    return or_node
