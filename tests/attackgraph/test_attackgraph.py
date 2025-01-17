"""Unit tests for AttackGraph functionality."""

import copy
from unittest.mock import patch

import pytest
from test_model import create_application_asset, create_association

from maltoolbox.attackgraph import Attacker, AttackGraph, AttackGraphNode
from maltoolbox.language import LanguageGraph
from maltoolbox.model import AttackerAttachment, Model


@pytest.fixture
def example_attackgraph(corelang_lang_graph: LanguageGraph, model: Model):
    """Fixture that generates an example attack graph
       with unattached attacker.

    Uses coreLang specification and model with two applications
    with an association and an attacker to create and return
    an AttackGraph object
    """
    # Create 2 assets
    app1 = create_application_asset(model, 'Application 1')
    app2 = create_application_asset(model, 'Application 2')
    model.add_asset(app1)
    model.add_asset(app2)

    # Create association between app1 and app2
    assoc = create_association(model, left_assets=[app1], right_assets=[app2])
    model.add_association(assoc)

    attacker = AttackerAttachment()
    attacker.entry_points = [(app1, ['networkConnectUninspected'])]
    model.add_attacker(attacker)

    return AttackGraph(lang_graph=corelang_lang_graph, model=model)


def test_attackgraph_init(corelang_lang_graph, model) -> None:
    """Test init with different params given."""
    # _generate_graph is called when langspec and model is given to init
    with patch('maltoolbox.attackgraph.AttackGraph._generate_graph') as _generate_graph:
        AttackGraph(lang_graph=corelang_lang_graph, model=model)
        assert _generate_graph.call_count == 1

    # _generate_graph is not called when no langspec or model is given
    with patch('maltoolbox.attackgraph.AttackGraph._generate_graph') as _generate_graph:
        AttackGraph(lang_graph=None, model=None)
        assert _generate_graph.call_count == 0

        AttackGraph(lang_graph=corelang_lang_graph, model=None)
        assert _generate_graph.call_count == 0

        AttackGraph(lang_graph=None, model=model)
        assert _generate_graph.call_count == 0


def attackgraph_save_load_no_model_given(
    example_attackgraph: AttackGraph, attach_attackers: bool
) -> None:
    """Save AttackGraph to a file and load it
    Note: Will create file in /tmp.
    """
    reward = 1
    node_with_reward_before = example_attackgraph.nodes[0]
    node_with_reward_before.extras['reward'] = reward

    if attach_attackers:
        example_attackgraph.attach_attackers()

    # Save the example attack graph to /tmp
    example_graph_path = '/tmp/example_graph.yml'
    example_attackgraph.save_to_file(example_graph_path)

    # Load the attack graph
    loaded_attack_graph = AttackGraph.load_from_file(example_graph_path)
    assert node_with_reward_before.id is not None
    node_with_reward_after = loaded_attack_graph.get_node_by_id(
        node_with_reward_before.id
    )
    assert node_with_reward_after is not None
    assert node_with_reward_after.extras.get('reward') == reward

    # The model will not exist in the loaded attack graph
    assert loaded_attack_graph.model is None

    # Both graphs should have the same nodes
    assert len(example_attackgraph.nodes) == len(loaded_attack_graph.nodes)

    # Loaded graph nodes will not have 'asset' since it does not have a model.
    for loaded_node in loaded_attack_graph.nodes:
        if not isinstance(loaded_node.id, int):
            msg = 'Invalid node id for loaded node.'
            raise ValueError(msg)
        original_node = example_attackgraph.get_node_by_id(loaded_node.id)

        assert original_node, f'Failed to find original node for id {loaded_node.id}.'

        # Convert loaded and original node to dicts
        loaded_node_dict = loaded_node.to_dict()
        original_node_dict = original_node.to_dict()
        for child in original_node_dict['children']:
            child_node = example_attackgraph.get_node_by_id(child)
            assert child_node, f'Failed to find child node for id {child}.'
            original_node_dict['children'][child] = (
                str(child_node.id) + ':' + child_node.name
            )
        for parent in original_node_dict['parents']:
            parent_node = example_attackgraph.get_node_by_id(parent)
            assert parent_node, f'Failed to find parent node for id {parent}.'
            original_node_dict['parents'][parent] = (
                str(parent_node.id) + ':' + parent_node.name
            )

        # Remove key that is not expected to match.
        del original_node_dict['asset']

        # Make sure nodes are the same (except for the excluded keys)
        assert loaded_node_dict == original_node_dict

    for loaded_attacker in loaded_attack_graph.attackers:
        if not isinstance(loaded_attacker.id, int):
            msg = 'Invalid attacker id for loaded attacker.'
            raise ValueError(msg)
        original_attacker = example_attackgraph.get_attacker_by_id(loaded_attacker.id)
        assert (
            original_attacker
        ), f'Failed to find original attacker for id {loaded_attacker.id}.'
        loaded_attacker_dict = loaded_attacker.to_dict()
        original_attacker_dict = original_attacker.to_dict()
        for step in original_attacker_dict['entry_points']:
            attack_step_name = original_attacker_dict['entry_points'][step]
            attack_step_name = str(step) + ':' + attack_step_name.split(':')[-1]
            original_attacker_dict['entry_points'][step] = attack_step_name
        for step in original_attacker_dict['reached_attack_steps']:
            attack_step_name = original_attacker_dict['reached_attack_steps'][step]
            attack_step_name = str(step) + ':' + attack_step_name.split(':')[-1]
            original_attacker_dict['reached_attack_steps'][step] = attack_step_name
        assert loaded_attacker_dict == original_attacker_dict


