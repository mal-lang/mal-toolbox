"""Unit tests for maltoolbox.model"""

import pytest
from python_jsonschema_objects.validators import ValidationError
from conftest import empty_model, path_testdata

from maltoolbox.model import Model, AttackerAttachment
from maltoolbox.exceptions import ModelAssociationException, DuplicateModelAssociationError

### Helper functions

def create_application_asset(model, name):
    """Helper function to create an asset of coreLang type Application"""
    return model.lang_classes_factory.ns.Application(name=name)


def create_data_asset(model, name):
    """Helper function to create an asset of coreLang type Data"""
    return model.lang_classes_factory.ns.Data(name=name)


def create_association(
        model,
        left_assets,
        right_assets,
        assoc_type="AppExecution",
        left_fieldname="hostApp",
        right_fieldname="appExecutedApps",
    ):
    """Helper function to create an association dict with
    given parameters, useful in tests"""

    # Simulate receiving the association from a json file
    association_dict = {
      assoc_type: {
        left_fieldname: left_assets,
        right_fieldname: right_assets
      }
    }

    # Create the association using the lang_classes_factory
    association = getattr(
            model.lang_classes_factory.ns,
            list(association_dict)[0])()

    # Add the assets
    for field, assets in association_dict[assoc_type].items():
        setattr(association, field, assets)

    return association

### Tests

def test_attacker_attachment_add_entry_point(model: Model):
    """"""

    asset1 = create_application_asset(model, "Asset1")
    asset2 = create_application_asset(model, "Asset2")
    model.add_asset(asset1)
    model.add_asset(asset2)

    # Add attacker 1
    attacker1 = AttackerAttachment()
    model.add_attacker(attacker1)

    attacker1.add_entry_point(asset1, 'read')
    assert len(attacker1.entry_points) == 1
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['read']

    attacker1.add_entry_point(asset1, 'access')
    assert len(attacker1.entry_points) == 1
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['read', 'access']

    # Try to add already existing entry point
    attacker1.add_entry_point(asset1, 'access')
    assert len(attacker1.entry_points) == 1
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['read', 'access']

    attacker1.add_entry_point(asset2, 'access')
    assert len(attacker1.entry_points) == 2
    assert attacker1.entry_points[1][0] == asset2
    assert attacker1.entry_points[1][1] == ['access']


def test_attacker_attachment_remove_entry_point(model: Model):
    """"""

    asset1 = create_application_asset(model, "Asset1")
    asset2 = create_application_asset(model, "Asset2")
    model.add_asset(asset1)
    model.add_asset(asset2)

    # Add attacker 1
    attacker1 = AttackerAttachment()
    model.add_attacker(attacker1)

    attacker1.add_entry_point(asset1, 'read')
    attacker1.add_entry_point(asset1, 'access')
    attacker1.add_entry_point(asset2, 'access')

    assert len(attacker1.entry_points) == 2
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['read', 'access']
    assert attacker1.entry_points[1][0] == asset2
    assert attacker1.entry_points[1][1] == ['access']

    attacker1.remove_entry_point(asset1, 'read')
    assert len(attacker1.entry_points) == 2
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['access']
    assert attacker1.entry_points[1][0] == asset2
    assert attacker1.entry_points[1][1] == ['access']

    # Try to remove inexistent entry point, but the asset is still present in
    # the list of entry points
    attacker1.remove_entry_point(asset1, 'read')
    assert len(attacker1.entry_points) == 2
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['access']
    assert attacker1.entry_points[1][0] == asset2
    assert attacker1.entry_points[1][1] == ['access']

    attacker1.remove_entry_point(asset1, 'access')
    assert len(attacker1.entry_points) == 1
    assert attacker1.entry_points[0][0] == asset2
    assert attacker1.entry_points[0][1] == ['access']

    # Try to remove inexistent entry point, where the asset is no longer in
    # the list of entry points
    attacker1.remove_entry_point(asset1, 'access')
    assert len(attacker1.entry_points) == 1
    assert attacker1.entry_points[0][0] == asset2
    assert attacker1.entry_points[0][1] == ['access']

    attacker1.remove_entry_point(asset2, 'access')
    assert len(attacker1.entry_points) == 0


