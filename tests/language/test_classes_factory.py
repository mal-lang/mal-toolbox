"""Tests for the LanguageGraph."""

from maltoolbox.language import LanguageClassesFactory, LanguageGraph


def test_corelang_classes_factory(corelang_lang_graph: LanguageGraph) -> None:
    """Test to see if the LanguageClassesFactory is properly generated based
    on coreLang Language Graph.
    """
    # Init LanguageClassesFactory
    lang_classes_factory = LanguageClassesFactory(corelang_lang_graph)

    assert hasattr(lang_classes_factory.ns, 'Asset_Application')
    assert hasattr(
        lang_classes_factory.ns,
        'Association_ApplicationVulnerability_vulnerabilities_application',
    )


def test_create_asset(corelang_lang_graph: LanguageGraph) -> None:
    # Init LanguageClassesFactory
    LanguageClassesFactory(corelang_lang_graph)
