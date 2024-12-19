"""Fixtures and helpers used in several test modules"""
import os
import pytest

from maltoolbox.language import LanguageGraph, LanguageClassesFactory
from maltoolbox.model import Model


## Helpers

def path_testdata(filename):
    """Returns the absolute path of a test data file (in ./testdata)

    Arguments:
    filename    - filename to append to path of ./testdata
    """
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(current_dir, f"testdata/{filename}")


def empty_model(name, lang_classes_factory):
    """Fixture that generates a model for tests

    Uses coreLang specification (fixture) to create and return Model
    """

    # Create instance model from model json file
    return Model(name, lang_classes_factory)

## Fixtures (can be ingested into tests)

@pytest.fixture
def corelang_lang_graph():
    """Fixture that returns the coreLang language specification as dict"""
    mar_file_path = path_testdata("org.mal-lang.coreLang-1.0.0.mar")
    return LanguageGraph.from_mar_archive(mar_file_path)


@pytest.fixture
def model(corelang_lang_graph):
    """Fixture that generates a model for tests

    Uses coreLang specification (fixture) to create and return a
    Model object with no assets or associations
    """
    # Init LanguageClassesFactory
    lang_classes_factory = LanguageClassesFactory(corelang_lang_graph)

    return empty_model('Test Model', lang_classes_factory)

@pytest.fixture
def testlang_lang_graph():
    """Fixture that returns the testLang language specification as dict"""
    mar_file_path = path_testdata("org.mal-lang.testLang-0.0.1.mar")
    return LanguageGraph.from_mar_archive(mar_file_path)


@pytest.fixture
def testlang_model(testlang_lang_graph):
    """Fixture that generates a model for tests

    Uses testLang specification (fixture) to create and return a
    Model object with no assets or associations
    """
    # Init LanguageClassesFactory
    lang_classes_factory = LanguageClassesFactory(testlang_lang_graph)

    return empty_model('Test Model', lang_classes_factory)
