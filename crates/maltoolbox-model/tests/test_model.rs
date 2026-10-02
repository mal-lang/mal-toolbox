//! Port of mal-toolbox's `tests/test_model.py`, over coreLang (loaded
//! from the same `.mar` fixture used by maltoolbox-language's tests),
//! mirroring `conftest.py`'s `corelang_lang_graph`/`model` fixtures.

use std::collections::HashSet;
use std::rc::Rc;

use maltoolbox_language::from_mar_archive;
use maltoolbox_model::{Model, ModelError};

fn corelang_model() -> Model {
    let path = std::path::Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../maltoolbox-language/tests/fixtures/org.mal-lang.coreLang-1.0.0.mar"
    ));
    let lang_graph = Rc::new(from_mar_archive(path).expect("load corelang"));
    Model::new("Test Model", lang_graph)
}

#[test]
fn add_asset() {
    let mut model = corelang_model();
    let before = model.assets.len();

    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();

    assert_eq!(before + 1, model.assets.len());
    assert!(model.assets.contains_key(&asset1));
}

#[test]
fn add_asset_with_id_set() {
    let mut model = corelang_model();
    let asset_id = model.next_id + 10;

    let asset1 = model
        .add_asset("Application", None, Some(asset_id), None, None, true)
        .unwrap();
    assert_eq!(asset1, asset_id);
    assert_eq!(model.next_id, asset_id + 1);

    let err = model
        .add_asset("Application", None, Some(asset_id), None, None, true)
        .unwrap_err();
    assert!(matches!(err, ModelError::DuplicateAssetId(id) if id == asset_id));
}

#[test]
fn add_asset_duplicate_name() {
    let mut model = corelang_model();
    let asset_name = "MyProgram";

    let asset1 = model
        .add_asset("Application", Some(asset_name.to_string()), None, None, None, true)
        .unwrap();
    assert_eq!(model.assets.len(), 1);
    assert_eq!(model.get_asset_by_id(asset1).unwrap().name, asset_name);

    let asset2 = model
        .add_asset("Application", Some(asset_name.to_string()), None, None, None, true)
        .unwrap();
    assert_eq!(model.assets.len(), 2);
    assert_eq!(
        model.get_asset_by_id(asset2).unwrap().name,
        format!("{asset_name}:{asset2}")
    );

    let err = model
        .add_asset("Application", Some(asset_name.to_string()), None, None, None, false)
        .unwrap_err();
    assert!(matches!(err, ModelError::DuplicateAssetName(_)));
    assert_eq!(model.assets.len(), 2);
}

#[test]
fn remove_asset_with_association() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model
        .add_associated_assets(asset1, "hostApp", HashSet::from([asset2]))
        .unwrap();

    assert_eq!(
        model.get_asset_by_id(asset1).unwrap().associated_assets.get("hostApp"),
        Some(&HashSet::from([asset2]))
    );
    assert_eq!(
        model.get_asset_by_id(asset2).unwrap().associated_assets.get("appExecutedApps"),
        Some(&HashSet::from([asset1]))
    );
    let count_before = model.assets.len();

    model.remove_asset(asset1).unwrap();

    assert!(model.get_asset_by_id(asset2).unwrap().associated_assets.is_empty());
    assert!(!model.assets.contains_key(&asset1));
    assert!(model.assets.contains_key(&asset2));
    assert_eq!(model.assets.len(), count_before - 1);
}

#[test]
fn remove_nonexisting_asset() {
    let mut model = corelang_model();
    let err = model.remove_asset(999_999).unwrap_err();
    assert!(matches!(err, ModelError::AssetNotFound { .. }));
}

#[test]
fn add_associated_asset() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();

    assert!(!model.get_asset_by_id(asset1).unwrap().associated_assets.contains_key("appExecutedApps"));
    assert!(!model.get_asset_by_id(asset2).unwrap().associated_assets.contains_key("hostApp"));

    model
        .add_associated_assets(asset1, "appExecutedApps", HashSet::from([asset2]))
        .unwrap();

    assert!(model
        .get_asset_by_id(asset1)
        .unwrap()
        .associated_assets
        .get("appExecutedApps")
        .unwrap()
        .contains(&asset2));
    assert!(model
        .get_asset_by_id(asset2)
        .unwrap()
        .associated_assets
        .get("hostApp")
        .unwrap()
        .contains(&asset1));

    let associations_in_common = model.associations_with(asset1, asset2);
    assert!(!associations_in_common.is_empty());
    for assoc in &associations_in_common {
        assert!(model.has_association_with(asset1, asset2, &assoc.name));
    }
}