def test_attackgraph_save_load_no_model_given_without_attackers(
    example_attackgraph: AttackGraph,
) -> None:
    attackgraph_save_load_no_model_given(example_attackgraph, False)


def test_attackgraph_save_load_no_model_given_with_attackers(
    example_attackgraph: AttackGraph,
) -> None:
    attackgraph_save_load_no_model_given(example_attackgraph, True)


def attackgraph_save_and_load_json_yml_model_given(
    example_attackgraph: AttackGraph, attach_attackers: bool
) -> None:
    """Try to save and load attack graph from json and yml with model given,
    and make sure the dict represenation is the same (except for reward field).
    """
    if attach_attackers:
        example_attackgraph.attach_attackers()

    for attackgraph_path in ('/tmp/attackgraph.yml', '/tmp/attackgraph.json'):
        example_attackgraph.save_to_file(attackgraph_path)
        loaded_attackgraph = AttackGraph.load_from_file(
            attackgraph_path, model=example_attackgraph.model
        )

        # Make sure model was 'attached' correctly
        assert loaded_attackgraph.model == example_attackgraph.model

        for node_full_name, loaded_node_dict in loaded_attackgraph._to_dict()[
            'attack_steps'
        ].items():
            original_node_dict = example_attackgraph._to_dict()['attack_steps'][
                node_full_name
            ]

            # Make sure nodes are the same (except for the excluded keys)
            assert loaded_node_dict == original_node_dict

        for node in loaded_attackgraph.nodes:
            # Make sure node gets an asset when loaded with model
            assert node.asset
            assert node.full_name == node.asset.name + ':' + node.name

            # Make sure node was added to lookup dict with correct id / name
            assert node.id is not None
            assert loaded_attackgraph.get_node_by_id(node.id) == node
            assert loaded_attackgraph.get_node_by_full_name(node.full_name) == node

        for loaded_attacker in loaded_attackgraph.attackers:
            if not isinstance(loaded_attacker.id, int):
                msg = 'Invalid attacker id for loaded attacker.'
                raise ValueError(msg)
            original_attacker = example_attackgraph.get_attacker_by_id(
                loaded_attacker.id
            )
            assert original_attacker, (
                'Failed to find original attacker for id ' '{loaded_attacker.id}.'
            )
            loaded_attacker_dict = loaded_attacker.to_dict()
            original_attacker_dict = original_attacker.to_dict()
            assert loaded_attacker_dict == original_attacker_dict


def test_attackgraph_save_and_load_json_yml_model_given_without_attackers(
    example_attackgraph: AttackGraph,
) -> None:
    attackgraph_save_and_load_json_yml_model_given(example_attackgraph, False)


def test_attackgraph_save_and_load_json_yml_model_given_with_attackers(
    example_attackgraph: AttackGraph,
) -> None:
    attackgraph_save_and_load_json_yml_model_given(example_attackgraph, True)