def test_attacker_attachment_remove_asset(model: Model):
    """"""

    asset1 = create_application_asset(model, "Asset1")
    asset2 = create_application_asset(model, "Asset2")
    model.add_asset(asset1)
    model.add_asset(asset2)

    attacker1 = AttackerAttachment()
    model.add_attacker(attacker1)
    attacker2 = AttackerAttachment()
    model.add_attacker(attacker2)

    attacker1.add_entry_point(asset1, 'read')
    attacker1.add_entry_point(asset1, 'access')
    attacker1.add_entry_point(asset2, 'access')

    attacker2.add_entry_point(asset1, 'read')
    attacker2.add_entry_point(asset2, 'read')
    attacker2.add_entry_point(asset2, 'access')

    assert len(attacker1.entry_points) == 2
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['read', 'access']
    assert attacker1.entry_points[1][0] == asset2
    assert attacker1.entry_points[1][1] == ['access']

    assert len(attacker2.entry_points) == 2
    assert attacker2.entry_points[0][0] == asset1
    assert attacker2.entry_points[0][1] == ['read']
    assert attacker2.entry_points[1][0] == asset2
    assert attacker2.entry_points[1][1] == ['read', 'access']

    model.remove_asset(asset2)
    # All of the entry points of the asset removed should be gone, but the
    # other assets should not be impacted.
    assert len(attacker1.entry_points) == 1
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['read', 'access']

    assert len(attacker2.entry_points) == 1
    assert attacker2.entry_points[0][0] == asset1
    assert attacker2.entry_points[0][1] == ['read']

    # Try to remove inexistent entry point, where the asset is no longer in
    # the list of entry points
    attacker1.remove_entry_point(asset2, 'access')
    assert len(attacker1.entry_points) == 1
    assert attacker1.entry_points[0][0] == asset1
    assert attacker1.entry_points[0][1] == ['read', 'access']

    assert len(attacker2.entry_points) == 1
    assert attacker2.entry_points[0][0] == asset1
    assert attacker2.entry_points[0][1] == ['read']


def test_model_add_asset(model: Model):
    """Make sure assets are added correctly"""

    assets_before = list(model.assets)

    # Create an application asset
    p1 = create_application_asset(model, 'Program 1')
    model.add_asset(p1)

    # Make sure the new asset was added to the model
    assert len(assets_before) + 1 == len(model.assets)
    assert p1 not in assets_before
    assert p1 in model.assets


def test_model_add_asset_with_id_set(model):
    """Make sure assets are added and next_id correctly updated
    when id is set explicitly in method call"""

    p1 = create_application_asset(model, 'Program 1')
    p1_id = model.next_id + 10
    model.add_asset(p1, asset_id=p1_id)

    # Make sure asset was added
    assert p1 in model.assets

    # Make sure next_id was incremented
    assert model.next_id == p1_id + 1

    # Add asset with same ID as previously added asset, expect ValueError
    p2 = create_application_asset(model, 'Program 2')
    with pytest.raises(ValueError):
        model.add_asset(p2, asset_id=p1_id)

    assert p2 not in model.assets


def test_model_add_asset_duplicate_name(model: Model):
    """Add several assets with the same name to the model"""

    asset_name = "MyProgram"

    # Add a new asset
    p1 = create_application_asset(model, asset_name)
    model.add_asset(p1)
    assert len(model.assets) == 1
    assert model.assets[0].name == asset_name

    # Add with same name again (allowed by default)
    p2 = create_application_asset(model, asset_name)
    model.add_asset(p2)
    assert len(model.assets) == 2
    # Is this expected - shouldn't p2 have same name as p1?
    assert model.assets[1].name == f"{asset_name}:{p2.id}"

    # Add asset again while not allowing duplicates, expect ValueError
    with pytest.raises(ValueError):
        model.add_asset(p1, allow_duplicate_names=False)
    # Make sure there are still only two assets named 'Program 1'
    assert len(model.assets) == 2


