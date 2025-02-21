"""Unit tests for maltoolbox.model"""

import pytest
from conftest import empty_model, path_testdata

from maltoolbox.model import (Model, ModelAsset,
    AttackerAttachment)

### Helper functions

APP_EXEC_ASSOC_NAME = "AppExecution"
DATA_CONTAIN_ASSOC_NAME = "DataContainment"

### Tests

def test_attacker_attachment_add_entry_point(model: Model):
    """"""

    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

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

    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

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

    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

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


def test_add_remove_attacker(model: Model):
    """"""

    asset1 = model.add_asset(asset_type = 'Application')

    attacker1 = AttackerAttachment()
    model.add_attacker(attacker1)
    attacker2 = AttackerAttachment()
    model.add_attacker(attacker2)

    attacker1.add_entry_point(asset1, 'read')
    attacker1.add_entry_point(asset1, 'access')
    attacker2.add_entry_point(asset1, 'read')

    assert len(model.attackers) == 2
    model.remove_attacker(attacker1)
    assert len(model.attackers) == 1
    model.remove_attacker(attacker2)
    assert len(model.attackers) == 0

def test_model_add_asset(model: Model):
    """Make sure assets are added correctly"""

    assets_before = list(model.assets.values())

    # Create an application asset
    asset1 = model.add_asset(asset_type = 'Application')

    # Make sure the new asset was added to the model
    assert len(assets_before) + 1 == len(model.assets)
    assert asset1 not in assets_before
    assert asset1 in model.assets.values()


def test_model_add_asset_with_id_set(model):
    """Make sure assets are added and next_id correctly updated
    when id is set explicitly in method call"""

    asset_id = model.next_id + 10
    asset1 = model.add_asset(asset_type = 'Application', asset_id = asset_id)

    # Make sure asset was added
    assert asset1 == model.assets[asset_id]

    # Make sure next_id was incremented
    assert model.next_id == asset_id + 1

    # Add asset with same ID as previously added asset, expect ValueError
    with pytest.raises(ValueError):
        asset2 = model.add_asset(
            asset_type = 'Application', asset_id = asset_id)


def test_model_add_asset_duplicate_name(model: Model):
    """Add several assets with the same name to the model"""

    asset_name = "MyProgram"

    # Add a new asset
    asset1 = model.add_asset(asset_type = 'Application', name = asset_name)
    assert len(model.assets) == 1
    assert model.assets[0].name == asset_name

    # Add with same name again (allowed by default)
    asset2 = model.add_asset(asset_type = 'Application', name = asset_name)
    assert len(model.assets) == 2
    # Is this expected - shouldn't asset2 have same name as asset1?
    assert model.assets[1].name == f"{asset_name}:{asset2.id}"

    # Add asset again while not allowing duplicates, expect ValueError
    with pytest.raises(ValueError):
        model.add_asset(
            asset_type = 'Application',
            name = asset_name,
            allow_duplicate_names = False)
    # Make sure there are still only two assets named 'Program 1'
    assert len(model.assets) == 2


def test_model_remove_asset_with_association(model: Model):
    """Remove assets from a model"""

    # Add two program assets to the model
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')
    asset1.add_associated_assets('hostApp', {asset2})

    assert asset1.associated_assets == {'hostApp': {asset2}}
    assert asset2.associated_assets == {'appExecutedApps': {asset1}}
    num_assets_before = len(model.assets)

    model.remove_asset(asset1)

    assert asset1.associated_assets == {}
    assert asset2.associated_assets == {}

    # Make sure asset asset1 was deleted, but asset2 still exists
    assert asset1 not in model.assets.values()
    assert asset2 in model.assets.values()
    assert len(model.assets) == num_assets_before - 1


def test_model_remove_nonexisting_asset(model: Model):
    """Removing a non existing asset leads to lookup error"""

    # Create an asset but don't add it to the model before removing it
    asset1 = ModelAsset(
        name = 'TestAsset',
        asset_id = 1,
        lg_asset = model.lang_graph.assets['Application'])
    with pytest.raises(LookupError):
        model.remove_asset(asset1)


