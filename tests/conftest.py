"""Fixtures and helpers used in several test modules"""
import os
import pytest

from maltoolbox.language import (LanguageGraph, LanguageGraphAsset,
    LanguageGraphAttackStep)
from maltoolbox.model import Model, ModelAsset, ModelAssociation


## Helpers

def path_testdata(filename):
    """Returns the absolute path of a test data file (in ./testdata)

    Arguments:
    filename    - filename to append to path of ./testdata
    """
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(current_dir, f"testdata/{filename}")


def empty_model(name, lang_graph):
    """Fixture that generates a model for tests
    """

    # Create instance model from model json file
    return Model(name, lang_graph)

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

    return empty_model('Test Model', corelang_lang_graph)


@pytest.fixture
def dummy_lang_graph(corelang_lang_graph):
    """Fixture that generates a dummy LanguageGraph with a dummy
    LanguageGraphAsset and LanguageGraphAttackStep
    """
    lang_graph = LanguageGraph()
    dummy_asset = LanguageGraphAsset(
        name = 'DummyAsset'
    )
    lang_graph.assets['DummyAsset'] = dummy_asset
    dummy_attack_step_node = LanguageGraphAttackStep(
        name = 'DummyAttackStep',
        type = 'or',
        asset = dummy_asset
    )
    dummy_asset.attack_steps['DummyAttackStep'] = dummy_attack_step_node


    return lang_graph