def test_attackgraph_get_node_by_id(example_attackgraph: AttackGraph) -> None:
    """Make sure get_node_by_id works as intended."""
    assert len(example_attackgraph.nodes)  # make sure loop is run
    for node in example_attackgraph.nodes:
        if not isinstance(node.id, int):
            msg = 'Invalid node id.'
            raise ValueError(msg)
        get_node = example_attackgraph.get_node_by_id(node.id)
        assert get_node == node


def test_attackgraph_attach_attackers(example_attackgraph: AttackGraph) -> None:
    """Make sure attackers are properly attached to graph."""
    app1_ncu = example_attackgraph.get_node_by_full_name(
        'Application 1:networkConnectUninspected'
    )
    app1_auv = example_attackgraph.get_node_by_full_name(
        'Application 1:attemptUseVulnerability'
    )

    assert app1_ncu
    assert app1_auv

    assert not example_attackgraph.attackers

    example_attackgraph.attach_attackers()

    assert len(example_attackgraph.attackers) == 1
    attacker = example_attackgraph.attackers[0]

    assert app1_ncu in attacker.entry_points
    assert app1_ncu in attacker.reached_attack_steps
    assert app1_auv not in attacker.entry_points
    assert app1_auv not in attacker.reached_attack_steps

    attacker.compromise(app1_auv)
    assert app1_auv in attacker.reached_attack_steps
    assert app1_auv not in attacker.entry_points

    for node in attacker.reached_attack_steps:
        # Make sure the Attacker is present on the nodes they have compromised
        assert attacker in node.compromised_by


def test_attackgraph_generate_graph(example_attackgraph: AttackGraph) -> None:
    """Make sure the graph is correctly generated from model and lang."""
    # TODO: Add test cases with defense steps

    # Empty the attack graph
    example_attackgraph.nodes = []
    example_attackgraph.attackers = []

    # Generate the attack graph again
    example_attackgraph._generate_graph()

    # Calculate how many nodes we should expect
    num_assets_attack_steps = 0
    assert example_attackgraph.model
    for asset in example_attackgraph.model.assets:
        attack_steps = example_attackgraph.lang_graph._get_attacks_for_asset_type(
            asset.type
        )
        num_assets_attack_steps += len(attack_steps)

    # Each attack step will get one node
    assert len(example_attackgraph.nodes) == num_assets_attack_steps


