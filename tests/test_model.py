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

    assert program1 in example_model.assets

    # Make sure latestId was incremented
    # TODO: should it be called next_id or next_asset_id instead?
    assert example_model.latestId == program1_id + 1

    # Add asset with same ID as previously added asset, expect ValueError
    program2 = create_application_asset(example_model, 'Program 2')
    with pytest.raises(ValueError):
        example_model.add_asset(program2, asset_id=program1_id)

    assert program2 not in example_model.assets


def test_model_add_asset_duplicate_name(example_model: Model):
    """Add several assets with the same name to the model"""

    # Add a new asset
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


def test_model_remove_asset(example_model: Model):
    """Remove assets from a model"""

    # Add two program assets to the model
    program1 = create_application_asset(example_model, 'Program 1')
    program2 = create_application_asset(example_model, 'Program 2')
    example_model.add_asset(program1)
    example_model.add_asset(program2)

    num_assets_before = len(example_model.assets)
    example_model.remove_asset(program1)

    # Make sure asset program1 was deleted, but program2 still exists
    assert program1 not in example_model.assets
    assert program2 in example_model.assets
    assert len(example_model.assets) == num_assets_before - 1


def test_model_remove_nonexisting_asset(example_model: Model):
    """Removing a non existing asset leads to lookup error"""

    # Create an asset but don't add it to the model before removing it
    program1 = create_application_asset(example_model, 'Program 1')
    with pytest.raises(LookupError):
        example_model.remove_asset(program1)
