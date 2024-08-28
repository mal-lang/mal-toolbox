"""Tests for the LanguageGraph"""

import pytest
from conftest import path_testdata

from maltoolbox.language import LanguageGraph

def test_languagegraph_save_load(corelang_lang_graph: LanguageGraph):
    """Test to see if saving and loading a language graph to a file produces
    the same language graph. We have to use the json format to save and load
    because YAML reorders the keys in alphabetical order."""
    graph_path = "/tmp/langgraph.json"
    corelang_lang_graph.save_to_file(graph_path)

    new_lang_graph = LanguageGraph.load_from_file(graph_path)

    assert new_lang_graph._to_dict() == corelang_lang_graph._to_dict()

def test_corelang_with_union_different_assets_same_super_asset():
    """Uses modified coreLang language specification.
    An attackstep in IAMObject will contain a union between
    Identity and Group, which should be allowed, since they
    share the same super asset.
    """

    mar_file_path = path_testdata("corelang-union-common-ancestor.mar")

    # Make sure that it can generate
    LanguageGraph.from_mar_archive(mar_file_path)
