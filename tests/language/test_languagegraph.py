"""Tests for the LanguageGraph"""

import pytest
from conftest import path_testdata

from maltoolbox.language import LanguageGraph

from maltoolbox.language.compiler import MalCompiler
from maltoolbox.language import LanguageGraph


def test_languagegraph_save_load(corelang_lang_graph: LanguageGraph):
    """Test to see if saving and loading a language graph to a file produces
    the same language graph. We have to use the json format to save and load
    because YAML reorders the keys in alphabetical order."""
    graph_path = "/tmp/langgraph.json"
    corelang_lang_graph.save_to_file(graph_path)

    new_lang_graph = LanguageGraph.load_from_file(graph_path)

    assert new_lang_graph._to_dict() == corelang_lang_graph._to_dict()

# TODO: Replace this with a dedicated test that just checks for union for
# assets with the same super asset
def test_corelang_with_union_different_assets_same_super_asset():
    """Uses modified coreLang language specification.
    An attackstep in IAMObject will contain a union between
    Identity and Group, which should be allowed, since they
    share the same super asset.
    """

    mar_file_path = path_testdata("corelang-union-common-ancestor.mar")

    # Make sure that it can generate
    LanguageGraph.from_mar_archive(mar_file_path)

def test_interleaved_vars():
    """Check to see if two interleaved variables(variables that contain
    variables from each other, A2 contains B1 and B2 contains A1) were
    resolved correct.
    """

    test_lang_graph = LanguageGraph(MalCompiler().compile(
        'tests/testdata/interleaved_vars.mal'))
    assert 'AssetA' in test_lang_graph.assets
    assert 'AssetB' in test_lang_graph.assets

    assetA = test_lang_graph.assets['AssetA']
    assetB = test_lang_graph.assets['AssetB']

    assert 'A1' in assetA.variables
    assert 'A2' in assetA.variables
    assert 'B1' in assetB.variables
    assert 'B2' in assetB.variables

    varA2 = assetA.variables['A2']
    varB2 = assetB.variables['B2']
    assert varA2[0] == assetA
    assert varA2[1].right_link.fieldname == 'fieldA'
    assert varB2[0] == assetB
    assert varB2[1].right_link.fieldname == 'fieldB'

def test_inherited_vars():
    LanguageGraph(MalCompiler().compile('tests/testdata/inherited_vars.mal'))

def test_attackstep_inherit():
    lang_spec = MalCompiler().compile(
        'tests/testdata/attackstep_inherit.mal'
    )
    lang_graph = LanguageGraph(lang_spec)

    BB_s1 = lang_graph.assets['BB'].attack_steps['s1']
    CC_s2 = lang_graph.assets['CC'].attack_steps['s2']

    assert CC_s2 in BB_s1.children
    assert len(BB_s1.own_children) == 1
    assert len(BB_s1.children) == 1

    chains_to_cc_s2 = BB_s1.children[CC_s2]
    assert len(chains_to_cc_s2) == 2
    assert chains_to_cc_s2[0].fieldname == "c_of_B"
    assert chains_to_cc_s2[1].fieldname == "c_of_A"