def test_model_remove_asset(model: Model):
    """Remove assets from a model"""

    # Add two program assets to the model
    p1 = create_application_asset(model, 'Program 1')
    p2 = create_application_asset(model, 'Program 2')
    model.add_asset(p1)
    model.add_asset(p2)

    num_assets_before = len(model.assets)
    model.remove_asset(p1)

    # Make sure asset p1 was deleted, but p2 still exists
    assert p1 not in model.assets
    assert p2 in model.assets
    assert len(model.assets) == num_assets_before - 1


def test_model_remove_nonexisting_asset(model: Model):
    """Removing a non existing asset leads to lookup error"""

    # Create an asset but don't add it to the model before removing it
    p1 = create_application_asset(model, 'Program 1')
    p1.id = 1  # Needs id to avoid crash in log statement
    with pytest.raises(LookupError):
        model.remove_asset(p1)


def test_model_add_association(model: Model):
    """Make sure associations work as intended"""

    # Create two assets
    p1 = create_application_asset(model, 'Program 1')
    p1_id = model.next_id
    p2 = create_application_asset(model, 'Program 2')
    p2_id = p1_id + 1

    # Add the assets with explicit IDs to keep track of them
    model.add_asset(p1, asset_id=p1_id)
    model.add_asset(p2, asset_id=p2_id)

    # Create an association between p1 and p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )

    associations_before = list(model.associations)
    # Add the association to the model
    model.add_association(association)
    associations_after = list(model.associations)

    # Make sure association was added to the model and assets
    assert len(associations_before) == len(associations_after) - 1
    assert association not in associations_before
    assert association in associations_after
    assert association in p1.associations
    assert association in p2.associations


def test_model_add_appexecution_association_two_assets(model: Model):
    """coreLang specifies that AppExecution only can have one 'left' asset"""

    # Add program assets
    p1 = create_application_asset(model, 'Program 1')
    p1_id = model.next_id
    p2 = create_application_asset(model, 'Program 2')
    p2_id = p1_id + 1
    model.add_asset(p1, asset_id=p1_id)
    model.add_asset(p2, asset_id=p2_id)

    # Try create an association between (p1, p2) and p1
    with pytest.raises(ValidationError):
        # will raise error because two assets (p1,p2)
        # are not allowed in the left field for AppExecution
        create_association(
            model, assoc_type="AppExecution",
            left_fieldname="hostApp", right_fieldname="appExecutedApps",
            left_assets=[p1, p2], right_assets=[p1]
        )


def test_model_add_association_duplicate(model: Model):
    """Make sure same association is not added twice"""

    # Create three data assets
    d1 = create_data_asset(model, 'Data 1')
    d1_id = model.next_id
    d2 = create_data_asset(model, 'Data 2')
    d2_id = d1_id + 1
    d3 = create_data_asset(model, 'Data 3')
    d3_id = d2_id + 1

    # Add the assets with explicit IDs to keep track of them
    model.add_asset(d1, asset_id=d1_id)
    model.add_asset(d2, asset_id=d2_id)
    model.add_asset(d3, asset_id=d3_id)

    # Create an association between (d1, d2) and d3
    association1 = create_association(
        model, assoc_type="DataContainment",
        left_fieldname="containingData", right_fieldname="containedData",
        left_assets=[d1, d2], right_assets=[d3]
    )
    # Create an identical association, but from just d2
    association2 = create_association(
        model, assoc_type="DataContainment",
        left_fieldname="containingData", right_fieldname="containedData",
        left_assets=[d2], right_assets=[d3]
    )
    # Create association with duplicate assets in both fields
    association3 = create_association(
        model, assoc_type="DataContainment",
        left_fieldname="containingData", right_fieldname="containedData",
        left_assets=[d2, d2], right_assets=[d3, d3]
    )

    # Add the first association to the model - no problem
    model.add_association(association1)
    assert len(model.associations) == 1

    # Add the first association again - should fail because duplicate
    # associations are not allowed
    with pytest.raises(DuplicateModelAssociationError) as e:
        model.add_association(association1)

    assert str(e.value) == (
        'Identical association DataContainment already exists'
    )

    # Add the second (almost identical) association.
    # Should fail because it contains d2 to d3 association
    # which already was added by association1
    with pytest.raises(DuplicateModelAssociationError) as e:
        model.add_association(association2)

    assert str(e.value) == (
        "Association type DataContainment already exists"
        " between Data 2 and Data 3"
    )

    # Add the third association, should fail because of duplicate
    # assets in fields
    with pytest.raises(ModelAssociationException):
        model.add_association(association3)

    assert len(model.associations) == 1