def test_model_add_associated_asset(model: Model):
    """Make sure associations work as intended"""

    # Create two assets
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

    assert 'appExecutedApps' not in asset1.associated_assets
    assert 'hostApp' not in asset2.associated_assets
    # Create an association between asset1 and asset2
    asset1.add_associated_assets(fieldname = 'appExecutedApps', assets = {asset2})
    # Add the association to the model

    # Make sure association was added to the model and assets
    assert 'appExecutedApps' in asset1.associated_assets
    assert asset2 in asset1.associated_assets['appExecutedApps']
    assert 'hostApp' in asset2.associated_assets
    assert asset1 in asset2.associated_assets['hostApp']


def test_model_add_appexecution_association_two_assets(model: Model):
    """coreLang specifies that AppExecution only can have one 'left' asset"""

    # Add program assets
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

    # Try create an association between (asset1, asset2) and asset1
    with pytest.raises(ValueError):
        # will raise error because two assets (asset1,asset2)
        # are not allowed in the left field for AppExecution
        asset1.add_associated_assets(fieldname = 'hostApp', assets = {asset1, asset2})


def test_model_add_association_wrong_type(model: Model):
    """coreLang specifies that hostApp must be an Application"""

    # Add program assets
    asset1 = model.add_asset(asset_type = 'Application')
    data = model.add_asset(asset_type = 'Data')

    # Try create an association between asset1 and data
    with pytest.raises(TypeError):
        # will raise error because data has wrong type
        asset1.add_associated_assets(fieldname = 'hostApp', assets = {data})


def test_model_add_association_nonexisting_fieldname(model: Model):
    """coreLang does not specify a fieldname called `unknownFieldName`"""

    # Add program assets
    asset1 = model.add_asset(asset_type = 'Application')
    data = model.add_asset(asset_type = 'Data')

    # Try create an association between asset1 and data
    with pytest.raises(LookupError):
        # will raise error because fieldname does not exist
        asset1.add_associated_assets(
            fieldname = 'unknownFieldName', assets = {data}
        )


def test_model_add_association_duplicate(model: Model):
    """Make sure same association is not added twice"""

    # Create three data assets
    d1 = model.add_asset(asset_type = 'Data')
    d2 = model.add_asset(asset_type = 'Data')
    d3 = model.add_asset(asset_type = 'Data')


    # Create an association between d3 and (d1, d2)
    d3.add_associated_assets(fieldname = 'containingData', assets = {d1, d2})

    # Identical to previous d3 to d2
    d3.add_associated_assets(fieldname = 'containingData', assets = {d2})

    # Indentical to previous d3 to d2
    d2.add_associated_assets(fieldname = 'containedData', assets = {d3, d3})

    assert d1.associated_assets['containedData'] == {d3}
    assert d2.associated_assets['containedData'] == {d3}
    assert d3.associated_assets['containingData'] == {d1, d2}


def test_model_remove_associated_asset(model: Model):
    """Make sure association can be removed"""

    # Create and add 2 applications
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

    asset1.add_associated_assets(
        fieldname = 'appExecutedApps', assets = {asset2})

    assert 'appExecutedApps' in asset1.associated_assets
    assert asset2 in asset1.associated_assets['appExecutedApps']
    assert 'hostApp' in asset2.associated_assets
    assert asset1 in asset2.associated_assets['hostApp']

    # Remove the association and make sure it was
    # removed from assets and model
    asset1.remove_associated_assets(
        fieldname = 'appExecutedApps', assets = {asset2})

    assert 'appExecutedApps' not in asset1.associated_assets
    assert 'hostApp' not in asset2.associated_assets


def test_model_remove_associated_asset_with_leftovers(model: Model):
    """Make sure association can be removed"""

    # Create and add 2 applications
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')
    asset3 = model.add_asset(asset_type = 'Application')

    asset1.add_associated_assets(
        fieldname = 'appExecutedApps', assets = {asset2, asset3})

    assert 'appExecutedApps' in asset1.associated_assets
    assert asset2 in asset1.associated_assets['appExecutedApps']
    assert asset3 in asset1.associated_assets['appExecutedApps']
    assert 'hostApp' in asset2.associated_assets
    assert asset1 in asset2.associated_assets['hostApp']
    assert 'hostApp' in asset3.associated_assets
    assert asset1 in asset3.associated_assets['hostApp']

    # Remove the association and make sure it was
    # removed from assets and model
    asset1.remove_associated_assets(
        fieldname = 'appExecutedApps', assets = {asset2})

    assert 'appExecutedApps' in asset1.associated_assets
    assert asset2 not in asset1.associated_assets['appExecutedApps']
    assert asset3 in asset1.associated_assets['appExecutedApps']
    assert 'hostApp' not in asset2.associated_assets
    assert 'hostApp' in asset3.associated_assets
    assert asset1 in asset3.associated_assets['hostApp']


