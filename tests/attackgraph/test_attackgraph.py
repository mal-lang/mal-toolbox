"""Unit tests for AttackGraph functionality"""

import copy
from unittest.mock import patch

from conftest import path_testdata
from maltoolbox.language import LanguageGraph
from maltoolbox.language.compiler import MalCompiler
from maltoolbox.attackgraph import (
    AttackGraph,
    AttackGraphNode,
    Attacker,
    create_attack_graph
)
from maltoolbox.model import Model


def test_attackgraph_init(corelang_lang_graph, model):
    """Test init with different params given"""

    # _generate_graph is called when langspec and model is given to init
    with patch("maltoolbox.attackgraph.AttackGraph._generate_graph")\
         as _generate_graph:
        AttackGraph(
            lang_graph=corelang_lang_graph,
            model=model
        )
        assert _generate_graph.call_count == 1

    # _generate_graph is not called when no model is given
    with patch("maltoolbox.attackgraph.AttackGraph._generate_graph")\
        as _generate_graph:
        AttackGraph(
            lang_graph=corelang_lang_graph,
            model=None
        )
        assert _generate_graph.call_count == 0

def attackgraph_save_load_no_model_given(
        example_attackgraph: AttackGraph,
        corelang_lang_graph: LanguageGraph,
        attach_attackers: bool
    ):
    """Save AttackGraph to a file and load it
    Note: Will create file in /tmp"""

    reward = 1
    node_with_reward_before = example_attackgraph.nodes[0]
    node_with_reward_before.extras['reward'] = reward

    if attach_attackers:
        example_attackgraph.attach_attackers()

    # Save the example attack graph to /tmp
    example_graph_path = "/tmp/example_graph.yml"
    example_attackgraph.save_to_file(example_graph_path)

    # Load the attack graph
    loaded_attack_graph = AttackGraph.load_from_file(example_graph_path,
        corelang_lang_graph)
    assert node_with_reward_before.id is not None
    node_with_reward_after = loaded_attack_graph.nodes[
        node_with_reward_before.id
    ]
    assert node_with_reward_after is not None
    assert node_with_reward_after.extras.get('reward') == reward

    # The model will not exist in the loaded attack graph
    assert loaded_attack_graph.model is None

    # Both graphs should have the same nodes
    assert len(example_attackgraph.nodes) == len(loaded_attack_graph.nodes)

    # Loaded graph nodes will not have 'asset' since it does not have a model.
    for loaded_node in loaded_attack_graph.nodes.values():
        if not isinstance(loaded_node.id, int):
            raise ValueError(f'Invalid node id for loaded node.')
        original_node = example_attackgraph.nodes[loaded_node.id]

        assert original_node, \
            f'Failed to find original node for id {loaded_node.id}.'

        # Convert loaded and original node to dicts
        loaded_node_dict = loaded_node.to_dict()
        original_node_dict = original_node.to_dict()
        for child in original_node_dict['children']:
            child_node = example_attackgraph.nodes[child]
            assert child_node, \
                f'Failed to find child node for id {child}.'
            original_node_dict['children'][child] = str(child_node.id) + \
                ":" + child_node.name
        for parent in original_node_dict['parents']:
            parent_node = example_attackgraph.nodes[parent]
            assert parent_node, \
                f'Failed to find parent node for id {parent}.'
            original_node_dict['parents'][parent] = str(parent_node.id) + \
                ":" + parent_node.name

        # Remove key that is not expected to match.
        del original_node_dict['asset']

        # Make sure nodes are the same (except for the excluded keys)
        assert loaded_node_dict == original_node_dict

    for loaded_attacker in loaded_attack_graph.attackers.values():
        if not isinstance(loaded_attacker.id, int):
            raise ValueError(f'Invalid attacker id for loaded attacker.')
        original_attacker = example_attackgraph.attackers[loaded_attacker.id]
        assert original_attacker, \
            f'Failed to find original attacker for id {loaded_attacker.id}.'
        loaded_attacker_dict = loaded_attacker.to_dict()
        original_attacker_dict = original_attacker.to_dict()
        for step in original_attacker_dict['entry_points']:
            attack_step_name = original_attacker_dict['entry_points'][step]
            attack_step_name = str(step) + ':' + \
                attack_step_name.split(':')[-1]
            original_attacker_dict['entry_points'][step] = attack_step_name
        for step in original_attacker_dict['reached_attack_steps']:
            attack_step_name = \
                original_attacker_dict['reached_attack_steps'][step]
            attack_step_name = str(step) + ':' + \
                attack_step_name.split(':')[-1]
            original_attacker_dict['reached_attack_steps'][step] = \
                attack_step_name
        assert loaded_attacker_dict == original_attacker_dict

