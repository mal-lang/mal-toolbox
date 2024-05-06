"""Unit tests for maltoolbox.model"""

import pytest

from maltoolbox.model import Model


def create_application_asset(model, name):
    """Helper function to create an asset of coreLang type Application"""
    return model.lang_classes_factory.ns.Application(name=name)


def test_model_add_asset(example_model: Model):
    """Make sure assets are added correctly"""

    assets_before = list(example_model.assets)

    # Create an application asset
    program1 = create_application_asset(example_model, 'Program 1')
    example_model.add_asset(program1)

    # Make sure the new asset was added to the model
    assert len(assets_before) + 1 == len(example_model.assets)
    assert program1 not in assets_before
    assert program1 in example_model.assets


def test_model_add_asset_with_id_set(example_model):
    """Make sure assets are added and latestId correctly updated
    when id is set explicitly in method call"""

    program1 = create_application_asset(example_model, 'Program 1')
    program1_id = example_model.latestId + 10
    example_model.add_asset(program1, asset_id=program1_id)

    # Make sure latestId was updated accordingly
    # TODO: should it be called next_id instead?
    assert example_model.latestId == program1_id + 1

    # Add asset with same ID as previously added asset, expect ValueError
    program2 = create_application_asset(example_model, 'Program 2')
    with pytest.raises(ValueError):
        example_model.add_asset(program2, asset_id=program1_id)


def test_model_add_duplicate_name(example_model: Model):
    """Add several assets with the same name to the model"""

    # Add a new asset (Program 4)
    program1 = create_application_asset(example_model, 'Program 1')
    example_model.add_asset(program1)
    assert example_model.assets.count(program1) == 1

    # Add asset again (will lead to duplicate name, allowed by default)
    example_model.add_asset(program1)
    assert example_model.assets.count(program1) == 2

    # Add asset again while not allowing duplicates, expect ValueError
    with pytest.raises(ValueError):
        example_model.add_asset(program1, allow_duplicate_names=False)
    # Make sure there are still only two assets named 'Program 1'
    assert example_model.assets.count(program1) == 2


def test_model_remove_asset():
    pass