def test_attackgraph_according_to_corelang(corelang_lang_graph, model) -> None:
    """Looking at corelang .mal file, make sure the resulting
    AttackGraph contains expected nodes.
    """
    # Create 2 assets
    app1 = create_application_asset(model, 'Application 1')
    app2 = create_application_asset(model, 'Application 2')
    model.add_asset(app1)
    model.add_asset(app2)

    # Create association between app1 and app2
    assoc = create_association(model, left_assets=[app1], right_assets=[app2])
    model.add_association(assoc)
    attack_graph = AttackGraph(lang_graph=corelang_lang_graph, model=model)

    # These are all attack 71 steps and defenses for Application asset in MAL
    expected_node_names_application = [
        'notPresent',
        'attemptUseVulnerability',
        'successfulUseVulnerability',
        'useVulnerability',
        'attemptReverseReach',
        'successfulReverseReach',
        'reverseReach',
        'localConnect',
        'networkConnectUninspected',
        'networkConnectInspected',
        'networkConnect',
        'specificAccessNetworkConnect',
        'accessNetworkAndConnections',
        'attemptNetworkConnectFromResponse',
        'networkConnectFromResponse',
        'specificAccessFromLocalConnection',
        'specificAccessFromNetworkConnection',
        'specificAccess',
        'bypassContainerization',
        'authenticate',
        'specificAccessAuthenticate',
        'localAccess',
        'networkAccess',
        'fullAccess',
        'physicalAccessAchieved',
        'attemptUnsafeUserActivity',
        'successfulUnsafeUserActivity',
        'unsafeUserActivity',
        'attackerUnsafeUserActivityCapability',
        'attackerUnsafeUserActivityCapabilityWithReverseReach',
        'attackerUnsafeUserActivityCapabilityWithoutReverseReach',
        'supplyChainAuditing',
        'bypassSupplyChainAuditing',
        'supplyChainAuditingBypassed',
        'attemptFullAccessFromSupplyChainCompromise',
        'fullAccessFromSupplyChainCompromise',
        'attemptReadFromSoftProdVulnerability',
        'attemptModifyFromSoftProdVulnerability',
        'attemptDenyFromSoftProdVulnerability',
        'softwareCheck',
        'softwareProductVulnerabilityLocalAccessAchieved',
        'softwareProductVulnerabilityNetworkAccessAchieved',
        'softwareProductVulnerabilityPhysicalAccessAchieved',
        'softwareProductVulnerabilityLowPrivilegesAchieved',
        'softwareProductVulnerabilityHighPrivilegesAchieved',
        'softwareProductVulnerabilityUserInteractionAchieved',
        'attemptSoftwareProductAbuse',
        'softwareProductAbuse',
        'readFromSoftProdVulnerability',
        'modifyFromSoftProdVulnerability',
        'denyFromSoftProdVulnerability',
        'attemptApplicationRespondConnectThroughData',
        'successfulApplicationRespondConnectThroughData',
        'applicationRespondConnectThroughData',
        'attemptAuthorizedApplicationRespondConnectThroughData',
        'successfulAuthorizedApplicationRespondConnectThroughData',
        'authorizedApplicationRespondConnectThroughData',
        'attemptRead',
        'successfulRead',
        'read',
        'specificAccessRead',
        'attemptModify',
        'successfulModify',
        'modify',
        'specificAccessModify',
        'attemptDeny',
        'successfulDeny',
        'deny',
        'specificAccessDelete',
        'denyFromNetworkingAsset',
        'denyFromLockout',
    ]

    # Make sure the nodes in the AttackGraph have the expected names and order
    for i, expected_name in enumerate(expected_node_names_application):
        assert attack_graph.nodes[i].name == expected_name

    # notPresent is a defense step and its children are (according to corelang):
    extected_children_of_not_present = [
        'successfulUseVulnerability',
        'successfulReverseReach',
        'networkConnectFromResponse',
        'specificAccessFromLocalConnection',
        'specificAccessFromNetworkConnection',
        'localAccess',
        'networkAccess',
        'successfulUnsafeUserActivity',
        'fullAccessFromSupplyChainCompromise',
        'readFromSoftProdVulnerability',
        'modifyFromSoftProdVulnerability',
        'denyFromSoftProdVulnerability',
        'successfulApplicationRespondConnectThroughData',
        'successfulAuthorizedApplicationRespondConnectThroughData',
        'successfulRead',
        'successfulModify',
        'successfulDeny',
    ]
    # Make sure children are also added for defense step notPresent
    not_present_children = [n.name for n in attack_graph.nodes[0].children]
    assert not_present_children == extected_children_of_not_present


def test_attackgraph_regenerate_graph() -> None:
    """Make sure graph is regenerated."""


def test_attackgraph_remove_node(example_attackgraph: AttackGraph) -> None:
    """Make sure nodes are removed correctly."""
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