def test_attackgraph_save_load_no_model_given_without_attackers(
        example_attackgraph: AttackGraph,
        corelang_lang_graph: LanguageGraph
    ):
    attackgraph_save_load_no_model_given(example_attackgraph,
        corelang_lang_graph, False)

def test_attackgraph_save_load_no_model_given_with_attackers(
        example_attackgraph: AttackGraph,
        corelang_lang_graph: LanguageGraph
    ):
    attackgraph_save_load_no_model_given(example_attackgraph,
        corelang_lang_graph, True)

def attackgraph_save_and_load_json_yml_model_given(
        example_attackgraph: AttackGraph,
        corelang_lang_graph: LanguageGraph,
        attach_attackers: bool
    ):
    """Try to save and load attack graph from json and yml with model given,
    and make sure the dict represenation is the same (except for reward field)
    """

    if attach_attackers:
        example_attackgraph.attach_attackers()

    for attackgraph_path in ("/tmp/attackgraph.yml", "/tmp/attackgraph.json"):
        example_attackgraph.save_to_file(attackgraph_path)
        loaded_attackgraph = AttackGraph.load_from_file(
            attackgraph_path,
            corelang_lang_graph,
            model=example_attackgraph.model
        )

        # Make sure model was 'attached' correctly
        assert loaded_attackgraph.model == example_attackgraph.model

        for node_full_name, loaded_node_dict in \
                loaded_attackgraph._to_dict()['attack_steps'].items():
            original_node_dict = \
                example_attackgraph._to_dict()['attack_steps'][node_full_name]

            # Make sure nodes are the same (except for the excluded keys)
            assert loaded_node_dict == original_node_dict

        for node in loaded_attackgraph.nodes.values():
            # Make sure node gets an asset when loaded with model
            assert node.model_asset
            assert node.full_name == node.model_asset.name + ":" + node.name

            # Make sure node was added to lookup dict with correct id / name
            assert node.id is not None
            assert loaded_attackgraph.nodes[node.id] == node
            assert loaded_attackgraph.get_node_by_full_name(node.full_name) == node

        for loaded_attacker in loaded_attackgraph.attackers.values():
            if not isinstance(loaded_attacker.id, int):
                raise ValueError(f'Invalid attacker id for loaded attacker.')
            original_attacker = example_attackgraph.attackers[
                loaded_attacker.id]
            assert original_attacker, \
                f'Failed to find original attacker for id ' \
                '{loaded_attacker.id}.'
            loaded_attacker_dict = loaded_attacker.to_dict()
            original_attacker_dict = original_attacker.to_dict()
            assert loaded_attacker_dict == original_attacker_dict

def test_attackgraph_save_and_load_json_yml_model_given_without_attackers(
        example_attackgraph: AttackGraph,
        corelang_lang_graph: LanguageGraph
    ):
        attackgraph_save_and_load_json_yml_model_given(
            example_attackgraph,
            corelang_lang_graph,
            False
        )

def test_attackgraph_save_and_load_json_yml_model_given_with_attackers(
        example_attackgraph: AttackGraph,
        corelang_lang_graph: LanguageGraph
    ):
        attackgraph_save_and_load_json_yml_model_given(
            example_attackgraph,
            corelang_lang_graph,
            True
        )

