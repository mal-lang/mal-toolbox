//! Self-consistency round-trip for Model::to_dict / from_dict /
//! save_to_file / load_from_file, over the same hand-built wiperLang
//! model used by `model_golden.rs`.

use std::collections::HashMap;
use std::rc::Rc;

use maltoolbox_language::{compile_file, generate_graph};
use maltoolbox_model::Model;
use serde_json::Value;

fn fixture_path(name: &str) -> std::path::PathBuf {
    std::path::Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../maltoolbox-language/tests/fixtures"
    ))
    .join(name)
}

fn build_model() -> Model {
    let spec = compile_file(fixture_path("wiperLang.mal")).expect("compile");
    let lang_graph = Rc::new(generate_graph(spec).expect("build language graph"));

    let mut model = Model::new("Test Model", lang_graph);
    let internet = model
        .add_asset("Internet", Some("internet1".into()), None, None, None, true)
        .unwrap();
    let device = model
        .add_asset(
            "Device",
            Some("device1".into()),
            None,
            Some(HashMap::from([("someDefense".to_string(), 0.5)])),
            Some(serde_json::Map::from_iter([(
                "note".to_string(),
                Value::String("test".into()),
            )])),
            true,
        )
        .unwrap();
    let data = model
        .add_asset("Data", Some("data1".into()), None, None, None, true)
        .unwrap();
    let wiper = model
        .add_asset("Wiper", Some("wiper1".into()), None, None, None, true)
        .unwrap();

    model
        .add_associated_assets(internet, "hosts", std::collections::HashSet::from([device]))
        .unwrap();
    model
        .add_associated_assets(device, "data", std::collections::HashSet::from([data]))
        .unwrap();
    model
        .add_associated_assets(device, "malware", std::collections::HashSet::from([wiper]))
        .unwrap();

    model
}

#[test]
fn round_trips_through_dict() {
    let model = build_model();
    let dict = model.to_dict();

    let reloaded = maltoolbox_model::from_dict(&dict, model.lang_graph.clone()).expect("from_dict");
    let reloaded_dict = reloaded.to_dict();

    assert_eq!(dict, reloaded_dict);
}

#[test]
fn round_trips_through_file() {
    let model = build_model();

    let dir =
        std::env::temp_dir().join(format!("maltoolbox-model-roundtrip-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("model.json");

    maltoolbox_model::save_to_file(&model, &path).expect("save");
    let reloaded = maltoolbox_model::load_from_file(&path, model.lang_graph.clone()).expect("load");

    assert_eq!(model.to_dict(), reloaded.to_dict());

    std::fs::remove_dir_all(&dir).ok();
}