def test_model_remove_association(model: Model):
    """Make sure association can be removed"""

    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )

    model.add_association(association)
    assert association in model.associations
    assert association in p1.associations
    assert association in p2.associations
    assert "AppExecution" in model._type_to_association
    assert model._type_to_association["AppExecution"]
    assert association in model._type_to_association["AppExecution"]

    # Remove the association and make sure it was
    # removed from assets and model
    model.remove_association(association)
    assert "AppExecution" not in model._type_to_association
    assert association not in model.associations
    assert association not in p1.associations
    assert association not in p2.associations


def test_model_remove_association_nonexisting(model: Model):
    """Make sure non existing association can not be removed"""
    # Create the association but don't add it
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[], right_assets=[]
    )

    # No associations exists
    assert model.associations == []

    # So we should expect a LookupError when trying to remove one
    with pytest.raises(LookupError):
        model.remove_association(association)


def test_model_remove_asset_from_association(model: Model):
    """Make sure we can remove asset from association and that
    associations with no assets on any 'side' is removed"""

    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    # Create and add association from p1 to p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )
    model.add_association(association)

    # We are removing p1 from association so one side will be empty
    # This means the association should be removed entirely
    model.remove_asset_from_association(p1, association)
    assert association not in p2.associations
    assert association not in p1.associations
    assert association not in model.associations


def test_model_remove_asset_from_association_nonexisting_asset(
        model: Model
    ):
    """Make sure error is thrown if deleting non existing asset
    from association"""

    # Create 4 applications and add 3 of them to model
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    p3 = create_application_asset(model, "Program 3")
    p4 = create_application_asset(model, 'Program 4')
    model.add_asset(p1)
    model.add_asset(p2)
    model.add_asset(p3)
    p4.id = 1 # ID is required, otherwise crash in log statement

    # Create an association between p1 and p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )
    model.add_association(association)

    # We are removing p3 from association where it does not exist
    with pytest.raises(LookupError):
        model.remove_asset_from_association(p3, association)

    # We are removing p4 from association, but p4
    # does not exist in the model
    with pytest.raises(LookupError):
        model.remove_asset_from_association(p4, association)


def test_model_remove_asset_from_association_nonexisting_association(
        model: Model
    ):
    """Make sure error is thrown if deleting non existing asset
    from association"""

    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    # Create (but don't add!) an association between p1 and p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )
    # We are removing an association that was never created -> LookupError
    with pytest.raises(LookupError):
        model.remove_asset_from_association(p1, association)


def test_model_add_attacker(model: Model):
    """Test functionality to add an attacker to the model"""

    # Add attacker 1
    attacker1 = AttackerAttachment()
    attacker1.entry_points = []
    model.add_attacker(attacker1)
    assert attacker1.name == f'Attacker:{attacker1.id}'

    # Add attacker 2 with explicit id set (can be duplicate id)
    attacker2_id = attacker1.id
    attacker2 = AttackerAttachment()
    attacker2.entry_points = []
    model.add_attacker(attacker2, attacker_id=attacker2_id)

    # Add attacker 2 with explicit id set (can be duplicate id)
    attacker2_id = attacker1.id
    attacker2 = AttackerAttachment()

    asset_id = 1
    attack_steps = ['attemptCredentialsReuse']
    attacker2.entry_points = [
        (asset_id, attack_steps)
    ]
    model.add_attacker(attacker2, attacker_id=attacker2_id)


    assert attacker2.name == f'Attacker:{attacker2_id}'


