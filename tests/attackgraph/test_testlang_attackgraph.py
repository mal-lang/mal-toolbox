"""Unit tests for more complex AttackGraph functionality using testLang """

import pytest

from maltoolbox.language import LanguageGraph
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode, Attacker
from maltoolbox.model import Model, AttackerAttachment

from test_model import create_association


def test_testlang_attackgraph_subtype(
        testlang_lang_graph: LanguageGraph,
        testlang_model: Model
    ):

    # Create assets
    baseasset1 = testlang_model.lang_classes_factory.get_asset_class('BaseAsset')(
        name = 'BaseAsset 1'
    )
    subasset1 = testlang_model.lang_classes_factory.get_asset_class('SubAsset')(
        name = 'SubAsset 1'
    )
    otherasset1 = testlang_model.lang_classes_factory.get_asset_class('OtherAsset')(
        name = 'OtherAsset 1'
    )
    testlang_model.add_asset(baseasset1)
    testlang_model.add_asset(subasset1)
    testlang_model.add_asset(otherasset1)

    # Create association between subasset1 and otherasset1
    assoc = create_association(testlang_model,
        left_assets = [subasset1, baseasset1],
        right_assets = [otherasset1],
        assoc_type = 'SubtypeTestAssoc_subtype_test_assoc_field1_BaseAsset_subtype_test_assoc_field2_OtherAsset',
        left_fieldname = 'subtype_test_assoc_field1',
        right_fieldname = 'subtype_test_assoc_field2')
    testlang_model.add_association(assoc)

    example_testlang_attackgraph = AttackGraph(
        lang_graph=testlang_lang_graph,
        model=testlang_model
    )
    example_testlang_attackgraph.save_to_file(
        '/tmp/example_testlang_attack_graph.yml')

def test_testlang_attackgraph_setops(
        testlang_lang_graph: LanguageGraph,
        testlang_model: Model
    ):

    # Create assets
    set_ops_a1 = testlang_model.lang_classes_factory.get_asset_class(
        'SetOpsAssetA')(
            name = 'SetOpsAssetA 1'
        )
    set_ops_b1 = testlang_model.lang_classes_factory.get_asset_class(
        'SetOpsAssetB')(
            name = 'SetOpsAssetB 1'
        )
    set_ops_b2 = testlang_model.lang_classes_factory.get_asset_class(
        'SetOpsAssetB')(
            name = 'SetOpsAssetB 2'
        )
    set_ops_b3 = testlang_model.lang_classes_factory.get_asset_class(
        'SetOpsAssetB')(
            name = 'SetOpsAssetB 3'
        )
    testlang_model.add_asset(set_ops_a1)
    testlang_model.add_asset(set_ops_b1)
    testlang_model.add_asset(set_ops_b2)
    testlang_model.add_asset(set_ops_b3)

    # Create association
    assoc = create_association(testlang_model,
        left_assets = [set_ops_a1],
        right_assets = [set_ops_b1, set_ops_b2],
        assoc_type = 'SetOps1_fieldA1_SetOpsAssetA_fieldB1_SetOpsAssetB',
        left_fieldname = 'fieldA1',
        right_fieldname = 'fieldB1')
    testlang_model.add_association(assoc)

    assoc = create_association(testlang_model,
        left_assets = [set_ops_a1],
        right_assets = [set_ops_b2, set_ops_b3],
        assoc_type = 'SetOps2_fieldA2_SetOpsAssetA_fieldB2_SetOpsAssetB',
        left_fieldname = 'fieldA2',
        right_fieldname = 'fieldB2')
    testlang_model.add_association(assoc)

    example_testlang_attackgraph = AttackGraph(
        lang_graph=testlang_lang_graph,
        model=testlang_model
    )

    assetA1_opsA = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetA 1:testStepSetOpsA')
    assetB1_opsB1 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 1:testStepSetOpsB1')
    assetB1_opsB2 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 1:testStepSetOpsB2')
    assetB1_opsB3 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 1:testStepSetOpsB3')
    assetB2_opsB1 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 2:testStepSetOpsB1')
    assetB2_opsB2 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 2:testStepSetOpsB2')
    assetB2_opsB3 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 2:testStepSetOpsB3')
    assetB3_opsB1 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 3:testStepSetOpsB1')
    assetB3_opsB2 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 3:testStepSetOpsB2')
    assetB3_opsB3 = example_testlang_attackgraph.get_node_by_full_name(
        'SetOpsAssetB 3:testStepSetOpsB3')

    assert assetB1_opsB1 in assetA1_opsA.children
    assert assetB1_opsB2 not in assetA1_opsA.children
    assert assetB1_opsB3 in assetA1_opsA.children
    assert assetB2_opsB1 in assetA1_opsA.children
    assert assetB2_opsB2 in assetA1_opsA.children
    assert assetB2_opsB3 not in assetA1_opsA.children
    assert assetB3_opsB1 in assetA1_opsA.children
    assert assetB3_opsB2 not in assetA1_opsA.children
    assert assetB3_opsB3 not in assetA1_opsA.children
