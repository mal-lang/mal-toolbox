"""Tests for the LanguageGraph"""

import pytest
from conftest import path_testdata

from maltoolbox.language import LanguageGraph, LanguageClassesFactory

def test_corelang_classes_factory(corelang_lang_graph: LanguageGraph):
    """ Test to see if the LanguageClassesFactory is properly generated based
    on coreLang Language Graph.
    """
    # Init LanguageClassesFactory
    lang_classes_factory = LanguageClassesFactory(corelang_lang_graph)

    assert hasattr(lang_classes_factory.ns, 'Asset_Application')
    assert hasattr(lang_classes_factory.ns, 'Association_ApplicationVulnerability_vulnerabilities_SoftwareVulnerability_application_Application')

def test_create_asset(corelang_lang_graph: LanguageGraph):
    # Init LanguageClassesFactory
    lang_classes_factory = LanguageClassesFactory(corelang_lang_graph)
