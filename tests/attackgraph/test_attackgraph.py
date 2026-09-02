"""Unit tests for AttackGraph functionality"""

import copy
import pickle
from unittest.mock import patch

import pytest
from conftest import path_testdata

from maltoolbox.attackgraph import AttackGraph, AttackGraphNode, create_attack_graph
from maltoolbox.language import LanguageGraph
from maltoolbox.language.compiler import MalCompiler
from maltoolbox.language.language_graph_assoc import LanguageGraphAssociationField
from maltoolbox.language.language_graph_lookup import get_attacks_for_asset_type
from maltoolbox.model import Model, ModelAsset


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
    origin = test_model.add_asset(asset_type='Origin', name='Origin')
    target1 = test_model.add_asset(asset_type='Target', name='Target 1')
    target2 = test_model.add_asset(asset_type='Target', name='Target 2')
    target3 = test_model.add_asset(asset_type='Target', name='Target 3')

    # setA = {Target 1, Target 2}, setB = {Target 2, Target 3}
    origin.add_associated_assets('setA', {target1, target2})
    origin.add_associated_assets('setB', {target2, target3})

    test_attack_graph = AttackGraph(lang_graph=test_lang_graph, model=test_model)

    check = test_attack_graph.get_node_by_full_name('Origin:check')
    target1_union = test_attack_graph.get_node_by_full_name('Target 1:unionResult')
    target1_intersection = test_attack_graph.get_node_by_full_name(
        'Target 1:intersectionResult'
    )
    target1_difference = test_attack_graph.get_node_by_full_name(
        'Target 1:differenceResult'
    )
    target2_union = test_attack_graph.get_node_by_full_name('Target 2:unionResult')
    target2_intersection = test_attack_graph.get_node_by_full_name(
        'Target 2:intersectionResult'
    )
    target2_difference = test_attack_graph.get_node_by_full_name(
        'Target 2:differenceResult'
    )
    target3_union = test_attack_graph.get_node_by_full_name('Target 3:unionResult')
    target3_intersection = test_attack_graph.get_node_by_full_name(
        'Target 3:intersectionResult'
    )
    target3_difference = test_attack_graph.get_node_by_full_name(
        'Target 3:differenceResult'
    )

    # Target 1 is only in setA: union yes, intersection no, difference yes.
    assert target1_union in check.children
    assert target1_intersection not in check.children
    assert target1_difference in check.children
    # Target 2 is in both setA and setB: union yes, intersection yes, difference no.
    assert target2_union in check.children
    assert target2_intersection in check.children
    assert target2_difference not in check.children
    # Target 3 is only in setB: union yes, intersection no, difference no.
    assert target3_union in check.children
    assert target3_intersection not in check.children
    assert target3_difference not in check.children


def test_attackgraph_setops_adv():

    test_lang_graph = LanguageGraph(
        MalCompiler().compile('tests/testdata/set_ops_adv.mal')
    )
    test_model = Model('Test Model', test_lang_graph)

    # Create assets: hub1 has two sibling hubs, hub2 and hub3, each of
    # which reaches a different, partially-overlapping set of targets.
    hub1 = test_model.add_asset(asset_type='Hub', name='Hub 1')
    hub2 = test_model.add_asset(asset_type='Hub', name='Hub 2')
    hub3 = test_model.add_asset(asset_type='Hub', name='Hub 3')
    target1 = test_model.add_asset(asset_type='Target', name='Target 1')
    target2 = test_model.add_asset(asset_type='Target', name='Target 2')
    target3 = test_model.add_asset(asset_type='Target', name='Target 3')

    # hub2's setA = {Target 1, Target 2}, hub3's setB = {Target 2, Target 3}
    hub2.add_associated_assets('setA', {target1, target2})
    hub3.add_associated_assets('setB', {target2, target3})
    hub1.add_associated_assets('siblings', {hub2, hub3})

    test_attack_graph = AttackGraph(lang_graph=test_lang_graph, model=test_model)

    hub1_inner = test_attack_graph.get_node_by_full_name('Hub 1:innerIntersection')
    hub1_outer = test_attack_graph.get_node_by_full_name('Hub 1:outerIntersection')
    target1_intersection = test_attack_graph.get_node_by_full_name(
        'Target 1:intersectionResult'
    )
    target2_intersection = test_attack_graph.get_node_by_full_name(
        'Target 2:intersectionResult'
    )
    target3_intersection = test_attack_graph.get_node_by_full_name(
        'Target 3:intersectionResult'
    )

    # innerIntersection intersects setA and setB per sibling, and no single
    # sibling has both fields set, so it never reaches any target.
    assert target1_intersection not in hub1_inner.children
    assert target2_intersection not in hub1_inner.children
    assert target3_intersection not in hub1_inner.children

    # outerIntersection intersects the union of siblings' setA with the
    # union of siblings' setB, so only Target 2 (in both unions) survives.
    assert target1_intersection not in hub1_outer.children
    assert target2_intersection in hub1_outer.children
    assert target3_intersection not in hub1_outer.children


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


