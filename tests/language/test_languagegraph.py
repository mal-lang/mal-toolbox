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

# TODO: Re-enable this test once the compiler and language are compatible with
# one another.
# def test_mallib_mal():
#     LanguageGraph(MalCompiler().compile('tests/testdata/mallib_test.mal'))
