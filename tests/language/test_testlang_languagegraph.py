"""Tests for the LanguageGraph"""

import pytest
from conftest import path_testdata

from maltoolbox.language.compiler import MalCompiler
from maltoolbox.language import LanguageGraph

def test_languagegraph_save_load(testlang_lang_graph: LanguageGraph):
    """Test to see if saving and loading a language graph to a file produces
    the same language graph. We have to use the json format to save and load
    because YAML reorders the keys in alphabetical order."""
    graph_path = "/tmp/langgraph.yml"
    testlang_lang_graph.save_to_file(graph_path)

    new_lang_graph = LanguageGraph.load_from_file(graph_path)

    assert new_lang_graph._to_dict() == testlang_lang_graph._to_dict()

def test_testlang_interleaved_vars(
        testlang_lang_graph: LanguageGraph):
    """Check to see if two interleaved variables(variables that contain
    variables from each other, A2 contains B1 and B2 contains A1) were
    resolved correct.
    """

    assert 'AssetA' in testlang_lang_graph.assets
    assert 'AssetB' in testlang_lang_graph.assets

    assetA = testlang_lang_graph.assets['AssetA']
    assetB = testlang_lang_graph.assets['AssetB']

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

def test_testLang_inherited_vars():
    LanguageGraph(MalCompiler().compile('tests/testdata/inherited_vars.mal'))
