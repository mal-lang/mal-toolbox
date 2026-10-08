//! Diffs pattern-matching results against output produced by the real
//! Python mal-toolbox's `SearchPattern.find_matches`, over the same
//! hand-built wiperLang model used by the attackgraph golden tests.

use std::collections::HashSet;
use std::rc::Rc;

use maltoolbox_attackgraph::AttackGraph;
use maltoolbox_language::{compile_file, generate_graph};
use maltoolbox_model::Model;
use maltoolbox_patternfinder::{SearchCondition, SearchPattern};

fn fixture_path(name: &str) -> std::path::PathBuf {
    std::path::Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../maltoolbox-language/tests/fixtures"
    ))
    .join(name)
}

fn build_graph() -> (Model, AttackGraph) {
    let spec = compile_file(fixture_path("wiperLang.mal")).expect("compile");
    let lang_graph = Rc::new(generate_graph(spec).expect("build language graph"));

    let mut model = Model::new("Test Model", lang_graph);
    let internet = model
        .add_asset("Internet", Some("internet1".into()), None, None, None, true)
        .unwrap();
    let device = model
        .add_asset("Device", Some("device1".into()), None, None, None, true)
        .unwrap();
    let data = model
        .add_asset("Data", Some("data1".into()), None, None, None, true)
        .unwrap();
    let wiper1 = model
        .add_asset("Wiper", Some("wiper1".into()), None, None, None, true)
        .unwrap();
    let wiper2 = model
        .add_asset("Wiper", Some("wiper2".into()), None, None, None, true)
        .unwrap();

    model
        .add_associated_assets(internet, "hosts", HashSet::from([device]))
        .unwrap();
    model
        .add_associated_assets(device, "data", HashSet::from([data]))
        .unwrap();
    model
        .add_associated_assets(device, "malware", HashSet::from([wiper1, wiper2]))
        .unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");
    (model, attack_graph)
}

fn path_full_names(
    graph: &AttackGraph,
    model: &Model,
    path: &[maltoolbox_attackgraph::AttackGraphNodeId],
) -> Vec<String> {
    path.iter()
        .map(|&id| graph.full_name_of(id, Some(model)))
        .collect()
}

#[test]
fn matches_python_oracle_simple_pattern() {
    let (model, graph) = build_graph();

    let pattern = SearchPattern::new(vec![
        SearchCondition::new(|n| n.name == "infect"),
        SearchCondition::new(|n| n.name == "activate"),
        SearchCondition::new(|n| n.name == "exfiltrate"),
    ]);

    let mut actual: Vec<Vec<String>> = pattern
        .find_matches(&graph)
        .iter()
        .map(|path| path_full_names(&graph, &model, path))
        .collect();
    actual.sort();

    let expected: Vec<Vec<String>> = vec![
        vec![
            "device1:infect".into(),
            "wiper1:activate".into(),
            "wiper1:exfiltrate".into(),
        ],
        vec![
            "device1:infect".into(),
            "wiper2:activate".into(),
            "wiper2:exfiltrate".into(),
        ],
    ];

    assert_eq!(actual, expected);
}

#[test]
fn matches_python_oracle_repeated_condition_pattern() {
    let (model, graph) = build_graph();

    let pattern = SearchPattern::new(vec![
        SearchCondition::new(|_| true).repeated(0, 1_000_000),
        SearchCondition::new(|n| n.name == "trigger"),
    ]);

    let mut actual: Vec<Vec<String>> = pattern
        .find_matches(&graph)
        .iter()
        .map(|path| path_full_names(&graph, &model, path))
        .collect();
    actual.sort();

    let mut expected: Vec<Vec<String>> = vec![
        vec![
            "device1:infect".into(),
            "wiper1:activate".into(),
            "wiper1:trigger".into(),
        ],
        vec![
            "device1:infect".into(),
            "wiper2:activate".into(),
            "wiper2:trigger".into(),
        ],
        vec!["wiper1:activate".into(), "wiper1:trigger".into()],
        vec!["wiper1:trigger".into()],
        vec!["wiper2:activate".into(), "wiper2:trigger".into()],
        vec!["wiper2:trigger".into()],
    ];
    expected.sort();

    assert_eq!(actual, expected);
}
