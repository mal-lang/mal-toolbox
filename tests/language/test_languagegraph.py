"""Tests for the LanguageGraph"""

import pytest
from conftest import path_testdata

from maltoolbox.language import LanguageGraph

def test_languagegraph_save_load(corelang_lang_graph: LanguageGraph):
    """Not implemented yet"""
    for graph_path in (
        "/tmp/langgraph.json", "/tmp/langgraph.yml", "/tmp/langgraph.yaml"
        ):
        corelang_lang_graph.save_to_file(graph_path)

        # This feature is not implemented yet, update test when implemented
        with pytest.raises(NotImplementedError):
            new_lang_graph = LanguageGraph.load_from_file(graph_path)
            assert new_lang_graph._to_dict() == corelang_lang_graph._to_dict()

def test_corelang_with_union_different_assets_same_super_asset():
    """Uses edited coreLang language specification.
    An attackstep in IAMObject will contain a union between
    Identity and Group, which should be allowed, since they
    share the same super asset.
    """

    mar_file_path = path_testdata("corelang-union-common-ancestor.mar")

    # Make sure that it can generate
    LanguageGraph.from_mar_archive(mar_file_path)
