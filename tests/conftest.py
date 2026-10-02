"""Fixtures and helpers used in several test modules"""

import os

import pytest

from maltoolbox.attackgraph import AttackGraph
from maltoolbox.language import LanguageGraph
from maltoolbox.model import Model

# Helpers


def path_testdata(filename):
    """Returns the absolute path of a test data file (in ./testdata)

    Arguments:
    ---------
    filename    - filename to append to path of ./testdata

    """
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(current_dir, f'testdata/{filename}')


def empty_model(name, lang_graph):
    """Fixture that generates a model for tests"""
    # Create instance model from model json file
    return Model(name, lang_graph)


# Fixtures (can be ingested into tests)


@pytest.fixture
def corelang_lang_graph():
    """Fixture that returns the coreLang language specification as dict"""
    mar_file_path = path_testdata('org.mal-lang.coreLang-1.0.0.mar')
    return LanguageGraph.from_mar_archive(mar_file_path)


@pytest.fixture
def model(corelang_lang_graph):
    """Fixture that generates a model for tests

    Uses coreLang specification (fixture) to create and return a
    Model object with no assets or associations
    """
    return empty_model('Test Model', corelang_lang_graph)


@pytest.fixture
def dummy_lang_graph():
    """Fixture that generates a dummy LanguageGraph with a dummy
    LanguageGraphAsset ('DummyAsset') and one LanguageGraphAttackStep of
    each type ('DummyOrAttackStep'/'DummyAndAttackStep'/
    'DummyDefenseAttackStep'/'DummyExistAttackStep'/
    'DummyNotExistAttackStep'), compiled from a real minimal .mal spec
    (testdata/dummy_lang.mal) rather than hand-built dataclass instances -
    the latter has no backing LanguageGraph, which the Rust-backed
    bindings' owner+id handle design can't represent (see
    PYTHON_BINDINGS_IMPLEMENTATION.md).
    """
    return LanguageGraph.from_mal_spec(path_testdata('dummy_lang.mal'))


@pytest.fixture
def example_attackgraph(corelang_lang_graph: LanguageGraph, model: Model):
    """Fixture that generates an example attack graph

    Uses coreLang specification and model with two applications
    with an association to create and return an AttackGraph object
    """
    # Create 2 assets
    app1 = model.add_asset(asset_type='Application', name='Application 1')
    app2 = model.add_asset(asset_type='Application', name='Application 2')

    # Create association between app1 and app2
    app1.add_associated_assets(fieldname='appExecutedApps', assets={app2})

    return AttackGraph(lang_graph=corelang_lang_graph, model=model)


@pytest.fixture
def example_model(corelang_lang_graph: LanguageGraph):
    """Fixture that generates an example model

    Uses coreLang specification to create and return a Model object
    with two applications with an association
    """
    model = Model(name='Example Model', lang_graph=corelang_lang_graph)
    app1 = model.add_asset(asset_type='Application', name='Application 1')
    app2 = model.add_asset(asset_type='Application', name='Application 2')
    app1.add_associated_assets(fieldname='appExecutedApps', assets={app2})

    return model


@pytest.fixture
def trainingLang_lang_graph():
    """Fixture that returns the trainingLang language specification as dict"""
    mar_file_path = path_testdata('org.mal-lang.trainingLang-1.0.0.mar')
    return LanguageGraph.from_mar_archive(mar_file_path)


@pytest.fixture
def assocChainLang_lang_graph():
    """Fixture that returns the assocChainLang language specification as dict"""
    mal_file_path = path_testdata('assocChainLang.mal')
    return LanguageGraph.load_from_file(mal_file_path)