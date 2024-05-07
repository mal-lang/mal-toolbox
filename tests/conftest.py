"""Fixtures and helpers used in several test modules"""
import os
import pytest

from maltoolbox.language import specification, LanguageClassesFactory
from maltoolbox.model import Model

def testdata_path(filename):
    """Returns the absolute path of a test data file (in ./testdata)

    Arguments:
    filename    - filename to append to path of ./testdata
    """
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(current_dir, f"testdata/{filename}")


@pytest.fixture
def corelang_spec():
    """Fixture that returns the coreLang language specification as dict"""
    mar_file_path = testdata_path("org.mal-lang.coreLang-1.0.0.mar")
    return specification.load_language_specification_from_mar(mar_file_path)


@pytest.fixture
def example_model(corelang_spec):
    """Fixture that generates a model for tests

    Uses coreLang specification (fixture) to create and return a
    Model object with no assets or associations
    """

    # Init LanguageClassesFactor
    lang_classes_factory = LanguageClassesFactory(corelang_spec)
    lang_classes_factory.create_classes()

    # Create instance model
    return Model('Test model', corelang_spec, lang_classes_factory)
