"""Unit tests for AttackGraph functionality"""

import pytest
from unittest.mock import patch

from maltoolbox.attackgraph import AttackGraph
from maltoolbox.model import Model, AttackerAttachment

from test_model import create_application_asset, create_association


@pytest.fixture
def example_attackgraph(corelang_spec, model: Model):
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
    assoc = create_association(model, from_assets=[app1], to_assets=[app2])
    model.add_association(assoc)

    attacker = AttackerAttachment()
    attacker.entry_points = [
        (app1, ['attemptCredentialsReuse'])
    ]
    model.add_attacker(attacker)

    return AttackGraph(lang_spec=corelang_spec, model=model)


def test_attackgraph_init(corelang_spec, model):
    """Test init with different params given"""

    # _generate_graph is called when langspec and model is given to init
    with patch("maltoolbox.attackgraph.AttackGraph._generate_graph")\
         as _generate_graph:
        AttackGraph(lang_spec=corelang_spec, model=model)
        assert _generate_graph.call_count == 1

    # _generate_graph is not called when no langspec or model is given
    with patch("maltoolbox.attackgraph.AttackGraph._generate_graph")\
        as _generate_graph:
        AttackGraph(lang_spec=None, model=None)
        assert _generate_graph.call_count == 0

        AttackGraph(lang_spec=corelang_spec, model=None)
        assert _generate_graph.call_count == 0

        AttackGraph(lang_spec=None, model=model)
        assert _generate_graph.call_count == 0


def test_attackgraph_save_load(example_attackgraph: AttackGraph):
    """Save AttackGraph to a file and load it
    Note: Will create file in /tmp"""

    # Save the example attack graph to /tmp
    example_graph_path = "/tmp/example_graph.txt"
    example_attackgraph.save_to_file(example_graph_path)

    # Load the attack graph
    loaded_attack_graph = AttackGraph()
    loaded_attack_graph.load_from_file(example_graph_path)

    # The model will not exist in the loaded attack graph
    assert loaded_attack_graph.model is None

    # Both graphs should have the same nodes
    assert len(example_attackgraph.nodes) == len(loaded_attack_graph.nodes)

    # Loaded graph nodes will not have 'asset' since it does not have a model.
    # Loaded graph nodes will have a 'reward' attribute which original
    # nodes does not, otherwise they should be the same
    for i, loaded_node in enumerate(loaded_attack_graph.nodes):
        original_node = example_attackgraph.nodes[i]

        # Convert loaded and original node to dicts
        loaded_node_dict = loaded_node.to_dict()
        original_node_dict = original_node.to_dict()
        # Remove keys that don't match
        del original_node_dict['asset']
        del loaded_node_dict['reward']

        # Make sure nodes are the same (except for the excluded keys)
        assert loaded_node_dict == original_node_dict


def test_attackgraph_get_node_by_id(example_attackgraph: AttackGraph):
    """Make sure get_node_by_id works as intended"""
    assert len(example_attackgraph.nodes)  # make sure loop is run
    for node in example_attackgraph.nodes:
        get_node = example_attackgraph.get_node_by_id(node.id)
        assert get_node == node


def test_attackgraph_attach_attackers(example_attackgraph: AttackGraph):
    """Make sure attackers are attached to graph"""

    nodes_before = list(example_attackgraph.nodes)
    # TODO: Should we use self.model in attach_attackers instead?
    example_attackgraph.attach_attackers(example_attackgraph.model)
    nodes_after = list(example_attackgraph.nodes)

    # An attacker node should be added
    assert len(nodes_after) == len(nodes_before) + 1

    # Make sure the Attacker node has correct ID
    attacker_node = nodes_after[-1]
    attacker_asset_id = example_attackgraph.model.attackers[0].id
    assert attacker_node.id == \
        f"Attacker:{attacker_asset_id}:{attacker_node.name}"

def test_attackgraph_generate_graph(example_attackgraph: AttackGraph):
    """Make sure the graph is correctly generated from model and lang"""
    # TODO: Add test cases with defense steps

    from maltoolbox.language import specification

    # Empty the attack graph
    example_attackgraph.nodes = []
    example_attackgraph.attackers = []

    # Generate the attack graph again
    example_attackgraph._generate_graph()

    # Calculate how many nodes we should expect
    num_assets_attack_steps = 0
    for asset in example_attackgraph.model.assets:
        attack_steps = specification.get_attacks_for_class(
            example_attackgraph.lang_spec, asset.metaconcept)
        num_assets_attack_steps += len(attack_steps)

    # Each attack step will get one node
    assert len(example_attackgraph.nodes) == num_assets_attack_steps

def test_attackgraph_regenerate_graph():
    """Make sure graph is regenerated"""
    pass  # we don't have to test this atm tbh plz


def test_attackgraph_remove_node(example_attackgraph: AttackGraph):
    """Make sure nodes are removed correctly"""
    node_to_remove = example_attackgraph.nodes[10]
    parents = list(node_to_remove.parents)
    children = list(node_to_remove.children)
    example_attackgraph.remove_node(node_to_remove)

    # Make sure it was correctly removed from list of nodes
    assert node_to_remove not in example_attackgraph.nodes

    # Make sure it was correctly removed from parent and children references
    for parent in parents:
        assert node_to_remove not in parent.children
    for child in children:
        assert node_to_remove not in child.parents

    # Make sure references were rewritten to merge parents with children
    ## TODO: Is it expected behaviour that this test fails?
    # for child in children:
    #     for parent in parents:
    #         assert child in parent.children
    #         assert parent in child.parents


def test_attackgraph_process_step_expression():
    """"""
    pass