def test_model_get_asset_by_id(model: Model):
    """Make sure correct asset is returned or None
    if no asset with that ID exists"""

    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    # Correct assets removed and None if asset with that not exists
    assert model.get_asset_by_id(p1.id) == p1
    assert model.get_asset_by_id(p2.id) == p2
    assert model.get_asset_by_id(1337) is None


def test_model_get_asset_by_name(model: Model):
    """Make sure correct asset is returned or None
    if no asset with that name exists"""

    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    # Correct assets removed and None if asset with that name not exists
    assert model.get_asset_by_name(p1.name) == p1
    assert model.get_asset_by_name(p2.name) == p2
    assert model.get_asset_by_name("Program 3") is None


def test_model_get_attacker_by_id(model: Model):
    """Make sure correct attacker is returned of None
    if no attacker with that ID exists"""

    # Add attacker 1
    attacker1 = AttackerAttachment()
    attacker1.entry_points = []
    model.add_attacker(attacker1)

    assert attacker1.id is not None
    assert model.get_attacker_by_id(attacker1.id) == attacker1
    assert model.get_attacker_by_id(1337) is None


def test_model_get_associated_assets_by_fieldname(model: Model):
    """Make sure assets associated to the asset through the given
    field_name are returned"""

    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    # Create and add an association between p1 and p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )
    model.add_association(association)

    # Since p2 is in an association with p1 through 'appExecutedApps'
    # p2 should be returned as an associated asset
    ret = model.get_associated_assets_by_field_name(
        p1, "appExecutedApps")
    assert p2 in ret

    # Other fieldname from p2 to p1
    ret = model.get_associated_assets_by_field_name(
        p2, "hostApp")
    assert p1 in ret

    # Non existing field name should give no assets
    ret = model.get_associated_assets_by_field_name(
        p1, "bogusFieldName")
    assert ret == []


def test_model_asset_to_dict(model: Model):
    """Make sure assets are converted to dictionaries correctly"""
    # Create and add asset
    p1 = create_application_asset(model, "Program 1")
    model.add_asset(p1)

    # Tuple is returned
    ret = model.asset_to_dict(p1)

    # First element should be the id
    p1_id = ret[0]
    assert p1_id == p1.id

    # Second element is the dict, each value should
    # be set as below for an 'Application' asset in coreLang
    p1_dict = ret[1]
    assert p1_dict.get('name') == p1.name
    assert p1_dict.get('type') == 'Application'

    # Default values should not be saved
    assert p1_dict.get('defenses') == None

def test_model_asset_with_nondefault_defense_to_dict(model: Model):
    """Make sure assets are converted to dictionaries correctly"""
    # Create and add asset
    p1 = create_application_asset(model, "Program 1")
    p1.notPresent = 1.0
    model.add_asset(p1)

    # Tuple is returned
    ret = model.asset_to_dict(p1)

    # First element should be the id
    p1_id = ret[0]
    assert p1_id == p1.id

    # Second element is the dict, each value should
    # be set as below for an 'Application' asset in coreLang
    p1_dict = ret[1]
    assert p1_dict.get('name') == p1.name
    assert p1_dict.get('type') == 'Application'

    # Default values for 'Application' defenses in coreLang
    assert p1_dict.get('defenses') == {
        'notPresent': 1.0
    }


def test_model_association_to_dict(model: Model):
    """Make sure associations are converted to dictionaries correctly"""
    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    # Create and add an association between p1 and p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )
    model.add_association(association)

    association_dict = model.association_to_dict(association)
    association_type = list(association_dict.keys())[0]
    assert association_type == 'AppExecution'
    assert association_dict[association_type ] == {
        'hostApp': [p1.id],
        'appExecutedApps': [p2.id]
    }


