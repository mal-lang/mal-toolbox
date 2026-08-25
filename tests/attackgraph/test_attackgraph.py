"""Unit tests for AttackGraph functionality"""

import copy
import pickle
from unittest.mock import patch

import pytest
from conftest import path_testdata

from maltoolbox.attackgraph import AttackGraph, AttackGraphNode, create_attack_graph
from maltoolbox.language import LanguageGraph
from maltoolbox.language.compiler import MalCompiler
from maltoolbox.language.language_graph_lookup import get_attacks_for_asset_type
from maltoolbox.model import Model


def check_graph_equivalence(true: AttackGraph, other: AttackGraph) -> None:
    """Helper function to check that two graphs are equivalent in terms of nodes and their relationships."""
    assert len(true.nodes) == len(other.nodes), (
        f'Number of nodes differ: True AttackGraph {len(true.nodes)} != Other: {len(other.nodes)}'
    )

    true_full_names = set(true.full_name_to_node.keys())
    other_full_names = set(other.full_name_to_node.keys())
    assert true_full_names == other_full_names, (
        f'Node full_names differ: '
        f'only in true: {true_full_names - other_full_names}; '
        f'only in other: {other_full_names - true_full_names}'
    )

    true_node_id_to_full_name = {node.id: node.full_name for node in true.nodes.values()}
    other_node_id_to_full_name = {node.id: node.full_name for node in other.nodes.values()}

    for true_node_full_name, true_node in true.full_name_to_node.items():
        try:
            part_node = other.full_name_to_node[true_node_full_name]
        except LookupError:
            pytest.fail(
                reason=f'{true_node.full_name} not in partially regenerated graph.'
            )
        true_node_child_names = {true_node_id_to_full_name[node.id] for node in true_node.children}
        part_node_child_names = {other_node_id_to_full_name[node.id] for node in part_node.children}
        assert true_node_child_names == part_node_child_names, (
            f'Different children between true and partially regenerated graphs for {true_node.full_name}'
        )
        true_node_parent_names = {true_node_id_to_full_name[node.id] for node in true_node.parents}
        part_node_parent_names = {other_node_id_to_full_name[node.id] for node in part_node.parents}
        assert true_node_parent_names == part_node_parent_names, (
            f'Different parents between true and partially regenerated graphs for {true_node.full_name}'
        )



def test_attackgraph_init(corelang_lang_graph, model):
    """Test init with different params given"""
    # _generate_graph is called when langspec and model is given to init
    with patch('maltoolbox.attackgraph.attackgraph.generate_graph') as _generate_graph:
        _generate_graph.return_value = None, None, None, None, None
        AttackGraph(lang_graph=corelang_lang_graph, model=model)
        assert _generate_graph.call_count == 1

    # _generate_graph is not called when no model is given
    with patch('maltoolbox.attackgraph.attackgraph.generate_graph') as _generate_graph:
        AttackGraph(lang_graph=corelang_lang_graph, model=None)
        assert _generate_graph.call_count == 0


def test_load_attack_graph(corelang_lang_graph: LanguageGraph):
    """Make sure we can load attack graphs"""
    json_ag = path_testdata('attackgraph.json')
    yml_ag = path_testdata('attackgraph.yml')

    loaded_json_ag = AttackGraph.load_from_file(json_ag, corelang_lang_graph)
    loaded_yml_ag = AttackGraph.load_from_file(yml_ag, corelang_lang_graph)
    assert loaded_json_ag._to_dict() == loaded_yml_ag._to_dict()

    for step in loaded_json_ag.nodes.values():
        # Make sure exist status gets correct type
        if step.type == 'exist':
            assert step.existence_status is None or isinstance(
                step.existence_status, bool
            )

    for step in loaded_yml_ag.nodes.values():
        # Make sure exist status gets correct type
        if step.type == 'exist':
            assert step.existence_status is None or isinstance(
                step.existence_status, bool
            )


def test_attackgraph_save_load_no_model_given(
    example_attackgraph: AttackGraph, corelang_lang_graph: LanguageGraph
):
    """Save AttackGraph to a file and load it
    Note: Will create file in /tmp
    """
    reward = 1
    node_with_reward_before = example_attackgraph.nodes[0]
    node_with_reward_before.extras['reward'] = reward

    # Save the example attack graph to /tmp
    example_graph_path = '/tmp/example_graph.yml'
    example_attackgraph.save_to_file(example_graph_path)

    # Load the attack graph
    loaded_attack_graph = AttackGraph.load_from_file(
        example_graph_path, corelang_lang_graph
    )
    assert node_with_reward_before.id is not None
    node_with_reward_after = loaded_attack_graph.nodes[node_with_reward_before.id]
    assert node_with_reward_after is not None
    assert node_with_reward_after.extras.get('reward') == reward

    # The model will not exist in the loaded attack graph
    assert loaded_attack_graph.model is None

    # Both graphs should have the same nodes
    assert len(example_attackgraph.nodes) == len(loaded_attack_graph.nodes)

    # Loaded graph nodes will not have 'asset' since it does not have a model.
    for loaded_node in loaded_attack_graph.nodes.values():
        if not isinstance(loaded_node.id, int):
            raise TypeError('Invalid node id for loaded node.')
        original_node = example_attackgraph.nodes[loaded_node.id]

        assert original_node, f'Failed to find original node for id {loaded_node.id}.'

        # Convert loaded and original node to dicts
        loaded_node_dict = loaded_node.to_dict()
        original_node_dict = original_node.to_dict()
        for child in original_node_dict['children']:
            child_node = example_attackgraph.nodes[child]
            assert child_node, f'Failed to find child node for id {child}.'
        for parent in original_node_dict['parents']:
            parent_node = example_attackgraph.nodes[parent]
            assert parent_node, f'Failed to find parent node for id {parent}.'

        # Remove key that is not expected to match.
        del original_node_dict['asset']

        # Make sure nodes are the same (except for the excluded keys)
        assert loaded_node_dict == original_node_dict


