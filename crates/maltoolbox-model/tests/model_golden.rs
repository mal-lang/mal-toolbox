//! Diffs `Model::to_dict()` against golden JSON produced by the real
//! Python mal-toolbox, built from the same wiperLang.mal fixture used by
//! maltoolbox-language's golden tests.
//!
//! The "MAL-Toolbox Version" metadata field is masked before comparison:
//! it's informational provenance (which implementation produced the
//! file), not part of the wire schema, so this Rust port legitimately
//! reports its own crate version there instead of claiming to be a
//! specific Python mal-toolbox release.

use std::collections::HashMap;
use std::rc::Rc;

use maltoolbox_language::{compile_file, generate_graph};
use maltoolbox_model::Model;
use serde_json::Value;

fn fixture_path(name: &str) -> std::path::PathBuf {
    std::path::Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/../maltoolbox-language/tests/fixtures"))
        .join(name)
}

fn mask_version(mut v: Value) -> Value {
    v["metadata"]["MAL-Toolbox Version"] = Value::String("<masked>".into());
    v
}

#[test]
fn matches_python_oracle_for_wiper_model() {
    let spec = compile_file(fixture_path("wiperLang.mal")).expect("compile");
    let lang_graph = Rc::new(generate_graph(spec).expect("build language graph"));

    let mut model = Model::new("Test Model", lang_graph);

    let internet = model.add_asset("Internet", Some("internet1".into()), None, None, None, true).unwrap();
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
    let data = model.add_asset("Data", Some("data1".into()), None, None, None, true).unwrap();
    let wiper = model.add_asset("Wiper", Some("wiper1".into()), None, None, None, true).unwrap();

    model
        .add_associated_assets(internet, "hosts", std::collections::HashSet::from([device]))
        .unwrap();
    model
        .add_associated_assets(device, "data", std::collections::HashSet::from([data]))
        .unwrap();
    model
        .add_associated_assets(device, "malware", std::collections::HashSet::from([wiper]))
        .unwrap();

    let actual = mask_version(model.to_dict());

    let golden_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/golden/wiper_model.json");
    let expected: Value = mask_version(
        serde_json::from_str(&std::fs::read_to_string(golden_path).unwrap()).unwrap(),
    );

    assert_eq!(
        actual, expected,
        "\n--- expected ---\n{}\n--- actual ---\n{}",
        serde_json::to_string_pretty(&expected).unwrap(),
        serde_json::to_string_pretty(&actual).unwrap(),
    );
}
