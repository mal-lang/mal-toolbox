"""Fixtures and helpers used in several test modules"""
import os
import pytest

from maltoolbox.language import (LanguageGraph, LanguageGraphAsset,
    LanguageGraphAttackStep)
from maltoolbox.model import Model
from maltoolbox.attackgraph import AttackGraph


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

## Fixtures (can be ingested into tests)

@pytest.fixture
def corelang_spec():
    """Fixture that returns the coreLang language specification as dict"""
    mar_file_path = path_testdata("org.mal-lang.coreLang-1.0.0.mar")
    return specification.load_language_specification_from_mar(mar_file_path)


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
    dummy_or_attack_step_node = LanguageGraphAttackStep(
        name = 'DummyOrAttackStep',
        type = 'or',
        asset = dummy_asset
    )
    dummy_asset.attack_steps['DummyOrAttackStep'] = dummy_or_attack_step_node

    dummy_and_attack_step_node = LanguageGraphAttackStep(
        name = 'DummyAndAttackStep',
        type = 'and',
        asset = dummy_asset
    )
    dummy_asset.attack_steps['DummyAndAttackStep'] =\
        dummy_and_attack_step_node

    dummy_defense_attack_step_node = LanguageGraphAttackStep(
        name = 'DummyDefenseAttackStep',
        type = 'defense',
        asset = dummy_asset
    )
    dummy_asset.attack_steps['DummyDefenseAttackStep'] =\
        dummy_defense_attack_step_node

    dummy_exist_attack_step_node = LanguageGraphAttackStep(
        name = 'DummyExistAttackStep',
        type = 'exist',
        asset = dummy_asset
    )
    dummy_asset.attack_steps['DummyExistAttackStep'] =\
        dummy_exist_attack_step_node

    dummy_exist_attack_step_node = LanguageGraphAttackStep(
        name = 'DummyNotExistAttackStep',
        type = 'notExist',
        asset = dummy_asset
    )
    dummy_asset.attack_steps['DummyNotExistAttackStep'] =\
        dummy_exist_attack_step_node
    return lang_graph


@pytest.fixture
def example_attackgraph(corelang_lang_graph: LanguageGraph, model: Model):
    """Fixture that generates an example attack graph

    Uses coreLang specification and model with two applications
    with an association to create and return an AttackGraph object
    """

    # Create 2 assets
    app1 = model.add_asset(asset_type = 'Application', name = 'Application 1')
    app2 = model.add_asset(asset_type = 'Application', name = 'Application 2')

    # Create association between app1 and app2
    app1.add_associated_assets(fieldname='appExecutedApps', assets={app2})

    return AttackGraph(
        lang_graph=corelang_lang_graph,
        model=model
    )