#[test]
fn add_appexecution_association_two_assets() {
    // CoreLang specifies that AppExecution only can have one 'left' asset
    // (hostApp has max multiplicity 1).
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();

    let err = model
        .add_associated_assets(asset1, "hostApp", HashSet::from([asset1, asset2]))
        .unwrap_err();
    assert!(matches!(err, ModelError::TooManyAssetsInField(..)));
}

#[test]
fn add_association_wrong_type() {
    // CoreLang specifies that hostApp must be an Application.
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let data = model.add_asset("Data", None, None, None, None, true).unwrap();

    let err = model
        .add_associated_assets(asset1, "hostApp", HashSet::from([data]))
        .unwrap_err();
    assert!(matches!(err, ModelError::WrongAssociatedAssetType { .. }));
}

#[test]
fn add_association_nonexisting_fieldname() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let data = model.add_asset("Data", None, None, None, None, true).unwrap();

    let err = model
        .add_associated_assets(asset1, "unknownFieldName", HashSet::from([data]))
        .unwrap_err();
    assert!(matches!(err, ModelError::UnknownAssociation { .. }));
}

#[test]
fn add_association_duplicate() {
    let mut model = corelang_model();
    let d1 = model.add_asset("Data", None, None, None, None, true).unwrap();
    let d2 = model.add_asset("Data", None, None, None, None, true).unwrap();
    let d3 = model.add_asset("Data", None, None, None, None, true).unwrap();

    model.add_associated_assets(d3, "containingData", HashSet::from([d1, d2])).unwrap();
    model.add_associated_assets(d3, "containingData", HashSet::from([d2])).unwrap();
    model.add_associated_assets(d2, "containedData", HashSet::from([d3])).unwrap();

    assert_eq!(
        model.get_asset_by_id(d1).unwrap().associated_assets["containedData"],
        HashSet::from([d3])
    );
    assert_eq!(
        model.get_asset_by_id(d2).unwrap().associated_assets["containedData"],
        HashSet::from([d3])
    );
    assert_eq!(
        model.get_asset_by_id(d3).unwrap().associated_assets["containingData"],
        HashSet::from([d1, d2])
    );
}

#[test]
fn remove_associated_asset() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model.add_associated_assets(asset1, "appExecutedApps", HashSet::from([asset2])).unwrap();

    model.remove_associated_assets(asset1, "appExecutedApps", &HashSet::from([asset2])).unwrap();

    assert!(!model.get_asset_by_id(asset1).unwrap().associated_assets.contains_key("appExecutedApps"));
    assert!(!model.get_asset_by_id(asset2).unwrap().associated_assets.contains_key("hostApp"));
}

#[test]
fn remove_associated_asset_with_leftovers() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset3 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model
        .add_associated_assets(asset1, "appExecutedApps", HashSet::from([asset2, asset3]))
        .unwrap();

    model.remove_associated_assets(asset1, "appExecutedApps", &HashSet::from([asset2])).unwrap();

    let remaining = &model.get_asset_by_id(asset1).unwrap().associated_assets["appExecutedApps"];
    assert!(!remaining.contains(&asset2));
    assert!(remaining.contains(&asset3));
    assert!(!model.get_asset_by_id(asset2).unwrap().associated_assets.contains_key("hostApp"));
    assert!(model.get_asset_by_id(asset3).unwrap().associated_assets["hostApp"].contains(&asset1));
}

#[test]
fn remove_nonexisting_associated_assets() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();

    let err = model
        .remove_associated_assets(asset1, "appExecutedApps", &HashSet::from([asset2]))
        .unwrap_err();
    assert!(matches!(err, ModelError::NotAssociated { .. }));
}

#[test]
fn remove_asset_from_association_nonexisting_asset() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset3 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset4 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model.add_associated_assets(asset1, "appExecutedApps", HashSet::from([asset2])).unwrap();

    assert!(matches!(
        model.remove_associated_assets(asset1, "appExecutedApps", &HashSet::from([asset3])),
        Err(ModelError::NotAssociated { .. })
    ));
    assert!(matches!(
        model.remove_associated_assets(asset1, "appExecutedApps", &HashSet::from([asset4])),
        Err(ModelError::NotAssociated { .. })
    ));
}

#[test]
fn get_asset_by_id() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();

    assert_eq!(model.get_asset_by_id(asset1).unwrap().id, asset1);
    assert_eq!(model.get_asset_by_id(asset2).unwrap().id, asset2);
    assert!(model.get_asset_by_id(1337).is_none());
}