def test_attackgraph_attach_attackers(example_attackgraph: AttackGraph):
    """Make sure attackers are properly attached to graph"""

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
    assert not app1_auv in attacker.entry_points
    assert not app1_auv in attacker.reached_attack_steps

    attacker.compromise(app1_auv)
    assert app1_auv in attacker.reached_attack_steps
    assert app1_auv not in attacker.entry_points


    for node in attacker.reached_attack_steps:
        # Make sure the Attacker is present on the nodes they have compromised
        assert attacker in node.compromised_by

def test_attackgraph_generate_graph(example_attackgraph: AttackGraph):
    """Make sure the graph is correctly generated from model and lang"""
    # TODO: Add test cases with defense steps

    # Empty the attack graph
    example_attackgraph.nodes = {}
    example_attackgraph.attackers = {}

    # Generate the attack graph again
    example_attackgraph._generate_graph()

    # Calculate how many nodes we should expect
    num_assets_attack_steps = 0
    assert example_attackgraph.model
    for asset in example_attackgraph.model.assets.values():
        attack_steps = example_attackgraph.\
            lang_graph._get_attacks_for_asset_type(
                asset.type
            )
        num_assets_attack_steps += len(attack_steps)

    # Each attack step will get one node
    assert len(example_attackgraph.nodes) == num_assets_attack_steps


