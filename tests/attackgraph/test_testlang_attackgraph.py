"""Unit tests for more complex AttackGraph functionality using testLang """

import pytest

from maltoolbox.language import LanguageGraph
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode, Attacker
from maltoolbox.model import Model, AttackerAttachment

from test_model import create_association


@pytest.fixture
def example_testlang_attackgraph(testlang_lang_graph: LanguageGraph, testlang_model: Model):
    """Fixture that generates an example attack graph
       with unattached attacker

    Uses coreLang specification and model with two applications
    with an association and an attacker to create and return
    an AttackGraph object
    """

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

    return AttackGraph(
        lang_graph=testlang_lang_graph,
        model=testlang_model
    )

def test_testlang_attackgraph(
        example_testlang_attackgraph: AttackGraph
    ):
    example_testlang_attackgraph.save_to_file(
        '/tmp/example_testlang_attack_graph.yml')
