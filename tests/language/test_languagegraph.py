"""Tests for the LanguageGraph"""

import pytest
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