def test_attackgraph_save_and_load_json_yml_model_given(
    example_attackgraph: AttackGraph, corelang_lang_graph: LanguageGraph
):
    """Try to save and load attack graph from json and yml with model given,
    and make sure the dict represenation is the same (except for reward field)
    """
    for attackgraph_path in ('/tmp/attackgraph.yml', '/tmp/attackgraph.json'):
        example_attackgraph.save_to_file(attackgraph_path)
        loaded_attackgraph = AttackGraph.load_from_file(
            attackgraph_path, corelang_lang_graph, model=example_attackgraph.model
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

        for node in loaded_attackgraph.nodes.values():
            # Make sure node gets an asset when loaded with model
            assert node.model_asset
            assert node.full_name == node.model_asset.name + ':' + node.name

            # Make sure node was added to lookup dict with correct id / name
            assert node.id is not None
            assert loaded_attackgraph.nodes[node.id] == node
            assert loaded_attackgraph.get_node_by_full_name(node.full_name) == node


def test_attackgraph_generate_graph(example_attackgraph: AttackGraph):
    """Make sure the graph is correctly generated from model and lang"""
    # TODO: Add test cases with defense steps

    # Empty the attack graph
    example_attackgraph.nodes = {}

    # Generate the attack graph again
    example_attackgraph.regenerate_graph()

    # Calculate how many nodes we should expect
    num_assets_attack_steps = 0
    assert example_attackgraph.model
    for asset in example_attackgraph.model.assets.values():
        attack_steps = get_attacks_for_asset_type(
            asset.type, example_attackgraph.lang_graph.lang_spec
        )
        num_assets_attack_steps += len(attack_steps)

    # Each attack step will get one node
    assert len(example_attackgraph.nodes) == num_assets_attack_steps


def test_attackgraph_get_node_by_full_name(example_attackgraph: AttackGraph):

    with pytest.raises(LookupError) as e:
        example_attackgraph.get_node_by_full_name('Application 2')
    assert repr(e) == (
        "<ExceptionInfo LookupError('Could not find node with name "
        '"Application 2". Did you mean: '
        "Application 2:read, Application 2:deny?') tblen=3>"
    )


def test_attackgraph_according_to_corelang(corelang_lang_graph, model):
    """Looking at corelang .mal file, make sure the resulting
    AttackGraph contains expected nodes
    """
    # Create 2 assets
    app1 = model.add_asset(asset_type='Application')
    app2 = model.add_asset(asset_type='Application')

    # Create association between app1 and app2
    app1.add_associated_assets(fieldname='appExecutedApps', assets={app2})
    attack_graph = AttackGraph(lang_graph=corelang_lang_graph, model=model)

    # These are all attack 71 steps and defenses for Application asset in MAL
    expected_node_names_application = {
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
    }

    # Make sure the nodes in the AttackGraph have the expected names
    app_attack_steps_names = {
        attack_step.name for attack_step in attack_graph.nodes.values()
    }
    assert app_attack_steps_names == expected_node_names_application

    # notPresent is a defense step and its children are (according to corelang):
    expected_children_of_notpresent = {
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
    }
    # Make sure children are also added for defense step notPresent
    notpresent_attack_step = attack_graph.nodes[0]
    notpresent_children_names = {
        attack_step.name for attack_step in notpresent_attack_step.children
    }
    assert notpresent_children_names == expected_children_of_notpresent


def test_attackgraph_remove_node(example_attackgraph: AttackGraph):
    """Make sure nodes are removed correctly"""
    node_to_remove = example_attackgraph.nodes[10]
    parents = list(node_to_remove.parents)
    children = list(node_to_remove.children)
    example_attackgraph.remove_node(node_to_remove)

    # Make sure it was correctly removed from list of nodes
    assert node_to_remove not in example_attackgraph.nodes.values()

    # Make sure it was correctly removed from parent and children references
    for parent in parents:
        assert node_to_remove not in parent.children
    for child in children:
        assert node_to_remove not in child.parents


def test_attackgraph_deepcopy(example_attackgraph: AttackGraph):
    """Try to deepcopy an attackgraph object. The nodes of the attack graph
    should be duplicated into new objects, while references to the instance
    model should remain the same.
    """
    copied_attackgraph: AttackGraph = copy.deepcopy(example_attackgraph)

    assert copied_attackgraph != example_attackgraph
    assert copied_attackgraph._to_dict() == example_attackgraph._to_dict()

    assert copied_attackgraph.next_node_id == example_attackgraph.next_node_id

    assert len(copied_attackgraph.nodes) == len(example_attackgraph.nodes)

    assert list(copied_attackgraph.nodes.keys()) == list(
        example_attackgraph.nodes.keys()
    )

    assert list(copied_attackgraph.full_name_to_node.keys()) == list(
        example_attackgraph.full_name_to_node.keys()
    )

    assert id(copied_attackgraph.model) == id(example_attackgraph.model)

    assert len(copied_attackgraph.nodes) == len(example_attackgraph.nodes)

    for node in copied_attackgraph.nodes.values():
        assert node.id is not None
        original_node = example_attackgraph.nodes[node.id]

        assert original_node
        assert id(original_node) != id(node)
        assert original_node.to_dict() == node.to_dict()
        assert id(original_node.model_asset) == id(node.model_asset)

        # Make sure thes node in the copied attack graph are the same
        same_node = copied_attackgraph.nodes[node.id]
        assert id(same_node) == id(node)

    # Make sure parents and children are same as those in the copied attack graph
    for node in copied_attackgraph.nodes.values():
        for parent in node.parents:
            assert parent.id is not None
            attack_graph_parent = copied_attackgraph.nodes[parent.id]
            assert id(attack_graph_parent) == id(parent)
        for child in node.children:
            assert child.id is not None
            attack_graph_child = copied_attackgraph.nodes[child.id]
            assert id(attack_graph_child) == id(child)


def test_deepcopy_memo_test(example_attackgraph: AttackGraph):
    """Make sure memo is filled up with expected number of objects"""
    memo: dict = {}

    # Deep copy nodes
    copied_nodes = copy.deepcopy(example_attackgraph.nodes, memo)

    # Make sure memo contains all of the nodes
    memo_nodes = [o for o in memo.values() if isinstance(o, AttackGraphNode)]
    assert len(copied_nodes) == len(memo_nodes) == len(example_attackgraph.nodes)

    # Make sure memo didn't store any new nodes
    memo_nodes = [o for o in memo.values() if isinstance(o, AttackGraphNode)]
    assert len(memo_nodes) == len(example_attackgraph.nodes)


def test_attackgraph_subtype():

    test_lang_graph = LanguageGraph(
        MalCompiler().compile('tests/testdata/subtype_attack_step.mal')
    )
    test_model = Model('Test Model', test_lang_graph)
    # Create assets
    baseasset1 = test_model.add_asset(name='BaseAsset 1', asset_type='BaseAsset')

    subasset1 = test_model.add_asset(name='SubAsset 1', asset_type='SubAsset')

    otherasset1 = test_model.add_asset(name='OtherAsset 1', asset_type='OtherAsset')

    # Create association between subasset1 and otherasset1
    subasset1.add_associated_assets('field2', {otherasset1})
    baseasset1.add_associated_assets('field2', {otherasset1})

    test_attack_graph = AttackGraph(lang_graph=test_lang_graph, model=test_model)
    ba_1_base_step1 = test_attack_graph.get_node_by_full_name('BaseAsset 1:base_step1')
    ba_1_base_step2 = test_attack_graph.get_node_by_full_name('BaseAsset 1:base_step2')
    sa_1_base_step1 = test_attack_graph.get_node_by_full_name('SubAsset 1:base_step1')
    sa_1_base_step2 = test_attack_graph.get_node_by_full_name('SubAsset 1:base_step2')
    sa_1_subasset_step1 = test_attack_graph.get_node_by_full_name(
        'SubAsset 1:subasset_step1'
    )
    oa_1_other_step1 = test_attack_graph.get_node_by_full_name(
        'OtherAsset 1:other_step1'
    )

    assert ba_1_base_step1 in oa_1_other_step1.children
    assert ba_1_base_step2 not in oa_1_other_step1.children
    assert sa_1_base_step1 in oa_1_other_step1.children
    assert sa_1_base_step2 in oa_1_other_step1.children
    assert sa_1_subasset_step1 in oa_1_other_step1.children


def test_attackgraph_setops():

    test_lang_graph = LanguageGraph(MalCompiler().compile('tests/testdata/set_ops.mal'))
    test_model = Model('Test Model', test_lang_graph)

    # Create assets
    set_ops_a1 = test_model.add_asset(asset_type='SO_A', name='SO_A 1')
    set_ops_b1 = test_model.add_asset(asset_type='SO_B', name='SO_B 1')
    set_ops_b2 = test_model.add_asset(asset_type='SO_B', name='SO_B 2')
    set_ops_b3 = test_model.add_asset(asset_type='SO_B', name='SO_B 3')

    # Create association
    set_ops_a1.add_associated_assets('fieldB1', {set_ops_b1, set_ops_b2})

    set_ops_a1.add_associated_assets('fieldB2', {set_ops_b2, set_ops_b3})

    test_attack_graph = AttackGraph(lang_graph=test_lang_graph, model=test_model)

    assetA1_origStep = test_attack_graph.get_node_by_full_name('SO_A 1:originStep')
    assetB1_unionStep = test_attack_graph.get_node_by_full_name('SO_B 1:unionStep')
    assetB1_intersectStep = test_attack_graph.get_node_by_full_name(
        'SO_B 1:intersectionStep'
    )
    assetB1_diffStep = test_attack_graph.get_node_by_full_name('SO_B 1:differenceStep')
    assetB2_unionStep = test_attack_graph.get_node_by_full_name('SO_B 2:unionStep')
    assetB2_intersectStep = test_attack_graph.get_node_by_full_name(
        'SO_B 2:intersectionStep'
    )
    assetB2_diffStep = test_attack_graph.get_node_by_full_name('SO_B 2:differenceStep')
    assetB3_unionStep = test_attack_graph.get_node_by_full_name('SO_B 3:unionStep')
    assetB3_intersectStep = test_attack_graph.get_node_by_full_name(
        'SO_B 3:intersectionStep'
    )
    assetB3_diffStep = test_attack_graph.get_node_by_full_name('SO_B 3:differenceStep')

    assert assetB1_unionStep in assetA1_origStep.children
    assert assetB1_intersectStep not in assetA1_origStep.children
    assert assetB1_diffStep in assetA1_origStep.children
    assert assetB2_unionStep in assetA1_origStep.children
    assert assetB2_intersectStep in assetA1_origStep.children
    assert assetB2_diffStep not in assetA1_origStep.children
    assert assetB3_unionStep in assetA1_origStep.children
    assert assetB3_intersectStep not in assetA1_origStep.children
    assert assetB3_diffStep not in assetA1_origStep.children


def test_attackgraph_setops_adv():

    test_lang_graph = LanguageGraph(
        MalCompiler().compile('tests/testdata/set_ops_adv.mal')
    )
    test_model = Model('Test Model', test_lang_graph)

    # Create assets
    set_ops_a1 = test_model.add_asset(asset_type='SOA_A', name='SOA_A 1')
    set_ops_a2 = test_model.add_asset(asset_type='SOA_A', name='SOA_A 2')
    set_ops_a3 = test_model.add_asset(asset_type='SOA_A', name='SOA_A 3')
    set_ops_b1 = test_model.add_asset(asset_type='SOA_B', name='SOA_B 1')
    set_ops_b2 = test_model.add_asset(asset_type='SOA_B', name='SOA_B 2')
    set_ops_b3 = test_model.add_asset(asset_type='SOA_B', name='SOA_B 3')

    # Create association
    set_ops_a2.add_associated_assets('fieldB1', {set_ops_b1, set_ops_b2})
    set_ops_a3.add_associated_assets('fieldB2', {set_ops_b2, set_ops_b3})
    set_ops_a1.add_associated_assets('fieldA3b', {set_ops_a2, set_ops_a3})

    test_attack_graph = AttackGraph(lang_graph=test_lang_graph, model=test_model)

    assetA1_origInnerStep = test_attack_graph.get_node_by_full_name(
        'SOA_A 1:originInnerStep'
    )
    assetA1_origOuterStep = test_attack_graph.get_node_by_full_name(
        'SOA_A 1:originOuterStep'
    )
    assetB1_intersectStep = test_attack_graph.get_node_by_full_name(
        'SOA_B 1:intersectionStep'
    )
    assetB2_intersectStep = test_attack_graph.get_node_by_full_name(
        'SOA_B 2:intersectionStep'
    )
    assetB3_intersectStep = test_attack_graph.get_node_by_full_name(
        'SOA_B 3:intersectionStep'
    )

    assert assetB1_intersectStep not in assetA1_origInnerStep.children
    assert assetB2_intersectStep not in assetA1_origInnerStep.children
    assert assetB3_intersectStep not in assetA1_origInnerStep.children

    assert assetB1_intersectStep not in assetA1_origOuterStep.children
    assert assetB2_intersectStep in assetA1_origOuterStep.children
    assert assetB3_intersectStep not in assetA1_origOuterStep.children


def test_attackgraph_transitive():
    test_lang_graph = LanguageGraph(
        MalCompiler().compile('tests/testdata/transitive.mal')
    )
    test_model = Model('Test Model', test_lang_graph)

    asset1 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 1')
    asset2 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 2')
    asset3 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 3')
    asset4 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 4')
    asset5 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 5')
    asset6 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 6')

    asset1.add_associated_assets('field2', {asset2})
    asset2.add_associated_assets('field2', {asset3})
    asset3.add_associated_assets('field2', {asset4})
    asset3.add_associated_assets('field2', {asset5})
    asset6.add_associated_assets('field2', {asset1})

    test_attack_graph = AttackGraph(lang_graph=test_lang_graph, model=test_model)

    asset1_test_step = test_attack_graph.get_node_by_full_name('TestAsset 1:test_step')
    asset2_test_step = test_attack_graph.get_node_by_full_name('TestAsset 2:test_step')
    asset3_test_step = test_attack_graph.get_node_by_full_name('TestAsset 3:test_step')
    asset4_test_step = test_attack_graph.get_node_by_full_name('TestAsset 4:test_step')
    asset5_test_step = test_attack_graph.get_node_by_full_name('TestAsset 5:test_step')
    asset6_test_step = test_attack_graph.get_node_by_full_name('TestAsset 6:test_step')

    assert asset1_test_step in asset1_test_step.children
    assert asset2_test_step in asset1_test_step.children
    assert asset3_test_step in asset1_test_step.children
    assert asset4_test_step in asset1_test_step.children
    assert asset5_test_step in asset1_test_step.children
    assert asset6_test_step not in asset1_test_step.children

    assert asset1_test_step not in asset2_test_step.children
    assert asset2_test_step in asset2_test_step.children
    assert asset3_test_step in asset2_test_step.children
    assert asset4_test_step in asset2_test_step.children
    assert asset5_test_step in asset2_test_step.children
    assert asset6_test_step not in asset2_test_step.children

    assert asset1_test_step not in asset3_test_step.children
    assert asset2_test_step not in asset3_test_step.children
    assert asset3_test_step in asset3_test_step.children
    assert asset4_test_step in asset3_test_step.children
    assert asset5_test_step in asset3_test_step.children
    assert asset6_test_step not in asset3_test_step.children

    assert asset1_test_step not in asset4_test_step.children
    assert asset2_test_step not in asset4_test_step.children
    assert asset3_test_step not in asset4_test_step.children
    assert asset4_test_step in asset4_test_step.children
    assert asset5_test_step not in asset4_test_step.children
    assert asset6_test_step not in asset4_test_step.children

    assert asset1_test_step not in asset5_test_step.children
    assert asset2_test_step not in asset5_test_step.children
    assert asset3_test_step not in asset5_test_step.children
    assert asset4_test_step not in asset5_test_step.children
    assert asset5_test_step in asset5_test_step.children
    assert asset6_test_step not in asset5_test_step.children

    assert asset1_test_step in asset6_test_step.children
    assert asset2_test_step in asset6_test_step.children
    assert asset3_test_step in asset6_test_step.children
    assert asset4_test_step in asset6_test_step.children
    assert asset5_test_step in asset6_test_step.children
    assert asset6_test_step in asset6_test_step.children


def test_attackgraph_transitive_advanced():
    # TODO: Improve this test to actually use more complex transitive
    # relationships. Right now it is just the asset and any direct
    # associations it may have.

    test_lang_graph = LanguageGraph(
        MalCompiler().compile('tests/testdata/transitive_advanced.mal')
    )
    test_model = Model('Test Model', test_lang_graph)

    asset1 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 1')
    asset2 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 2')
    asset3 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 3')
    asset4 = test_model.add_asset(asset_type='TestAsset', name='TestAsset 4')

    asset1.add_associated_assets('fieldA2', {asset2, asset3})
    asset1.add_associated_assets('fieldB2', {asset3, asset4})

    test_attack_graph = AttackGraph(lang_graph=test_lang_graph, model=test_model)

    asset1_test_step = test_attack_graph.get_node_by_full_name('TestAsset 1:test_step')
    asset2_test_step = test_attack_graph.get_node_by_full_name('TestAsset 2:test_step')
    asset3_test_step = test_attack_graph.get_node_by_full_name('TestAsset 3:test_step')
    asset4_test_step = test_attack_graph.get_node_by_full_name('TestAsset 4:test_step')

    assert asset1_test_step in asset1_test_step.children
    assert asset2_test_step not in asset1_test_step.children
    assert asset3_test_step in asset1_test_step.children
    assert asset4_test_step not in asset1_test_step.children


def test_create_attack_graph():
    """See that the create attack graph wrapper works"""
    mar = path_testdata('org.mal-lang.coreLang-1.0.0.mar')
    model = path_testdata('simple_example_model.yml')

    # Make sure that it runs without errors
    create_attack_graph(mar, model)


def tests_create_ag_from_model():
    """We have a predefined model in trainingLang with these associations:

    User:3 --- Host:0 --- Network:3 --- Host:1
                 |
                 |
               Data:2
    """

    def check_parent_child_relationship(
        ag: AttackGraph, parent_fn: str, children_fns: list[str]
    ):

        parent = ag.get_node_by_full_name(parent_fn)
        assert parent, f'Could not find node {parent_fn}'

        # Verify that parent has given children
        assert {c.full_name for c in parent.children} == set(children_fns)

        # Verify that child has given parent
        for child_fn in children_fns:
            child = ag.get_node_by_full_name(child_fn)
            assert child, f'Could not find child by full name {child_fn}'
            assert parent_fn in [p.full_name for p in child.parents]

    mar = path_testdata('org.mal-lang.trainingLang-1.0.0.mar')
    model = path_testdata('simple_traininglang_model.yml')

    # Make sure attack graph is created without errors
    created_ag = create_attack_graph(mar, model)

    # Make sure all nodes were generated for the model
    assert {n.full_name for n in created_ag.nodes.values()} == {
        'Host:0:notPresent',
        'Host:0:authenticate',
        'Host:0:connect',
        'Host:0:access',
        'Host:1:notPresent',
        'Host:1:authenticate',
        'Host:1:connect',
        'Host:1:access',
        'Data:2:notPresent',
        'Data:2:read',
        'Data:2:modify',
        'User:3:notPresent',
        'User:3:compromise',
        'User:3:phishing',
        'Network:3:access',
    }

    # Make sure associations were added as parent/child relationships
    check_parent_child_relationship(
        created_ag, 'Host:0:notPresent', ['Host:0:connect', 'Host:0:access']
    )
    check_parent_child_relationship(
        created_ag, 'Host:0:authenticate', ['Host:0:access']
    )
    check_parent_child_relationship(created_ag, 'Host:0:connect', ['Host:0:access'])
    check_parent_child_relationship(
        created_ag,
        'Host:0:access',
        ['Data:2:modify', 'Data:2:read', 'Network:3:access'],
    )
    check_parent_child_relationship(
        created_ag, 'Host:1:notPresent', ['Host:1:connect', 'Host:1:access']
    )
    check_parent_child_relationship(
        created_ag, 'Host:1:authenticate', ['Host:1:access']
    )
    check_parent_child_relationship(created_ag, 'Host:1:connect', ['Host:1:access'])
    check_parent_child_relationship(created_ag, 'Host:1:access', ['Network:3:access'])
    check_parent_child_relationship(
        created_ag, 'Data:2:notPresent', ['Data:2:read', 'Data:2:modify']
    )
    check_parent_child_relationship(created_ag, 'Data:2:read', [])
    check_parent_child_relationship(created_ag, 'Data:2:modify', [])
    check_parent_child_relationship(
        created_ag, 'User:3:notPresent', ['User:3:compromise']
    )
    check_parent_child_relationship(
        created_ag, 'User:3:compromise', ['Host:0:authenticate']
    )
    check_parent_child_relationship(
        created_ag, 'User:3:phishing', ['User:3:compromise']
    )
    check_parent_child_relationship(
        created_ag, 'Network:3:access', ['Host:0:connect', 'Host:1:connect']
    )


def test_partial_regeneration(trainingLang_lang_graph: LanguageGraph) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)

    host0 = model.add_asset(asset_type='Host', name='Host0')
    network.add_associated_assets('hosts', {host0})
    AG.partially_regenerate_graph(
        new_assets={host0}, new_associations={(network, 'hosts', host0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    user0 = model.add_asset(asset_type='User', name='User0')
    host0.add_associated_assets(fieldname='users', assets={user0})
    AG.partially_regenerate_graph(
        new_assets={user0}, new_associations={(host0, 'users', user0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Data [data] * <-- DataOnHosts --> * [hosts] Host
    data0 = model.add_asset(asset_type='Data', name='Data0')
    host0.add_associated_assets(fieldname='data', assets={data0})
    AG.partially_regenerate_graph(
        new_assets={data0}, new_associations={(host0, 'data', data0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Add a second host to the already existing network, this requires
    # relinking of the pre-existing Network:LAN:access node's children.
    host1 = model.add_asset(asset_type='Host', name='Host1')
    network.add_associated_assets('hosts', {host1})
    AG.partially_regenerate_graph(
        new_assets={host1}, new_associations={(network, 'hosts', host1)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Associate the same user with the second host as well, exercising
    # relinking of an existing node (User0:compromise) to a new child.
    host1.add_associated_assets(fieldname='users', assets={user0})
    AG.partially_regenerate_graph(
        new_associations={(host1, 'users', user0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # A second Data asset, this time on Host1, and a second piece of Data
    # added onto Host0 (which already has Data0 associated), covering both
    # a fresh host/data pairing and a host gaining an additional Data child.
    data1 = model.add_asset(asset_type='Data', name='Data1')
    data2 = model.add_asset(asset_type='Data', name='Data2')
    host1.add_associated_assets(fieldname='data', assets={data1})
    host0.add_associated_assets(fieldname='data', assets={data2})
    AG.partially_regenerate_graph(
        new_assets={data1, data2},
        new_associations={(host1, 'data', data1), (host0, 'data', data2)},
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Network [fromNetworks] * <-- InterNetworkConnectivity --> * [toNetworks] Network
    network2 = model.add_asset(asset_type='Network', name='WAN')
    AG.partially_regenerate_graph(new_assets={network2})
    network.add_associated_assets(fieldname='toNetworks', assets={network2})
    AG.partially_regenerate_graph(
        new_associations={(network, 'toNetworks', network2)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Now tear everything back down and check that the partially regenerated graph is equivalent to the newly generated graph.
    network.remove_associated_assets(fieldname='toNetworks', assets={network2})
    AG.partially_regenerate_graph(
        removed_associations={(network, 'toNetworks', network2)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(network2)
    AG.partially_regenerate_graph(removed_assets={network2})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(data1)
    AG.partially_regenerate_graph(removed_assets={data1}, removed_associations={(host1, 'data', data1)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(data2)
    AG.partially_regenerate_graph(removed_assets={data2}, removed_associations={(host0, 'data', data2)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    host1.remove_associated_assets(fieldname='users', assets={user0})
    AG.partially_regenerate_graph(
        removed_associations={(host1, 'users', user0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(host1)
    AG.partially_regenerate_graph(removed_assets={host1}, removed_associations={(network, 'hosts', host1)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    host0.remove_associated_assets(fieldname='data', assets={data0})
    AG.partially_regenerate_graph(
        removed_associations={(host0, 'data', data0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(data0)
    AG.partially_regenerate_graph(removed_assets={data0})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(user0)
    AG.partially_regenerate_graph(removed_assets={user0}, removed_associations={(host0, 'users', user0)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    network.remove_associated_assets(fieldname='hosts', assets={host0})
    AG.partially_regenerate_graph(
        removed_associations={(network, 'hosts', host0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(host0)
    AG.partially_regenerate_graph(removed_assets={host0})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Back down to only the original Network asset.
    assert set(model.assets.values()) == {network}


def test_partial_regeneration_change_model_completely(trainingLang_lang_graph: LanguageGraph) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)

    new_assets = set()
    new_associations = set()

    host0 = model.add_asset(asset_type='Host', name='Host0')
    new_assets.add(host0)
    network.add_associated_assets('hosts', {host0})
    new_associations.add((network, 'hosts', host0))

    user0 = model.add_asset(asset_type='User', name='User0')
    new_assets.add(user0)
    host0.add_associated_assets(fieldname='users', assets={user0})
    new_associations.add((host0, 'users', user0))

    data0 = model.add_asset(asset_type='Data', name='Data0')
    new_assets.add(data0)
    host0.add_associated_assets(fieldname='data', assets={data0})
    new_associations.add((host0, 'data', data0))

    host1 = model.add_asset(asset_type='Host', name='Host1')
    new_assets.add(host1)
    network.add_associated_assets('hosts', {host1})
    new_associations.add((network, 'hosts', host1))

    host1.add_associated_assets(fieldname='users', assets={user0})
    new_associations.add((host1, 'users', user0))

    data1 = model.add_asset(asset_type='Data', name='Data1')
    data2 = model.add_asset(asset_type='Data', name='Data2')
    new_assets.update({data1, data2})
    host1.add_associated_assets(fieldname='data', assets={data1})
    host0.add_associated_assets(fieldname='data', assets={data2})
    new_associations.update({(host1, 'data', data1), (host0, 'data', data2)})

    network2 = model.add_asset(asset_type='Network', name='WAN')
    new_assets.add(network2)
    network.add_associated_assets(fieldname='toNetworks', assets={network2})
    new_associations.add((network, 'toNetworks', network2))

    AG.partially_regenerate_graph(new_assets=new_assets, new_associations=new_associations)
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    removed_assets = set()
    removed_associations = set()
    new_assets.clear()
    new_associations.clear()

    for asset in model.assets.values():
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in list(model.assets.values()):
        if asset != network:
            removed_assets.add(asset)
            model.remove_asset(asset)

    network1 = model.add_asset(asset_type='Network', name='Network1')
    network2 = model.add_asset(asset_type='Network', name='Network2')
    network3 = model.add_asset(asset_type='Network', name='Network3')
    new_assets.update({network1, network2, network3})
    network1.add_associated_assets(fieldname='toNetworks', assets={network2, network3})
    new_associations.update({(network1, 'toNetworks', network2), (network1, 'toNetworks', network3)})
    network.add_associated_assets(fieldname='toNetworks', assets={network1})
    new_associations.add((network, 'toNetworks', network1))

    hostInNetwork = model.add_asset(asset_type='Host', name='HostInNetwork')
    hostInNetwork1 = model.add_asset(asset_type='Host', name='HostInNetwork1')
    hostInNetwork2 = model.add_asset(asset_type='Host', name='HostInNetwork2')
    hostInNetwork3 = model.add_asset(asset_type='Host', name='HostInNetwork3')
    new_assets.update({hostInNetwork, hostInNetwork1, hostInNetwork2, hostInNetwork3})
    network.add_associated_assets(fieldname='hosts', assets={hostInNetwork})
    network1.add_associated_assets(fieldname='hosts', assets={hostInNetwork1})
    network2.add_associated_assets(fieldname='hosts', assets={hostInNetwork2})
    network3.add_associated_assets(fieldname='hosts', assets={hostInNetwork3})
    new_associations.update({(network, 'hosts', hostInNetwork), (network1, 'hosts', hostInNetwork1),
        (network2, 'hosts', hostInNetwork2), (network3, 'hosts', hostInNetwork3)
    })

    dataConnectedToAllHosts = model.add_asset(asset_type='Data', name='DataConnectedToAllHosts')
    new_assets.add(dataConnectedToAllHosts)
    dataConnectedToAllHosts.add_associated_assets(fieldname='hosts', assets={hostInNetwork, hostInNetwork1, hostInNetwork2, hostInNetwork3})

    userFornet0and2 = model.add_asset(asset_type='User', name='UserForNet0and2')
    userFornet1and3 = model.add_asset(asset_type='User', name='UserForNet1and3')
    new_assets.update({userFornet0and2, userFornet1and3})
    userFornet0and2.add_associated_assets(fieldname='hosts', assets={hostInNetwork, hostInNetwork2})
    userFornet1and3.add_associated_assets(fieldname='hosts', assets={hostInNetwork1, hostInNetwork3})
    new_associations.update({(userFornet0and2, 'hosts', hostInNetwork), (userFornet0and2, 'hosts', hostInNetwork2),
        (userFornet1and3, 'hosts', hostInNetwork1), (userFornet1and3, 'hosts', hostInNetwork3)
    })

    AG.partially_regenerate_graph(new_assets=new_assets, new_associations=new_associations, removed_assets=removed_assets, removed_associations=removed_associations)
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)


def test_partial_regeneration_corelang(corelang_lang_graph: LanguageGraph) -> None:
    """Tests partial regeneration of the attack graph for a model in coreLang."""
    model = Model('Test Model', corelang_lang_graph)
    corpnet = model.add_asset(asset_type='Network', name='CorpNet')
    AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)

    # --- Phase 1: incremental build ---

    webapp = model.add_asset(asset_type='Application', name='WebApp')
    corpnet.add_associated_assets('applications', {webapp})
    AG.partially_regenerate_graph(
        new_assets={webapp}, new_associations={(corpnet, 'applications', webapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    webhw = model.add_asset(asset_type='Hardware', name='WebServer')
    webhw.add_associated_assets('sysExecutedApps', {webapp})
    AG.partially_regenerate_graph(
        new_assets={webhw}, new_associations={(webhw, 'sysExecutedApps', webapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    webdata = model.add_asset(asset_type='Data', name='WebAppData')
    webapp.add_associated_assets('containedData', {webdata})
    AG.partially_regenerate_graph(
        new_assets={webdata}, new_associations={(webapp, 'containedData', webdata)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Add a second application to the already existing network, this requires
    # relinking of the pre-existing Network:CorpNet:access node's children.
    dbapp = model.add_asset(asset_type='Application', name='DBApp')
    corpnet.add_associated_assets('applications', {dbapp})
    AG.partially_regenerate_graph(
        new_assets={dbapp}, new_associations={(corpnet, 'applications', dbapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # WebApp executes DBApp (self-referential AppExecution association),
    # exercising relinking of an existing node's (WebApp) children.
    webapp.add_associated_assets('appExecutedApps', {dbapp})
    AG.partially_regenerate_graph(
        new_associations={(webapp, 'appExecutedApps', dbapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Two new assets and three new associations in a single call: DBApp gets
    # its own hardware, which also hosts a second, hardware-only Data asset.
    dbhw = model.add_asset(asset_type='Hardware', name='DBServer')
    dbdata = model.add_asset(asset_type='Data', name='DBData')
    dbhw.add_associated_assets('sysExecutedApps', {dbapp})
    dbhw.add_associated_assets('hostedData', {dbdata})
    dbapp.add_associated_assets('containedData', {dbdata})
    AG.partially_regenerate_graph(
        new_assets={dbhw, dbdata},
        new_associations={
            (dbhw, 'sysExecutedApps', dbapp),
            (dbhw, 'hostedData', dbdata),
            (dbapp, 'containedData', dbdata),
        },
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # IDPS protecting two existing applications at once, i.e. a multi-target
    # association added in a single call.
    netidps = model.add_asset(asset_type='IDPS', name='NetIDPS')
    netidps.add_associated_assets('protectedApps', {webapp, dbapp})
    AG.partially_regenerate_graph(
        new_assets={netidps},
        new_associations={
            (netidps, 'protectedApps', webapp),
            (netidps, 'protectedApps', dbapp),
        },
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Identity/Credentials/User chain plus an IAM read privilege, all new at once.
    svcidentity = model.add_asset(asset_type='Identity', name='SvcIdentity')
    svccreds = model.add_asset(asset_type='Credentials', name='SvcCreds')
    alice = model.add_asset(asset_type='User', name='Alice')
    svcidentity.add_associated_assets('credentials', {svccreds})
    alice.add_associated_assets('userIds', {svcidentity})
    svcidentity.add_associated_assets('readPrivData', {webdata})
    AG.partially_regenerate_graph(
        new_assets={svcidentity, svccreds, alice},
        new_associations={
            (svcidentity, 'credentials', svccreds),
            (alice, 'userIds', svcidentity),
            (svcidentity, 'readPrivData', webdata),
        },
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # --- Phase 2: change model (almost) completely ---
    # Tear everything down except CorpNet, then rebuild a bigger topology:
    # three networks linked pairwise via ConnectionRule assets, each with its
    # own application/hardware/data, plus a second IAM chain and an IDPS
    # protecting two apps at once. CorpNet's 'applications' field is both
    # relieved of WebApp/DBApp and given a new ProxyApp in the same call,
    # which is exactly the "same fieldname sees both an addition and a
    # removal in one partial_regenerate_graph call" case that previously
    # broke partial regeneration for trainingLang.

    removed_assets = set()
    removed_associations = set()
    for asset in model.assets.values():
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in list(model.assets.values()):
        if asset != corpnet:
            removed_assets.add(asset)
            model.remove_asset(asset)

    new_assets = set()
    new_associations = set()

    dmz = model.add_asset(asset_type='Network', name='DMZ')
    backup = model.add_asset(asset_type='Network', name='BackupNet')
    new_assets.update({dmz, backup})

    cr1 = model.add_asset(asset_type='ConnectionRule', name='CR-CorpNet-DMZ')
    cr2 = model.add_asset(asset_type='ConnectionRule', name='CR-DMZ-Backup')
    new_assets.update({cr1, cr2})
    cr1.add_associated_assets('networks', {corpnet, dmz})
    cr2.add_associated_assets('networks', {dmz, backup})
    new_associations.update({
        (cr1, 'networks', corpnet), (cr1, 'networks', dmz),
        (cr2, 'networks', dmz), (cr2, 'networks', backup),
    })

    proxyapp = model.add_asset(asset_type='Application', name='ProxyApp')
    dmzapp = model.add_asset(asset_type='Application', name='DmzApp')
    backupapp = model.add_asset(asset_type='Application', name='BackupApp')
    new_assets.update({proxyapp, dmzapp, backupapp})
    # Same fieldname ('applications') on CorpNet as the associations just removed.
    corpnet.add_associated_assets('applications', {proxyapp})
    dmz.add_associated_assets('applications', {dmzapp})
    backup.add_associated_assets('applications', {backupapp})
    new_associations.update({
        (corpnet, 'applications', proxyapp),
        (dmz, 'applications', dmzapp),
        (backup, 'applications', backupapp),
    })

    proxyhw = model.add_asset(asset_type='Hardware', name='ProxyServer')
    new_assets.add(proxyhw)
    proxyhw.add_associated_assets('sysExecutedApps', {proxyapp})
    new_associations.add((proxyhw, 'sysExecutedApps', proxyapp))

    shareddata = model.add_asset(asset_type='Data', name='SharedData')
    new_assets.add(shareddata)
    proxyapp.add_associated_assets('containedData', {shareddata})
    # SharedData is reachable both through ProxyApp's containment and
    # directly through the hardware it's hosted on.
    shareddata.add_associated_assets('hardware', {proxyhw})
    new_associations.update({
        (proxyapp, 'containedData', shareddata),
        (shareddata, 'hardware', proxyhw),
    })

    svcidentity2 = model.add_asset(asset_type='Identity', name='SvcIdentity2')
    svccreds2 = model.add_asset(asset_type='Credentials', name='SvcCreds2')
    bob = model.add_asset(asset_type='User', name='Bob')
    new_assets.update({svcidentity2, svccreds2, bob})
    svcidentity2.add_associated_assets('credentials', {svccreds2})
    bob.add_associated_assets('userIds', {svcidentity2})
    svcidentity2.add_associated_assets('readPrivData', {shareddata})
    new_associations.update({
        (svcidentity2, 'credentials', svccreds2),
        (bob, 'userIds', svcidentity2),
        (svcidentity2, 'readPrivData', shareddata),
    })

    edgeidps = model.add_asset(asset_type='IDPS', name='EdgeIDPS')
    new_assets.add(edgeidps)
    edgeidps.add_associated_assets('protectedApps', {proxyapp, dmzapp})
    new_associations.update({
        (edgeidps, 'protectedApps', proxyapp),
        (edgeidps, 'protectedApps', dmzapp),
    })

    AG.partially_regenerate_graph(
        new_assets=new_assets, new_associations=new_associations,
        removed_assets=removed_assets, removed_associations=removed_associations,
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # --- Phase 3: teardown ---

    # Partial removal from a multi-target association (EdgeIDPS keeps
    # protecting ProxyApp but stops protecting DmzApp).
    edgeidps.remove_associated_assets('protectedApps', {dmzapp})
    AG.partially_regenerate_graph(
        removed_associations={(edgeidps, 'protectedApps', dmzapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    svcidentity2.remove_associated_assets('readPrivData', {shareddata})
    AG.partially_regenerate_graph(
        removed_associations={(svcidentity2, 'readPrivData', shareddata)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    shareddata.remove_associated_assets('hardware', {proxyhw})
    AG.partially_regenerate_graph(
        removed_associations={(shareddata, 'hardware', proxyhw)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Cascading removal of several interlinked assets (a network, its
    # application and their connecting rule) in one call.
    removed_assets = set()
    removed_associations = set()
    for asset in (backup, backupapp, cr2):
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in (backup, backupapp, cr2):
        removed_assets.add(asset)
        model.remove_asset(asset)
    AG.partially_regenerate_graph(
        removed_assets=removed_assets, removed_associations=removed_associations
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Final bulk teardown back to only the original Network asset.
    removed_assets = set()
    removed_associations = set()
    for asset in model.assets.values():
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in list(model.assets.values()):
        if asset != corpnet:
            removed_assets.add(asset)
            model.remove_asset(asset)
    AG.partially_regenerate_graph(
        removed_assets=removed_assets, removed_associations=removed_associations
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    assert set(model.assets.values()) == {corpnet}

def test_partial_regeneration_with_assocChainLang(assocChainLang_lang_graph: LanguageGraph) -> None:
    """Tests partial regeneration of the attack graph for a model in assocChainLang."""
    model = Model('Test Model', assocChainLang_lang_graph)
    parent = model.add_asset(asset_type='A', name='A:0')
    for asset_type in ["B", "C", "D", "E", "F", "G", "H", "I"]:
        child = model.add_asset(asset_type=asset_type, name=f"{asset_type}:0")
        parent.add_associated_assets(asset_type.lower(), {child})
        parent = child
    AG = AttackGraph(lang_graph=assocChainLang_lang_graph, model=model)

    for asset_type, fieldname in [("A", "b"), ("B", "c"), ("C", "d"), ("D", "e"), ("E", "f"), ("F", "g"), ("G", "h"), ("H", "i")]:
        parent = model.get_asset_by_name(f"{asset_type}:0")
        child = model.get_asset_by_name(f"{fieldname.upper()}:0")
        parent.remove_associated_assets(fieldname, {child})
        generated_AG = AttackGraph(lang_graph=assocChainLang_lang_graph, model=model)
        AG.partially_regenerate_graph(removed_associations={(parent, fieldname, child)})
        check_graph_equivalence(AG, generated_AG)

        parent.add_associated_assets(fieldname, {child})
        generated_AG = AttackGraph(lang_graph=assocChainLang_lang_graph, model=model)
        AG.partially_regenerate_graph(new_associations={(parent, fieldname, child)})
        check_graph_equivalence(AG, generated_AG)


def tests_create_ag_step_lists():
    """We have a predefined model in trainingLang with these associations:

    User:3 --- Host:0 --- Network:3 --- Host:1
                 |
                 |
               Data:2
    """
    mar = path_testdata('org.mal-lang.trainingLang-1.0.0.mar')
    model = path_testdata('simple_traininglang_model.yml')
    created_ag = create_attack_graph(mar, model)

    # Make sure all nodes were stored in correct list
    defenses = [n for n in created_ag.nodes.values() if n.type == 'defense']
    attacks = [n for n in created_ag.nodes.values() if n.type in ('or', 'and')]
    assert defenses == created_ag.defense_steps
    assert attacks == created_ag.attack_steps


def test_attackgraph_pickle(corelang_lang_graph, model):

    ag = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    pickle_path = '/tmp/attackgraph.pkl'
    with open(pickle_path, 'wb') as f:
        pickle.dump(ag, f)

    with open(pickle_path, 'rb') as f:
        unpickled_ag: AttackGraph = pickle.load(f)

    assert ag._to_dict() == unpickled_ag._to_dict()


def test_model_pickle(example_model: Model):

    pickle_path = '/tmp/model.pkl'
    with open(pickle_path, 'wb') as f:
        pickle.dump(example_model, f)

    with open(pickle_path, 'rb') as f:
        unpickled_model: Model = pickle.load(f)

    assert example_model.to_dict() == unpickled_model.to_dict()