def test_model_remove_nonexisting_associated_assets(model: Model):
    """Make sure non existing association can not be removed"""

    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

    # No association exists
    assert 'appExecutedApps' not in asset1.associated_assets
    assert 'hostApp' not in asset2.associated_assets

    # So we should expect a LookupError when trying to remove one
    with pytest.raises(LookupError):
        asset1.remove_associated_assets(
            fieldname = 'appExecutedApps', assets = {asset2})


def test_model_remove_asset_from_association_nonexisting_asset(
        model: Model
    ):
    """Make sure error is thrown if deleting non existing asset
    from association"""

    # Create 4 applications and add 3 of them to model
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')
    asset3 = model.add_asset(asset_type = 'Application')
    asset4 = model.add_asset(asset_type = 'Application')

    # Create an association between asset1 and asset2
    asset1.add_associated_assets(
        fieldname = 'appExecutedApps', assets = {asset2})

    # We are removing asset3 from association where it does not exist
    with pytest.raises(LookupError):
        asset1.remove_associated_assets(fieldname = 'appExecutedApps',
            assets = {asset3})

    # We are removing asset4 from association, but asset4
    # does not exist in the model
    with pytest.raises(LookupError):
        asset1.remove_associated_assets(fieldname = 'appExecutedApps',
            assets = {asset4})


def test_model_add_attacker(model: Model):
    """Test functionality to add an attacker to the model"""

    # Add attacker 1
    attacker1 = AttackerAttachment()
    model.add_attacker(attacker1)
    assert attacker1.name == f'Attacker:{attacker1.id}'

    # Add attacker 2 with explicit id set (can be duplicate id)
    attacker2_id = attacker1.id
    attacker2 = AttackerAttachment()
    model.add_attacker(attacker2, attacker_id=attacker2_id)

    # Add attacker 2 with explicit id set (can be duplicate id)
    attacker2_id = attacker1.id
    attacker2 = AttackerAttachment()

    testcreds = model.add_asset(asset_type = 'Credentials')

    attack_steps = ['attemptCredentialsReuse']
    attacker2.entry_points = [
        (testcreds, attack_steps)
    ]
    model.add_attacker(attacker2, attacker_id=attacker2_id)


    assert attacker2.name == f'Attacker:{attacker2_id}'


def test_model_get_asset_by_id(model: Model):
    """Make sure correct asset is returned or None
    if no asset with that ID exists"""

    # Create and add 2 applications
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

    # Correct assets removed and None if asset with that not exists
    assert model.get_asset_by_id(asset1.id) == asset1
    assert model.get_asset_by_id(asset2.id) == asset2
    assert model.get_asset_by_id(1337) is None


def test_model_get_asset_by_name(model: Model):
    """Make sure correct asset is returned or None
    if no asset with that name exists"""

    # Create and add 2 applications
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')

    # Correct assets removed and None if asset with that name not exists
    assert model.get_asset_by_name(asset1.name) == asset1
    assert model.get_asset_by_name(asset2.name) == asset2
    assert model.get_asset_by_name("Program 3") is None


def test_model_get_attacker_by_id(model: Model):
    """Make sure correct attacker is returned of None
    if no attacker with that ID exists"""

    # Add attacker 1
    attacker1 = AttackerAttachment()
    model.add_attacker(attacker1)

    assert attacker1.id is not None
    assert model.get_attacker_by_id(attacker1.id) == attacker1
    assert model.get_attacker_by_id(1337) is None


def test_model_asset_to_dict(model: Model):
    """Make sure assets are converted to dictionaries correctly"""
    # Create and add asset
    asset1 = model.add_asset(asset_type = 'Application')

    (asset1_id, asset1_dict) = next(iter(asset1._to_dict().items()))

    assert asset1_id == asset1.id
    assert asset1_dict.get('name') == asset1.name
    assert asset1_dict.get('type') == 'Application'

    # Default values should not be saved
    assert asset1_dict.get('defenses', None) == None