#[test]
fn get_asset_by_name() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let name1 = model.get_asset_by_id(asset1).unwrap().name.clone();
    let name2 = model.get_asset_by_id(asset2).unwrap().name.clone();

    assert_eq!(model.get_asset_by_name(&name1).unwrap().id, asset1);
    assert_eq!(model.get_asset_by_name(&name2).unwrap().id, asset2);
    assert!(model.get_asset_by_name("Program 3").is_none());
}

#[test]
fn asset_to_dict() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();

    let dict = model.get_asset_by_id(asset1).unwrap().to_dict();
    assert_eq!(dict["name"], model.get_asset_by_id(asset1).unwrap().name.as_str());
    assert_eq!(dict["type"], "Application");
    // Default values should not be saved.
    assert!(dict.get("defenses").is_none());
}

#[test]
fn asset_with_nondefault_defense_to_dict() {
    let mut model = corelang_model();
    let asset1 = model
        .add_asset(
            "Application",
            None,
            None,
            Some(std::collections::HashMap::from([("notPresent".to_string(), 1.0)])),
            None,
            true,
        )
        .unwrap();

    let dict = model.get_asset_by_id(asset1).unwrap().to_dict();
    assert_eq!(dict["defenses"]["notPresent"], 1.0);
}

#[test]
fn serialize() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let _asset3 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model.add_associated_assets(asset1, "appExecutedApps", HashSet::from([asset2])).unwrap();

    let dict = model.to_dict();

    assert_eq!(dict["metadata"]["name"], model.name.as_str());
    assert_eq!(dict["metadata"]["langVersion"], model.lang_graph.metadata.version.as_str());
    assert_eq!(dict["metadata"]["langID"], model.lang_graph.metadata.id.as_str());
}

#[test]
fn save_and_load_model_from_scratch() {
    let mut model = corelang_model();
    let asset1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model
        .assets
        .get_mut(&asset1)
        .unwrap()
        .extras
        .insert("testing".to_string(), "testing".into());
    let asset2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let asset3 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model
        .add_associated_assets(asset1, "appExecutedApps", HashSet::from([asset2, asset3]))
        .unwrap();

    let dir = std::env::temp_dir().join(format!("maltoolbox-model-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();

    for ext in ["yml", "yaml", "json"] {
        let path = dir.join(format!("test.{ext}"));
        maltoolbox_model::save_to_file(&model, &path).unwrap();
        let new_model = maltoolbox_model::load_from_file(&path, model.lang_graph.clone()).unwrap();
        assert_eq!(new_model.to_dict(), model.to_dict());
    }

    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn dynamic_model() {
    let lang_path = std::path::Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../maltoolbox-language/tests/fixtures/wiperLang.mal"
    ));
    let lang = Rc::new(maltoolbox_language::from_mal_spec(lang_path).expect("load wiperLang"));
    let mut model = Model::new("Example Model", lang.clone());

    let c2server = model.add_asset("C2Server", Some("C2Server".into()), Some(2), None, None, true).unwrap();
    let infected_device = model
        .add_asset("Device", Some("InfectedDevice".into()), Some(3), None, None, true)
        .unwrap();
    model.add_associated_assets(c2server, "receiveFrom", HashSet::from([infected_device])).unwrap();

    let data = model.add_asset("Data", Some("InfectedData".into()), Some(4), None, None, true).unwrap();
    model.add_associated_assets(infected_device, "data", HashSet::from([data])).unwrap();

    let malware = model.add_asset("Wiper", Some("Wiper".into()), Some(5), None, None, true).unwrap();
    model.add_associated_assets(malware, "victim", HashSet::from([infected_device])).unwrap();

    let vulnerable_device = model
        .add_asset("Device", Some("VulnerableDevice".into()), Some(6), None, None, true)
        .unwrap();
    model
        .add_associated_assets(vulnerable_device, "receiveFrom", HashSet::from([infected_device]))
        .unwrap();
    model
        .add_associated_assets(vulnerable_device, "sendTo", HashSet::from([infected_device]))
        .unwrap();

    let internet = model.add_asset("Internet", Some("Internet".into()), Some(1), None, None, true).unwrap();
    model
        .add_associated_assets(
            internet,
            "hosts",
            HashSet::from([c2server, infected_device, vulnerable_device]),
        )
        .unwrap();

    let dir = std::env::temp_dir().join(format!("maltoolbox-model-dyn-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("test.yml");

    maltoolbox_model::save_to_file(&model, &path).unwrap();
    let loaded_model = maltoolbox_model::load_from_file(&path, lang).unwrap();

    assert_eq!(loaded_model.to_dict(), model.to_dict());
    std::fs::remove_dir_all(&dir).ok();
}
