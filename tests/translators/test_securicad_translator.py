"""Unit tests for AttackGraph functionality"""

import pytest

from conftest import path_testdata

from maltoolbox.model import Model
from maltoolbox.translators import securicad

# TODO Re-enable this when the securicad translator has been updated.
# def test_securicad_translator(corelang_lang_graph):
#     """Test that we can load old securiCAD models """
#     scad_file = path_testdata("example_model.sCAD")
#     lang_classes_factory = LanguageClassesFactory(corelang_lang_graph)
#     scad_model = securicad.load_model_from_scad_archive(
#         scad_file,
#         corelang_lang_graph,
#         lang_classes_factory
#     )
#
#     assert len(scad_model.assets) > 0
#
#     scad_model_dict = scad_model._to_dict()
#
#     regular_model = Model.load_from_file(
#         path_testdata("scad_equivalent_model.yml"),
#         lang_classes_factory
#     )
#
#     assert len(regular_model.assets) > 0
#
#     regular_model_dict = regular_model._to_dict()
#
#     # Remove metadata as it is likely to mismatch quite often due to
#     # irrelevant reasons.
#     del regular_model_dict['metadata']
#     del scad_model_dict['metadata']
#
#     assert regular_model_dict == scad_model_dict