def test_create_dynamic_ag():
    """Create an attack graph from a model in a language using DynaMAL grammar."""

    lang = LanguageGraph.from_mal_spec("tests/testdata/wiperLang.mal")
    model = Model.load_from_file("tests/testdata/wiper_model.yml", lang)
    AG = AttackGraph(lang_graph=lang, model=model)

    wiper_test = AG.get_node_by_full_name("Wiper:test")
    for model_effect in wiper_test.additive_model_effects:
        assert len(model_effect.base) == 1, "Too many assoc traversal for base in dynamic statement"
        assert model_effect.base[0].field_name == "self", "Base field name is not correct for dynamic statement"
        for dyn_target in model_effect.targets:
            assert not dyn_target.assoc_op, "Dynamic target should not operate on associations"
            assert len(dyn_target.assoc_traversal) == 1, "Dynamic target should have exactly one assoc traversal"
            assert dyn_target.assoc_traversal[0].field_name == "victim", "Dynamic target assoc traversal field name is not correct"
            assert dyn_target.assoc_traversal[0].asset_filter.name in ("C2Server", "Device")

    # Imagine we compromise Wiper:test
    def get_lg_assoc_field(asset: ModelAsset, field_name: str) -> LanguageGraphAssociationField:
        assoc = asset.lg_asset.associations[field_name]
        if assoc.left_field == field_name:
            return assoc.right_field
        else:
            return assoc.left_field
    for model_effect in wiper_test.additive_model_effects:
        base_assets = {wiper_test.model_asset}
        for assoc_traversal in model_effect.base:
            if assoc_traversal.field_name == "self":
                assert base_assets == {wiper_test.model_asset}
                continue
        for dyn_target in model_effect.targets:
            target_assets = copy.copy(base_assets)
            for traversal_index in range(len(dyn_target.assoc_traversal)-1):
                assoc_traversal = dyn_target.assoc_traversal[traversal_index]
                if assoc_traversal.field_name == "self":
                    target_assets = {wiper_test.model_asset}
                else:
                    new_target_assets = set()
                    for asset in target_assets:
                        new_target_assets.update(asset.associated_assets[assoc_traversal.field_name])
                    target_assets = new_target_assets
            if dyn_target.assoc_op:
                pass
            else:
                terminating_assoc_traversal = dyn_target.assoc_traversal[-1]
                for asset in target_assets:
                    add_assoc_field = get_lg_assoc_field(asset, terminating_assoc_traversal.field_name)
                    added_asset = model.add_asset(
                        asset_type=add_assoc_field.asset.name, 
                        name=f"{add_assoc_field.fieldname}_{len(model.assets)}",
                    )
                    try:
                        asset.add_associated_assets(add_assoc_field.fieldname, {added_asset})
                    except ValueError as exception:
                        assert exception.args[0] == 'You can have maximum 1 assets for association field victim'

        AG.regenerate_graph()





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