def test_attackgraph_deepcopy(example_attackgraph: AttackGraph) -> None:
    """Try to deepcopy an attackgraph object. The nodes of the attack graph
    and attackers should be duplicated into new objects, while references to
    the instance model should remain the same.
    """
    example_attackgraph.attach_attackers()
    copied_attackgraph: AttackGraph = copy.deepcopy(example_attackgraph)

    assert copied_attackgraph != example_attackgraph
    assert copied_attackgraph._to_dict() == example_attackgraph._to_dict()

    assert copied_attackgraph.next_node_id == example_attackgraph.next_node_id
    assert copied_attackgraph.next_attacker_id == example_attackgraph.next_attacker_id

    assert len(copied_attackgraph.nodes) == len(example_attackgraph.nodes)

    assert list(copied_attackgraph._id_to_node.keys()) == list(
        example_attackgraph._id_to_node.keys()
    )

    assert list(copied_attackgraph._id_to_attacker.keys()) == list(
        example_attackgraph._id_to_attacker.keys()
    )

    assert list(copied_attackgraph._full_name_to_node.keys()) == list(
        example_attackgraph._full_name_to_node.keys()
    )

    assert id(copied_attackgraph.model) == id(example_attackgraph.model)

    assert len(copied_attackgraph.nodes) == len(example_attackgraph.nodes)

    for node in copied_attackgraph.nodes:
        assert node.id is not None
        original_node = example_attackgraph.get_node_by_id(node.id)

        assert original_node
        assert id(original_node) != id(node)
        assert original_node.to_dict() == node.to_dict()
        assert id(original_node.asset) == id(node.asset)

        # Make sure thes node in the copied attack graph are the same
        same_node = copied_attackgraph.get_node_by_id(node.id)
        assert id(same_node) == id(node)

        for attacker in node.compromised_by:
            assert id(attacker) == id(copied_attackgraph.attackers[0])
            original_node.compromised_by

    # Make sure parents and children are same as those in the copied attack graph
    for node in copied_attackgraph.nodes:
        for parent in node.parents:
            assert parent.id is not None
            attack_graph_parent = copied_attackgraph.get_node_by_id(parent.id)
            assert id(attack_graph_parent) == id(parent)
        for child in node.children:
            assert child.id is not None
            attack_graph_child = copied_attackgraph.get_node_by_id(child.id)
            assert id(attack_graph_child) == id(child)

    assert len(copied_attackgraph.attackers) == len(example_attackgraph.attackers)
    assert id(copied_attackgraph.attackers) != id(example_attackgraph.attackers)

    for attacker in copied_attackgraph.attackers:
        for entry_point in attacker.entry_points:
            assert entry_point.id
            entry_point_in_attack_graph = copied_attackgraph.get_node_by_id(
                entry_point.id
            )
            assert entry_point_in_attack_graph
            assert entry_point == entry_point_in_attack_graph
            assert id(entry_point) == id(entry_point_in_attack_graph)

        assert attacker.id is not None
        original_attacker = example_attackgraph.get_attacker_by_id(attacker.id)
        assert original_attacker
        assert id(original_attacker) != id(attacker)
        assert original_attacker.to_dict() == attacker.to_dict()


def test_attackgraph_deepcopy_attackers(example_attackgraph: AttackGraph) -> None:
    """Make sure attackers entry points and reached steps are copied correctly."""
    example_attackgraph.attach_attackers()

    original_attacker = example_attackgraph.attackers[0]
    for reached in original_attacker.reached_attack_steps:
        assert reached.id
        node = example_attackgraph.get_node_by_id(reached.id)
        assert node
        assert id(node) == id(reached)

    for entrypoint in original_attacker.entry_points:
        assert entrypoint.id
        node = example_attackgraph.get_node_by_id(entrypoint.id)
        assert node
        assert id(node) == id(entrypoint)

    copied_attackgraph = copy.deepcopy(example_attackgraph)
    copied_attacker = copied_attackgraph.attackers[0]
    for reached in copied_attacker.reached_attack_steps:
        assert reached.id
        node = copied_attackgraph.get_node_by_id(reached.id)
        assert node
        assert id(node) == id(reached)

    for entrypoint in copied_attacker.entry_points:
        assert entrypoint.id
        node = copied_attackgraph.get_node_by_id(entrypoint.id)
        assert node
        assert id(node) == id(entrypoint)


def test_deepcopy_memo_test(example_attackgraph: AttackGraph) -> None:
    """Make sure memo is filled up with expected number of objects."""
    example_attackgraph.attach_attackers()
    memo: dict = {}

    # Deep copy nodes
    copied_nodes = copy.deepcopy(example_attackgraph.nodes, memo)

    # Make sure memo contains all of the nodes
    memo_nodes = [o for o in memo.values() if isinstance(o, AttackGraphNode)]
    assert len(copied_nodes) == len(memo_nodes) == len(example_attackgraph.nodes)

    # Deep copy attackers
    copied_attackers = copy.deepcopy(example_attackgraph.attackers, memo)

    # Make sure memo stored all of the attackers
    memo_attackers = [o for o in memo.values() if isinstance(o, Attacker)]
    assert (
        len(copied_attackers)
        == len(memo_attackers)
        == len(example_attackgraph.attackers)
    )

    # Make sure memo didn't store any new nodes
    memo_nodes = [o for o in memo.values() if isinstance(o, AttackGraphNode)]
    assert len(memo_nodes) == len(example_attackgraph.nodes)
