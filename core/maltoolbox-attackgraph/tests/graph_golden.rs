//! Diffs the Rust AttackGraph builder's output against golden JSON
//! produced by the real Python mal-toolbox, for a small hand-built model
//! over the wiperLang.mal fixture.
//!
//! The comparison is topology-based rather than raw JSON equality:
//! `AttackGraphNode.id` is an arbitrary integer assigned by iteration
//! order, and Rust `HashMap` iteration order isn't guaranteed to match
//! Python dict insertion order - so node ids legitimately differ between
//! the two even when the graphs are identical. Both sides are
//! canonicalized to replace id-keyed children/parents with sorted lists
//! of target full names, and the raw `id` field is dropped, before
//! comparing.

use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use maltoolbox_attackgraph::AttackGraph;
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

fn canonicalize(attack_steps: &Value) -> HashMap<String, Value> {
    let obj = attack_steps
        .as_object()
        .expect("attack_steps must be an object");
    let mut out = HashMap::new();
    for (full_name, node) in obj {
        let mut node = node.clone();
        node.as_object_mut().unwrap().remove("id");
        for key in ["children", "parents"] {
            let names: HashSet<String> = node[key]
                .as_object()
                .unwrap()
                .values()
                .map(|v| v.as_str().unwrap().to_string())
                .collect();
            let mut sorted: Vec<String> = names.into_iter().collect();
            sorted.sort();
            node[key] = Value::Array(sorted.into_iter().map(Value::String).collect());
        }
        out.insert(full_name.clone(), node);
    }
    out
}

#[test]
fn matches_python_oracle_for_wiper_attackgraph() {
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
        .add_associated_assets(internet, "hosts", HashSet::from([device]))
        .unwrap();
    model
        .add_associated_assets(device, "data", HashSet::from([data]))
        .unwrap();
    model
        .add_associated_assets(device, "malware", HashSet::from([wiper]))
        .unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");
    let actual_full = attack_graph.to_dict(Some(&model));
    let actual = canonicalize(&actual_full["attack_steps"]);

    let golden_path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/golden/wiper_attackgraph.json"
    );
    let expected_full: Value =
        serde_json::from_str(&std::fs::read_to_string(golden_path).unwrap()).unwrap();
    let expected = canonicalize(&expected_full["attack_steps"]);

    assert_eq!(
        actual,
        expected,
        "\n--- expected ---\n{}\n--- actual ---\n{}",
        serde_json::to_string_pretty(&expected).unwrap(),
        serde_json::to_string_pretty(&actual).unwrap(),
    );
}