def test_attackstep_override():
    test_lang_graph = LanguageGraph(MalCompiler().compile(
        'tests/testdata/attackstep_override.mal'))

    assert 'EmptyParent' in test_lang_graph.assets
    assert 'Child1' in test_lang_graph.assets
    assert 'Child2' in test_lang_graph.assets
    assert 'Child3' in test_lang_graph.assets
    assert 'Child4' in test_lang_graph.assets
    assert 'FinalChild' in test_lang_graph.assets

    assetEP = test_lang_graph.assets['EmptyParent']
    assetC1 = test_lang_graph.assets['Child1']
    assetC2 = test_lang_graph.assets['Child2']
    assetC3 = test_lang_graph.assets['Child3']
    assetC4 = test_lang_graph.assets['Child4']
    assetFC = test_lang_graph.assets['FinalChild']

    EP_target1 = assetEP.attack_steps['target1']
    assert 'target1' in assetEP.attack_steps
    assert 'target2' in assetEP.attack_steps
    assert 'target3' in assetEP.attack_steps
    assert 'target4' in assetEP.attack_steps

    assert 'attack_step_with_child' in assetC1.attack_steps
    assert 'attackstep' in assetC1.attack_steps
    assert 'target1' in assetC1.attack_steps
    assert 'target2' in assetC1.attack_steps
    assert 'target3' in assetC1.attack_steps
    assert 'target4' in assetC1.attack_steps
    c1_attackstep = assetC1.attack_steps['attackstep']
    assert c1_attackstep.own_children == {}
    assert c1_attackstep.children == {}

    # attack_step_with_child is defined in parent with target1 as child
    c1_parent_attackstep = assetC1.attack_steps['attack_step_with_child']
    assert c1_parent_attackstep.own_children == {}
    assert c1_parent_attackstep.children.keys() == {EP_target1}

    assert 'attack_step_with_child' in assetC2.attack_steps
    assert 'attackstep' in assetC2.attack_steps
    assert 'target1' in assetC2.attack_steps
    assert 'target2' in assetC2.attack_steps
    assert 'target3' in assetC2.attack_steps
    assert 'target4' in assetC2.attack_steps
    c2_attackstep = assetC2.attack_steps['attackstep']
    assert c2_attackstep.inherits == c1_attackstep
    assert c2_attackstep.own_children == {}

    # attack_step_with_child is defined in grandparent with target1 as child
    c2_parent_attackstep = assetC2.attack_steps['attack_step_with_child']
    assert c2_parent_attackstep.own_children == {}
    assert c2_parent_attackstep.children.keys() == {EP_target1}

    assert 'attack_step_with_child' in assetC3.attack_steps
    assert 'attackstep' in assetC3.attack_steps
    assert 'target1' in assetC3.attack_steps
    assert 'target2' in assetC3.attack_steps
    assert 'target3' in assetC3.attack_steps
    assert 'target4' in assetC3.attack_steps
    c3_attackstep = assetC3.attack_steps['attackstep']
    assert c3_attackstep.inherits == c2_attackstep
    c3_target1 = assetC3.attack_steps['target1']
    c3_target2 = assetC3.attack_steps['target2']
    c3_target3 = assetC3.attack_steps['target3']
    c3_target4 = assetC3.attack_steps['target4']
    assert c3_target1 in c3_attackstep.own_children
    assert c3_target2 not in c3_attackstep.own_children
    assert c3_target3 not in c3_attackstep.own_children
    assert c3_target4 not in c3_attackstep.own_children

    # attack_step_with_child is defined in grandparent with target1 as child
    c3_parent_attackstep = assetC2.attack_steps['attack_step_with_child']
    assert c3_parent_attackstep.own_children == {}
    assert c3_parent_attackstep.children.keys() == {EP_target1}

    assert 'attack_step_with_child' in assetC4.attack_steps
    assert 'attackstep' in assetC4.attack_steps
    assert 'target1' in assetC4.attack_steps
    assert 'target2' in assetC4.attack_steps
    assert 'target3' in assetC4.attack_steps
    assert 'target4' in assetC4.attack_steps
    c4_attackstep = assetC4.attack_steps['attackstep']
    assert c4_attackstep.inherits == c3_attackstep
    assert c4_attackstep.own_children == {}

    # attack_step_with_child is defined in grandparent with target1 as child
    c4_parent_attackstep = assetC2.attack_steps['attack_step_with_child']
    assert c4_parent_attackstep.own_children == {}
    assert c4_parent_attackstep.children.keys() == {EP_target1}

    assert 'attack_step_with_child' in assetC4.attack_steps
    assert 'attackstep' in assetC4.attack_steps
    assert 'target1' in assetC4.attack_steps
    assert 'target2' in assetC4.attack_steps
    assert 'target3' in assetC4.attack_steps
    assert 'target4' in assetC4.attack_steps
    fc_attackstep = assetFC.attack_steps['attackstep']
    assert fc_attackstep.inherits == c4_attackstep
    fc_target1 = assetFC.attack_steps['target1']
    fc_target2 = assetFC.attack_steps['target2']
    fc_target3 = assetFC.attack_steps['target3']
    fc_target4 = assetFC.attack_steps['target4']
    assert fc_target1 in fc_attackstep.own_children
    assert fc_target2 in fc_attackstep.own_children
    assert fc_target3 in fc_attackstep.own_children
    assert fc_target4 in fc_attackstep.own_children

# TODO: Re-enable this test once the compiler and language are compatible with
# one another.
# def test_mallib_mal():
#     LanguageGraph(MalCompiler().compile('tests/testdata/mallib_test.mal'))

def test_probability_distributions():
    lg = LanguageGraph(MalCompiler().compile('tests/testdata/prob_dists.mal'))
    lg.save_to_file('logs/prob_dists_lg.yml')