def test_attackgraph_according_to_corelang(corelang_lang_graph, model):
    """Looking at corelang .mal file, make sure the resulting
    AttackGraph contains expected nodes"""

    # Create 2 assets
    app1 = model.add_asset(asset_type = 'Application')
    app2 = model.add_asset(asset_type = 'Application')

    # Create association between app1 and app2
    app1.add_associated_assets(fieldname='appExecutedApps', assets = {app2})
    attack_graph = AttackGraph(lang_graph=corelang_lang_graph, model = model)

    # These are all attack 71 steps and defenses for Application asset in MAL
    expected_node_names_application = {
        "notPresent", "attemptUseVulnerability", "successfulUseVulnerability",
        "useVulnerability", "attemptReverseReach", "successfulReverseReach",
        "reverseReach", "localConnect", "networkConnectUninspected",
        "networkConnectInspected", "networkConnect",
        "specificAccessNetworkConnect",
        "accessNetworkAndConnections", "attemptNetworkConnectFromResponse",
        "networkConnectFromResponse", "specificAccessFromLocalConnection",
        "specificAccessFromNetworkConnection", "specificAccess",
        "bypassContainerization", "authenticate",
        "specificAccessAuthenticate", "localAccess", "networkAccess",
        "fullAccess", "physicalAccessAchieved", "attemptUnsafeUserActivity",
        "successfulUnsafeUserActivity", "unsafeUserActivity",
        "attackerUnsafeUserActivityCapability",
        "attackerUnsafeUserActivityCapabilityWithReverseReach",
        "attackerUnsafeUserActivityCapabilityWithoutReverseReach",
        "supplyChainAuditing", "bypassSupplyChainAuditing",
        "supplyChainAuditingBypassed",
        "attemptFullAccessFromSupplyChainCompromise",
        "fullAccessFromSupplyChainCompromise",
        "attemptReadFromSoftProdVulnerability",
        "attemptModifyFromSoftProdVulnerability",
        "attemptDenyFromSoftProdVulnerability", "softwareCheck",
        "softwareProductVulnerabilityLocalAccessAchieved",
        "softwareProductVulnerabilityNetworkAccessAchieved",
        "softwareProductVulnerabilityPhysicalAccessAchieved",
        "softwareProductVulnerabilityLowPrivilegesAchieved",
        "softwareProductVulnerabilityHighPrivilegesAchieved",
        "softwareProductVulnerabilityUserInteractionAchieved",
        "attemptSoftwareProductAbuse",
        "softwareProductAbuse", "readFromSoftProdVulnerability",
        "modifyFromSoftProdVulnerability",
        "denyFromSoftProdVulnerability",
        "attemptApplicationRespondConnectThroughData",
        "successfulApplicationRespondConnectThroughData",
        "applicationRespondConnectThroughData",
        "attemptAuthorizedApplicationRespondConnectThroughData",
        "successfulAuthorizedApplicationRespondConnectThroughData",
        "authorizedApplicationRespondConnectThroughData",
        "attemptRead", "successfulRead", "read", "specificAccessRead",
        "attemptModify", "successfulModify", "modify", "specificAccessModify",
        "attemptDeny", "successfulDeny", "deny",
        "specificAccessDelete", "denyFromNetworkingAsset", "denyFromLockout"
    }

    # Make sure the nodes in the AttackGraph have the expected names
    app_attack_steps_names = {attack_step.name for attack_step in
        attack_graph.nodes.values()}
    assert app_attack_steps_names == expected_node_names_application

    # notPresent is a defense step and its children are (according to corelang):
    expected_children_of_notpresent = {
        "successfulUseVulnerability",
        "successfulReverseReach",
        "networkConnectFromResponse",
        "specificAccessFromLocalConnection",
        "specificAccessFromNetworkConnection",
        "localAccess",
        "networkAccess",
        "successfulUnsafeUserActivity",
        "fullAccessFromSupplyChainCompromise",
        "readFromSoftProdVulnerability",
        "modifyFromSoftProdVulnerability",
        "denyFromSoftProdVulnerability",
        "successfulApplicationRespondConnectThroughData",
        "successfulAuthorizedApplicationRespondConnectThroughData",
        "successfulRead",
        "successfulModify",
        "successfulDeny"
    }
    # Make sure children are also added for defense step notPresent
    notpresent_attack_step = attack_graph.nodes[0]
    notpresent_children_names = {attack_step.name for attack_step in
        notpresent_attack_step.children}
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
    """
    Try to deepcopy an attackgraph object. The nodes of the attack graph
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

    assert list(copied_attackgraph.nodes.keys()) \
        == list(example_attackgraph.nodes.keys())

    assert list(copied_attackgraph.attackers.keys()) \
        == list(example_attackgraph.attackers.keys())

    assert list(copied_attackgraph._full_name_to_node.keys()) \
        == list(example_attackgraph._full_name_to_node.keys())

    assert id(copied_attackgraph.model) == id(example_attackgraph.model)

    assert len(copied_attackgraph.nodes) \
        == len(example_attackgraph.nodes)

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

        for attacker in node.compromised_by:
            assert id(attacker) == id(copied_attackgraph.attackers[0])
            original_node.compromised_by

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

    assert len(copied_attackgraph.attackers) \
        == len(example_attackgraph.attackers)
    assert id(copied_attackgraph.attackers) \
        != id(example_attackgraph.attackers)

    for attacker in copied_attackgraph.attackers.values():

        for entry_point in attacker.entry_points:
            assert entry_point.id
            entry_point_in_attack_graph = copied_attackgraph.nodes[entry_point.id]
            assert entry_point_in_attack_graph
            assert entry_point == entry_point_in_attack_graph
            assert id(entry_point) == id(entry_point_in_attack_graph)

        assert attacker.id is not None
        original_attacker = example_attackgraph.attackers[attacker.id]
        assert original_attacker
        assert id(original_attacker) != id(attacker)
        assert original_attacker.to_dict() == attacker.to_dict()


def test_attackgraph_deepcopy_attackers(example_attackgraph: AttackGraph):
    """
    Make sure attackers entry points and reached steps are copied correctly
    """
    example_attackgraph.attach_attackers()

    original_attacker = example_attackgraph.attackers[0]
    for reached in original_attacker.reached_attack_steps:
        assert reached.id
        node = example_attackgraph.nodes[reached.id]
        assert node
        assert id(node) == id(reached)

    for entrypoint in original_attacker.entry_points:
        assert entrypoint.id
        node = example_attackgraph.nodes[entrypoint.id]
        assert node
        assert id(node) == id(entrypoint)

    copied_attackgraph = copy.deepcopy(example_attackgraph)
    copied_attacker = copied_attackgraph.attackers[0]
    for reached in copied_attacker.reached_attack_steps:
        assert reached.id
        node = copied_attackgraph.nodes[reached.id]
        assert node
        assert id(node) == id(reached)

    for entrypoint in copied_attacker.entry_points:
        assert entrypoint.id
        node = copied_attackgraph.nodes[entrypoint.id]
        assert node
        assert id(node) == id(entrypoint)


def test_deepcopy_memo_test(example_attackgraph: AttackGraph):
    """
    Make sure memo is filled up with expected number of objects
    """
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
    assert len(copied_attackers) == len(memo_attackers) == len(example_attackgraph.attackers)

    # Make sure memo didn't store any new nodes
    memo_nodes = [o for o in memo.values() if isinstance(o, AttackGraphNode)]
    assert len(memo_nodes) == len(example_attackgraph.nodes)

def test_attackgraph_subtype():

    test_lang_graph = LanguageGraph(MalCompiler().compile(
        'tests/testdata/subtype_attack_step.mal'))
    test_model = Model('Test Model', test_lang_graph)
    # Create assets
    baseasset1 = test_model.add_asset(
        name = 'BaseAsset 1',
        asset_type = 'BaseAsset')

    subasset1 = test_model.add_asset(
        name = 'SubAsset 1',
        asset_type = 'SubAsset')

    otherasset1 = test_model.add_asset(
        name = 'OtherAsset 1',
        asset_type = 'OtherAsset')

    # Create association between subasset1 and otherasset1
    subasset1.add_associated_assets('field2', {otherasset1})
    baseasset1.add_associated_assets('field2', {otherasset1})

    test_attack_graph = AttackGraph(
        lang_graph=test_lang_graph,
        model=test_model
    )
    ba_1_base_step1 = test_attack_graph.get_node_by_full_name(
        'BaseAsset 1:base_step1')
    ba_1_base_step2 = test_attack_graph.get_node_by_full_name(
        'BaseAsset 1:base_step2')
    sa_1_base_step1 = test_attack_graph.get_node_by_full_name(
        'SubAsset 1:base_step1')
    sa_1_base_step2 = test_attack_graph.get_node_by_full_name(
        'SubAsset 1:base_step2')
    sa_1_subasset_step1 = test_attack_graph.get_node_by_full_name(
        'SubAsset 1:subasset_step1')
    oa_1_other_step1 = test_attack_graph.get_node_by_full_name(
        'OtherAsset 1:other_step1')

    assert ba_1_base_step1 in oa_1_other_step1.children
    assert ba_1_base_step2 not in oa_1_other_step1.children
    assert sa_1_base_step1 in oa_1_other_step1.children
    assert sa_1_base_step2 in oa_1_other_step1.children
    assert sa_1_subasset_step1 in oa_1_other_step1.children

def test_attackgraph_setops():

    test_lang_graph = LanguageGraph(MalCompiler().compile(
        'tests/testdata/set_ops.mal'))
    test_model = Model('Test Model', test_lang_graph)

    # Create assets
    set_ops_a1 = test_model.add_asset(
        asset_type = 'SO_A',
        name = 'SO_A 1')
    set_ops_b1 = test_model.add_asset(
        asset_type = 'SO_B',
        name = 'SO_B 1')
    set_ops_b2 = test_model.add_asset(
        asset_type = 'SO_B',
        name = 'SO_B 2')
    set_ops_b3 = test_model.add_asset(
        asset_type = 'SO_B',
        name = 'SO_B 3')

    # Create association
    set_ops_a1.add_associated_assets('fieldB1', {set_ops_b1, set_ops_b2})

    set_ops_a1.add_associated_assets('fieldB2', {set_ops_b2, set_ops_b3})

    test_attack_graph = AttackGraph(
        lang_graph=test_lang_graph,
        model=test_model
    )

    assetA1_origStep = test_attack_graph.get_node_by_full_name(
        'SO_A 1:originStep')
    assetB1_unionStep = test_attack_graph.get_node_by_full_name(
        'SO_B 1:unionStep')
    assetB1_intersectStep = test_attack_graph.get_node_by_full_name(
        'SO_B 1:intersectionStep')
    assetB1_diffStep = test_attack_graph.get_node_by_full_name(
        'SO_B 1:differenceStep')
    assetB2_unionStep = test_attack_graph.get_node_by_full_name(
        'SO_B 2:unionStep')
    assetB2_intersectStep = test_attack_graph.get_node_by_full_name(
        'SO_B 2:intersectionStep')
    assetB2_diffStep = test_attack_graph.get_node_by_full_name(
        'SO_B 2:differenceStep')
    assetB3_unionStep = test_attack_graph.get_node_by_full_name(
        'SO_B 3:unionStep')
    assetB3_intersectStep = test_attack_graph.get_node_by_full_name(
        'SO_B 3:intersectionStep')
    assetB3_diffStep = test_attack_graph.get_node_by_full_name(
        'SO_B 3:differenceStep')

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

    test_lang_graph = LanguageGraph(MalCompiler().compile(
        'tests/testdata/set_ops_adv.mal'))
    test_model = Model('Test Model', test_lang_graph)

    # Create assets
    set_ops_a1 = test_model.add_asset(
        asset_type = 'SOA_A',
        name = 'SOA_A 1')
    set_ops_a2 = test_model.add_asset(
        asset_type = 'SOA_A',
        name = 'SOA_A 2')
    set_ops_a3 = test_model.add_asset(
        asset_type = 'SOA_A',
        name = 'SOA_A 3')
    set_ops_b1 = test_model.add_asset(
        asset_type = 'SOA_B',
        name = 'SOA_B 1')
    set_ops_b2 = test_model.add_asset(
        asset_type = 'SOA_B',
        name = 'SOA_B 2')
    set_ops_b3 = test_model.add_asset(
        asset_type = 'SOA_B',
        name = 'SOA_B 3')

    # Create association
    set_ops_a2.add_associated_assets('fieldB1', {set_ops_b1, set_ops_b2})
    set_ops_a3.add_associated_assets('fieldB2', {set_ops_b2, set_ops_b3})
    set_ops_a1.add_associated_assets('fieldA3b', {set_ops_a2, set_ops_a3})

    test_attack_graph = AttackGraph(
        lang_graph=test_lang_graph,
        model=test_model
    )

    assetA1_origInnerStep = test_attack_graph.get_node_by_full_name(
        'SOA_A 1:originInnerStep')
    assetA1_origOuterStep = test_attack_graph.get_node_by_full_name(
        'SOA_A 1:originOuterStep')
    assetB1_intersectStep = test_attack_graph.get_node_by_full_name(
        'SOA_B 1:intersectionStep')
    assetB2_intersectStep = test_attack_graph.get_node_by_full_name(
        'SOA_B 2:intersectionStep')
    assetB3_intersectStep = test_attack_graph.get_node_by_full_name(
        'SOA_B 3:intersectionStep')

    assert assetB1_intersectStep not in assetA1_origInnerStep.children
    assert assetB2_intersectStep not in assetA1_origInnerStep.children
    assert assetB3_intersectStep not in assetA1_origInnerStep.children

    assert assetB1_intersectStep not in assetA1_origOuterStep.children
    assert assetB2_intersectStep in assetA1_origOuterStep.children
    assert assetB3_intersectStep not in assetA1_origOuterStep.children

def test_attackgraph_transitive():
    test_lang_graph = LanguageGraph(MalCompiler().compile(
        'tests/testdata/transitive.mal'))
    test_model = Model('Test Model', test_lang_graph)

    asset1 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 1')
    asset2 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 2')
    asset3 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 3')
    asset4 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 4')
    asset5 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 5')
    asset6 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 6')

    asset1.add_associated_assets('field2', {asset2})
    asset2.add_associated_assets('field2', {asset3})
    asset3.add_associated_assets('field2', {asset4})
    asset3.add_associated_assets('field2', {asset5})
    asset6.add_associated_assets('field2', {asset1})

    test_attack_graph = AttackGraph(
        lang_graph=test_lang_graph,
        model=test_model
    )

    asset1_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 1:test_step')
    asset2_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 2:test_step')
    asset3_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 3:test_step')
    asset4_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 4:test_step')
    asset5_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 5:test_step')
    asset6_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 6:test_step')

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

    test_lang_graph = LanguageGraph(MalCompiler().compile(
        'tests/testdata/transitive_advanced.mal'))
    test_model = Model('Test Model', test_lang_graph)

    asset1 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 1')
    asset2 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 2')
    asset3 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 3')
    asset4 = test_model.add_asset(
        asset_type = 'TestAsset',
        name = 'TestAsset 4')

    asset1.add_associated_assets('fieldA2', {asset2, asset3})
    asset1.add_associated_assets('fieldB2', {asset3, asset4})

    test_attack_graph = AttackGraph(
        lang_graph=test_lang_graph,
        model=test_model
    )

    asset1_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 1:test_step')
    asset2_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 2:test_step')
    asset3_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 3:test_step')
    asset4_test_step = test_attack_graph.get_node_by_full_name(
        'TestAsset 4:test_step')

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
        assert parent, f"Could not find node {parent_fn}"

        # Verify that parent has given children
        assert {c.full_name for c in parent.children} == set(children_fns)

        # Verify that child has given parent
        for child_fn in children_fns:
            child = ag.get_node_by_full_name(child_fn)
            assert child, f"Could not find child by full name {child_fn}"
            assert parent_fn in [p.full_name for p in child.parents]

    mar = path_testdata('org.mal-lang.trainingLang-1.0.0.mar')
    model = path_testdata('simple_traininglang_model.yml')

    # Make sure attack graph is created without errors
    created_ag = create_attack_graph(mar, model)

    # Make sure all nodes were generated for the model
    assert {n.full_name for n in created_ag.nodes.values()} == {
        'Host:0:notPresent', 'Host:0:authenticate', 'Host:0:connect',
        'Host:0:access', 'Host:1:notPresent', 'Host:1:authenticate',
        'Host:1:connect', 'Host:1:access', 'Data:2:notPresent',
        'Data:2:read', 'Data:2:modify', 'User:3:notPresent',
        'User:3:compromise', 'User:3:phishing', 'Network:3:access'
    }

    # Make sure associations were added as parent/child relationships
    check_parent_child_relationship(
        created_ag, 'Host:0:notPresent', ['Host:0:connect', 'Host:0:access'])
    check_parent_child_relationship(
        created_ag, 'Host:0:authenticate', ['Host:0:access'])
    check_parent_child_relationship(
        created_ag, 'Host:0:connect', ['Host:0:access'])
    check_parent_child_relationship(
        created_ag, 'Host:0:access',
        ['Data:2:modify', 'Data:2:read', 'Network:3:access']
    )
    check_parent_child_relationship(
        created_ag, 'Host:1:notPresent', ['Host:1:connect', 'Host:1:access'])
    check_parent_child_relationship(
        created_ag, 'Host:1:authenticate', ['Host:1:access'])
    check_parent_child_relationship(
        created_ag, 'Host:1:connect', ['Host:1:access'])
    check_parent_child_relationship(
        created_ag, 'Host:1:access', ['Network:3:access'])
    check_parent_child_relationship(
        created_ag, 'Data:2:notPresent', ['Data:2:read', 'Data:2:modify'])
    check_parent_child_relationship(
        created_ag, 'Data:2:read', [])
    check_parent_child_relationship(
        created_ag, 'Data:2:modify', [])
    check_parent_child_relationship(
        created_ag, 'User:3:notPresent', ['User:3:compromise'])
    check_parent_child_relationship(
        created_ag, 'User:3:compromise', ['Host:0:authenticate'])
    check_parent_child_relationship(
        created_ag, 'User:3:phishing', ['User:3:compromise'])
    check_parent_child_relationship(
        created_ag, 'Network:3:access', ['Host:0:connect', 'Host:1:connect'])


def test_attackgraph_remove_attacker(example_attackgraph: AttackGraph):
    example_attackgraph.attach_attackers()
    attackers = list(example_attackgraph.attackers.values())
    for attacker in attackers:
        example_attackgraph.remove_attacker(attacker)
