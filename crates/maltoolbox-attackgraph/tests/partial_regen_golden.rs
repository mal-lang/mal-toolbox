//! Diffs partial-regeneration output against golden JSON produced by the
//! real Python mal-toolbox's `AttackGraph.partially_regenerate_graph`.
//! Topology-based comparison, same rationale as `graph_golden.rs`.

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
    let obj = attack_steps.as_object().expect("attack_steps must be an object");
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
fn matches_python_oracle_for_partial_regeneration() {
    let spec = compile_file(fixture_path("wiperLang.mal")).expect("compile");
    let lang_graph = Rc::new(generate_graph(spec).expect("build language graph"));

    let mut model = Model::new("Test Model", lang_graph);
    let internet = model.add_asset("Internet", Some("internet1".into()), None, None, None, true).unwrap();
    let device = model.add_asset("Device", Some("device1".into()), None, None, None, true).unwrap();
    let data = model.add_asset("Data", Some("data1".into()), None, None, None, true).unwrap();
    let wiper1 = model.add_asset("Wiper", Some("wiper1".into()), None, None, None, true).unwrap();

    model.add_associated_assets(internet, "hosts", HashSet::from([device])).unwrap();
    model.add_associated_assets(device, "data", HashSet::from([data])).unwrap();
    model.add_associated_assets(device, "malware", HashSet::from([wiper1])).unwrap();

    let mut attack_graph = AttackGraph::from_model(&model).expect("build attack graph");

    // Now add a second Wiper, associated to device1 via "malware", and
    // partially regenerate instead of rebuilding from scratch.
    let wiper2 = model.add_asset("Wiper", Some("wiper2".into()), None, None, None, true).unwrap();
    model.add_associated_assets(device, "malware", HashSet::from([wiper2])).unwrap();

    let created = attack_graph
        .partially_regenerate_graph(
            &model,
            &HashSet::from([wiper2]),
            &HashSet::from([(device, "malware".to_string(), wiper2)]),
            &HashMap::new(),
            &HashSet::new(),
        )
        .expect("partial regeneration");

    assert_eq!(created.len(), 5, "expected the 5 new Wiper attack steps to be created");

    let actual_full = attack_graph.to_dict(Some(&model));
    let actual = canonicalize(&actual_full["attack_steps"]);

    let golden_path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/golden/wiper_partial_regen.json"
    );
    let expected_full: Value = serde_json::from_str(&std::fs::read_to_string(golden_path).unwrap()).unwrap();
    let expected = canonicalize(&expected_full["attack_steps"]);

    assert_eq!(
        actual, expected,
        "\n--- expected ---\n{}\n--- actual ---\n{}",
        serde_json::to_string_pretty(&expected).unwrap(),
        serde_json::to_string_pretty(&actual).unwrap(),
    );
}
