"""Unit tests for maltoolbox.model"""

import pytest

from maltoolbox.model import Model


def create_application_asset(model, name):
    """Helper function to create an asset of coreLang type Application"""
    return model.lang_classes_factory.ns.Application(name=name)


def create_association(
        model,
        metaconcept,
        from_fieldname,
        to_fieldname,
        from_assets,
        to_assets
    ):
    """Helper function to create an association dict with
    given parameters, useful in tests"""

    # Simulate receving the association from a json file
    association_dict = {
      "metaconcept": metaconcept,
      "association": {
        from_fieldname: from_assets,
        to_fieldname: to_assets
      }
    }

    # Create the association using the lang_classes_factory
    association = getattr(
        model.lang_classes_factory.ns,
        association_dict['metaconcept'])()

    # Add the assets
    for field, assets in association_dict['association'].items():
        setattr(association, field, assets)

    return association


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
    program1.id = 1  # Needs id to avoid crash in log statement
    with pytest.raises(LookupError):
        example_model.remove_asset(program1)


def test_model_add_association(example_model: Model):
    """Make sure associations work as intended"""

    # Create two assets
    program1 = create_application_asset(example_model, 'Program 1')
    program1_id = example_model.latestId
    program2 = create_application_asset(example_model, 'Program 2')
    program2_id = program1_id + 1

    # Add the assets with explicit IDs to keep track of them
    example_model.add_asset(program1, asset_id=program1_id)
    example_model.add_asset(program2, asset_id=program2_id)

    # Create an association between program1 and program2
    association = create_association(
        example_model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[program1], to_assets=[program2]
    )

    associations_before = list(example_model.associations)
    # Add the association to the model
    example_model.add_association(association)
    associations_after = list(example_model.associations)

    # Make sure association was added to the model and assets
    assert len(associations_before) == len(associations_after) - 1
    assert association not in associations_before
    assert association in associations_after
    assert association in program1.associations
    assert association in program2.associations


def test_model_remove_association(example_model: Model):
    """Make sure association can be removed"""

    # Create and add 2 applications
    p1 = create_application_asset(example_model, "Program 1")
    p2 = create_application_asset(example_model, "Program 2")
    example_model.add_asset(p1)
    example_model.add_asset(p2)

    association = create_association(
        example_model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
    )

    example_model.add_association(association)
    assert association in example_model.associations
    assert association in p1.associations
    assert association in p2.associations

    # Remove the association and make sure it was
    # removed from assets and model
    example_model.remove_association(association)
    assert association not in example_model.associations
    assert association not in p1.associations
    assert association not in p2.associations


def test_model_remove_association_nonexisting(example_model: Model):
    """Make sure non existing association can not be removed"""
    # Create the association but don't add it
    association = create_association(
        example_model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[], to_assets=[]
    )

    # No associations exists
    assert example_model.associations == []

    # So we should expect a LookupError when trying to remove one
    with pytest.raises(LookupError):
        example_model.remove_association(association)