def test_model_attacker_to_dict(model: Model):
    """Make sure attackers get correct format and values"""

    # Create and add an asset
    p1 = create_application_asset(model, "Program 1")
    model.add_asset(p1)

    # Add attacker 1
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (p1, attack_steps)
    ]
    model.add_attacker(attacker)

    # Convert the attacker to a dictionary and make sure
    # id and name were converted correctly
    ret = model.attacker_to_dict(attacker)
    assert ret[0] == attacker.id
    attacker_dict = ret[1]
    assert attacker_dict.get('name') == attacker.name

    # entry_points_dict has asset IDs as keys
    entry_points_dict = attacker_dict.get('entry_points')

    # attacker should be attached to p1, therefore p1s
    # id should be a key in the entry_points_dict
    assert p1.id is not None and entry_points_dict
    assert p1.id in entry_points_dict

    # The given steps should be inside the entry_point of
    # the attacker for asset p1
    assert entry_points_dict[p1.id]['attack_steps'] == attack_steps


def test_serialize(model: Model):
    """Put all to_dict methods together and see that they work"""

    # Create and add 3 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    p3 = create_application_asset(model, "Program 3")
    model.add_asset(p1)
    model.add_asset(p2)
    model.add_asset(p3)

    # Create and add an association between p1 and p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )
    model.add_association(association)

    # Add attacker
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (p1, attack_steps)
    ]
    model.add_attacker(attacker)

    model_dict = model._to_dict()

    # to_dict will create map from asset id to asset dict
    # (dict is second value of tuple returned from asset_to_dict)
    for asset in [p1, p2, p3]:
        assert model_dict['assets'][asset.id] == \
        model.asset_to_dict(asset)[1]

    # associations are added as they are created by association_to_dict
    assert model_dict['associations'] == \
        [model.association_to_dict(association)]

    # attackers are added similar to assets (id maps to attacker dict)
    assert model_dict['attackers'][attacker.id] == \
        model.attacker_to_dict(attacker)[1]

    # Meta data should also be added
    assert model_dict['metadata']['name'] == model.name
    assert model_dict['metadata']['langVersion'] == \
        model.lang_classes_factory.lang_graph.metadata['version']
    assert model_dict['metadata']['langID'] == \
        model.lang_classes_factory.lang_graph.metadata['id']


def test_model_save_and_load_model_from_scratch(model: Model):
    """Create a model, save it to file, load it from file and compare them
    Note: will create file in /tmp
    """

    # Create and add 3 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    p3 = create_application_asset(model, "Program 3")
    model.add_asset(p1)
    model.add_asset(p2)
    model.add_asset(p3)

    # Create and add an association between p1 and p2
    association = create_association(
        model, assoc_type="AppExecution",
        left_fieldname="hostApp", right_fieldname="appExecutedApps",
        left_assets=[p1], right_assets=[p2]
    )
    model.add_association(association)

    # Add attacker
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (p1, attack_steps)
    ]
    model.add_attacker(attacker)

    for model_path in ("/tmp/test.json", "/tmp/test.yaml", "/tmp/test.yml"):
        # Mock open() function so no real files are written to filesystem
        model.save_to_file(model_path)

        # Create a new model by loading old model from file
        new_model = Model.load_from_file(
            model_path,
            model.lang_classes_factory
        )

        assert new_model._to_dict() == model._to_dict()


def test_model_save_and_load_model_example_model(model):
    """Load the simple_example_model.json from testdata, store it, compare
    Note: will create file in /tmp"""

    # Load from example file
    model = Model.load_from_file(
        path_testdata("simple_example_model.json"),
        model.lang_classes_factory
    )

    # Save to file
    model.save_to_file('/tmp/test.json')

    # Create new model and load from previously saved file
    new_model = Model.load_from_file(
        '/tmp/test.json',
        model.lang_classes_factory
    )

    assert new_model._to_dict() == model._to_dict()

def test_model_load_older_version_example_model(model):
    """Load the older_version_example_model.json from testdata, and check if
    its version is correct"""

    # Load from example file
    model = Model.load_from_file(
        path_testdata("older_version_example_model.json"),
        model.lang_classes_factory
    )

    assert model.maltoolbox_version == '0.0.38'