def test_model_asset_with_nondefault_defense_to_dict(model: Model):
    """Make sure assets are converted to dictionaries correctly"""
    # Create and add asset
    asset1 = model.add_asset(
        asset_type = 'Application',
        defenses = {'notPresent': 1.0})

    (asset1_id, asset1_dict) = next(iter(asset1._to_dict().items()))

    assert asset1_id == asset1.id
    assert asset1_dict.get('name') == asset1.name
    assert asset1_dict.get('type') == 'Application'

    # Non-default defense value should be saved
    assert asset1_dict.get('defenses', None) == {
        'notPresent': 1.0
    }


def test_model_attacker_to_dict(model: Model):
    """Make sure attackers get correct format and values"""

    # Create and add an asset
    asset1 = model.add_asset(asset_type = 'Application')

    # Add attacker 1
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (asset1, attack_steps)
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

    # attacker should be attached to asset1, therefore asset1s
    # id should be a key in the entry_points_dict
    assert asset1.name is not None and entry_points_dict
    assert asset1.name in entry_points_dict

    # The given steps should be inside the entry_point of
    # the attacker for asset asset1
    assert entry_points_dict[asset1.name]['attack_steps'] == attack_steps


def test_serialize(model: Model):
    """Put all to_dict methods together and see that they work"""

    # Create and add 3 applications
    asset1 = model.add_asset(asset_type = 'Application')
    asset2 = model.add_asset(asset_type = 'Application')
    asset3 = model.add_asset(asset_type = 'Application')

    # Create and add an association between asset1 and asset2
    asset1.add_associated_assets(
        fieldname = 'appExecutedApps', assets = {asset2})

    # Add attacker
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (asset1, attack_steps)
    ]
    model.add_attacker(attacker)

    model_dict = model._to_dict()

    # to_dict will create map from asset id to asset dict
    for asset in [asset1, asset2, asset3]:
        assert model_dict['assets'][asset.id] == \
        asset._to_dict()[asset.id]

    # attackers are added similar to assets (id maps to attacker dict)
    assert model_dict['attackers'][attacker.id] == \
        model.attacker_to_dict(attacker)[1]

    # Meta data should also be added
    assert model_dict['metadata']['name'] == model.name
    assert model_dict['metadata']['langVersion'] == \
        model.lang_graph.metadata['version']
    assert model_dict['metadata']['langID'] == \
        model.lang_graph.metadata['id']


def test_model_save_and_load_model_from_scratch(model: Model):
    """Create a model, save it to file, load it from file and compare them
    Note: will create file in /tmp
    """

    # Create and add 3 applications
    asset1 = model.add_asset(asset_type = 'Application')
    asset1.extras = {"testing": "testing"}
    asset2 = model.add_asset(asset_type = 'Application')
    asset3 = model.add_asset(asset_type = 'Application')

    # Create and add an association between asset1 and asset2
    asset1.add_associated_assets(
        fieldname = 'appExecutedApps', assets = {asset2})

    # Add attacker
    attacker = AttackerAttachment()
    attack_steps = ["attemptCredentialsReuse"]
    attacker.entry_points = [
        (asset1, attack_steps)
    ]
    model.add_attacker(attacker)

    for model_path in ("/tmp/test.yml", "/tmp/test.yaml", "/tmp/test.json"):
        # Mock open() function so no real files are written to filesystem
        model.save_to_file(model_path)

        # Create a new model by loading old model from file
        new_model = Model.load_from_file(
            model_path,
            model.lang_graph
        )

        assert new_model._to_dict() == model._to_dict()


def test_model_load_and_save_example_model(model):
    """Load the simple_example_model.json from testdata, store it, compare
    Note: will create file in /tmp"""

    # Load from example file
    model = Model(
        path_testdata("simple_example_model.yml"),
        model.lang_graph
    )

    # Save to file
    model.save_to_file('/tmp/test.yml')

    # Create new model and load from previously saved file
    new_model = Model.load_from_file(
        '/tmp/test.yml',
        model.lang_graph
    )

    assert new_model._to_dict() == model._to_dict()
