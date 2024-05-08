"""Unit tests for maltoolbox.model"""

import pytest

from conftest import empty_model, path_testdata
from maltoolbox.model import Model, AttackerAttachment


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
    """Make sure assets are added and latestId correctly updated
    when id is set explicitly in method call"""

    p1 = create_application_asset(model, 'Program 1')
    p1_id = model.latestId + 10
    model.add_asset(p1, asset_id=p1_id)

    # Make sure asset was added
    assert p1 in model.assets

    # Make sure latestId was incremented
    # TODO: should it be called next_id or next_asset_id instead?
    assert model.latestId == p1_id + 1

    # Add asset with same ID as previously added asset, expect ValueError
    p2 = create_application_asset(model, 'Program 2')
    with pytest.raises(ValueError):
        model.add_asset(p2, asset_id=p1_id)

    assert p2 not in model.assets


def test_model_add_asset_duplicate_name(model: Model):
    """Add several assets with the same name to the model"""

    # Add a new asset
    p1 = create_application_asset(model, 'Program 1')
    model.add_asset(p1)
    assert model.assets.count(p1) == 1

    # Add asset again (will lead to duplicate name, allowed by default)
    model.add_asset(p1)
    assert model.assets.count(p1) == 2

    # Add asset again while not allowing duplicates, expect ValueError
    with pytest.raises(ValueError):
        model.add_asset(p1, allow_duplicate_names=False)
    # Make sure there are still only two assets named 'Program 1'
    assert model.assets.count(p1) == 2


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
    p1_id = model.latestId
    p2 = create_application_asset(model, 'Program 2')
    p2_id = p1_id + 1

    # Add the assets with explicit IDs to keep track of them
    model.add_asset(p1, asset_id=p1_id)
    model.add_asset(p2, asset_id=p2_id)

    # Create an association between p1 and p2
    association = create_association(
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
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


def test_model_remove_association(model: Model):
    """Make sure association can be removed"""

    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    association = create_association(
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
    )

    model.add_association(association)
    assert association in model.associations
    assert association in p1.associations
    assert association in p2.associations

    # Remove the association and make sure it was
    # removed from assets and model
    model.remove_association(association)
    assert association not in model.associations
    assert association not in p1.associations
    assert association not in p2.associations


def test_model_remove_association_nonexisting(model: Model):
    """Make sure non existing association can not be removed"""
    # Create the association but don't add it
    association = create_association(
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[], to_assets=[]
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
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
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
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
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
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
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
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
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


def test_model_asset_to_json(model: Model):
    """Make sure assets are converted to json correctly"""
    # Create and add asset
    p1 = create_application_asset(model, "Program 1")
    model.add_asset(p1)

    # Tuple is returned
    ret = model.asset_to_json(p1)

    # First element should be the id
    p1_id = ret[0]
    assert p1_id == str(p1.id)

    # Second element is the dict, each value should
    # be set as below for an 'Application' asset in coreLang
    p1_dict = ret[1]
    assert p1_dict.get('name') == p1.name
    assert p1_dict.get('metaconcept') == 'Application'
    assert p1_dict.get('eid') == str(p1.id)

    # Default values for 'Application' defenses in coreLang
    assert p1_dict.get('defenses') == {
        'notPresent': '0.0', 'supplyChainAuditing': '0.0'
    }


def test_model_association_to_json(model: Model):
    """Make sure associations are converted to json correctly"""
    # Create and add 2 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)

    # Create and add an association between p1 and p2
    association = create_association(
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
    )
    model.add_association(association)

    association_json = model.association_to_json(association)
    assert association_json.get('metaconcept') == 'AppExecution'
    assert association_json.get('association') == {
        'hostApp': [str(p1.id)],
        'appExecutedApps': [str(p2.id)]
    }


def test_model_attacker_to_json(model: Model):
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

    # Convert the attacker to json and make sure
    # id and name were converted correctly
    ret = model.attacker_to_json(attacker)
    assert ret[0] == str(attacker.id)
    attacker_dict = ret[1]
    assert attacker_dict.get('name') == attacker.name

    # entrypoints_dict has asset IDs as keys
    entrypoints_dict = attacker_dict.get('entry_points')

    # attacker should be attached to p1, therefore p1s
    # id should be a key in the entrypoints_dict
    assert str(p1.id) in entrypoints_dict

    # The given steps should be inside the entrypoint of
    # the attacker for asset p1
    assert entrypoints_dict[str(p1.id)]['attack_steps'] == attack_steps


def test_model_to_json(model: Model):
    """Put all to_json methods together and see that they work"""

    # Create and add 3 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    p3 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)
    model.add_asset(p3)

    # Create and add an association between p1 and p2
    association = create_association(
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
    )
    model.add_association(association)

    # Add attacker
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (p1, attack_steps)
    ]
    model.add_attacker(attacker)

    model_dict = model.model_to_json()

    # to_json will create map from asset id to asset dict
    # (dict is second value of tuple returned from asset_to_json)
    for asset in [p1, p2, p3]:
        assert model_dict['assets'][str(asset.id)] == \
        model.asset_to_json(asset)[1]

    # associations are added as they are created by association_to_json
    assert model_dict['associations'] == \
        [model.association_to_json(association)]

    # attackers are added similar to assets (id maps to attacker dict)
    assert model_dict['attackers'][str(attacker.id)] == \
        model.attacker_to_json(attacker)[1]

    # Meta data should also be added
    assert model_dict['metadata']['name'] == model.name
    assert model_dict['metadata']['langVersion'] == \
        model.lang_spec['formatVersion']
    assert model_dict['metadata']['langID'] == \
        model.lang_spec['defines'].get('id')


def test_model_save_and_load_model_from_scratch(model: Model):
    """Create a model, save it to file, load it from file and compare them
    Note: will store file in /tmp
    """

    # Create and add 3 applications
    p1 = create_application_asset(model, "Program 1")
    p2 = create_application_asset(model, "Program 2")
    p3 = create_application_asset(model, "Program 2")
    model.add_asset(p1)
    model.add_asset(p2)
    model.add_asset(p3)

    # Create and add an association between p1 and p2
    association = create_association(
        model, metaconcept="AppExecution",
        from_fieldname="hostApp", to_fieldname="appExecutedApps",
        from_assets=[p1], to_assets=[p2]
    )
    model.add_association(association)

    # Add attacker
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (p1, attack_steps)
    ]
    model.add_attacker(attacker)

    # Mock open() function so no real files are written to filesystem
    model.save_to_file('/tmp/test.json')

    # Create a new model by loading old model from file
    new_model = empty_model(model.lang_spec, 'New Test Model')
    new_model.load_from_file('/tmp/test.json')

    assert new_model.model_to_json() == model.model_to_json()


def test_model_save_and_load_model_example_model(model):
    """Load the simple_example_model.json from testdata, store it, compare"""

    # Load from example file
    model.load_from_file(
        path_testdata("simple_example_model.json")
    )

    # Save to file
    model.save_to_file('/tmp/test.json')

    # Create new model and load from previously saved file
    new_model = empty_model(model.lang_spec, 'New Test Model')
    new_model.load_from_file('/tmp/test.json')

    assert new_model.model_to_json() == model.model_to_json()
