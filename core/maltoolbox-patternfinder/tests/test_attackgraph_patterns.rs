//! Port of `tests/patternfinder/test_attackgraph_patterns.py`.

use std::collections::HashSet;
use std::rc::Rc;

use maltoolbox_attackgraph::{AttackGraph, AttackGraphNodeId};
use maltoolbox_language::graph::LanguageGraph;
use maltoolbox_model::Model;
use maltoolbox_patternfinder::{SearchCondition, SearchPattern};

fn fixtures_dir() -> &'static std::path::Path {
    std::path::Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../maltoolbox-language/tests/fixtures"
    ))
}

/// A minimal stand-in for Python's `dummy_lang_graph` fixture: one asset
/// with one `and`-type attack step, just enough to construct bare
/// `AttackGraphNode`s from, mirroring how the Python tests build a graph
/// by hand without a `Model`.
fn dummy_lang_graph() -> Rc<LanguageGraph> {
    use std::sync::atomic::{AtomicU64, Ordering};
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let unique = COUNTER.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!(
        "maltoolbox-pattern-test-{}-{unique}",
        std::process::id()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("dummy.mal");
    std::fs::write(
        &path,
        r#"
        #id: "dummy"
        #version: "0.0.0"
        category C {
            asset DummyAsset {
                & DummyAndAttackStep
            }
        }
        "#,
    )
    .unwrap();
    let graph = Rc::new(maltoolbox_language::from_mal_spec(&path).expect("compile dummy lang"));
    std::fs::remove_dir_all(&dir).ok();
    graph
}

/// Build an `AttackGraph` with no model, manually inserting bare nodes
/// for `DummyAsset:DummyAndAttackStep` with explicit ids, mirroring
/// `AttackGraphNode(id, dummy_and_step, dummy_asset)` plus manual
/// `.parents`/`.children` assignment in the Python tests.
fn bare_graph(lang_graph: Rc<LanguageGraph>, ids: &[i64]) -> (AttackGraph, Vec<AttackGraphNodeId>) {
    let dummy_asset = lang_graph.asset_id("DummyAsset").expect("DummyAsset");
    let step_id = lang_graph.asset(dummy_asset).attack_steps["DummyAndAttackStep"];

    let mut graph = AttackGraph::empty(lang_graph);
    let mut keys = Vec::new();
    for &id in ids {
        let key = graph
            .add_node(step_id, None, Some(id), None, None, None, None)
            .expect("add_node");
        keys.push(key);
    }
    (graph, keys)
}

fn link(graph: &mut AttackGraph, parent: AttackGraphNodeId, children: &[AttackGraphNodeId]) {
    for &child in children {
        graph.nodes[parent].children.insert(child);
        graph.nodes[child].parents.insert(parent);
    }
}

#[test]
fn find_pattern_example_graph() {
    let lang_graph = Rc::new(
        maltoolbox_language::from_mar_archive(
            fixtures_dir().join("org.mal-lang.coreLang-1.0.0.mar"),
        )
        .expect("load corelang"),
    );
    let mut model = Model::new("Test Model", lang_graph);
    let app1 = model
        .add_asset(
            "Application",
            Some("Application 1".into()),
            None,
            None,
            None,
            true,
        )
        .unwrap();
    let app2 = model
        .add_asset(
            "Application",
            Some("Application 2".into()),
            None,
            None,
            None,
            true,
        )
        .unwrap();
    model
        .add_associated_assets(app1, "appExecutedApps", HashSet::from([app2]))
        .unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");

    let pattern = SearchPattern::new(vec![
        SearchCondition::new(|n| n.name == "attemptRead"),
        SearchCondition::new(|n| n.name == "successfulRead"),
        SearchCondition::new(|n| n.name == "read"),
    ]);

    let paths = pattern.find_matches(&attack_graph);
    for path in paths {
        let names: Vec<&str> = path
            .iter()
            .map(|&id| attack_graph.nodes[id].name.as_str())
            .collect();
        assert_eq!(names, vec!["attemptRead", "successfulRead", "read"]);
    }
}

#[test]
fn find_multiple() {
    let lang_graph = dummy_lang_graph();
    let (mut graph, ids) = bare_graph(lang_graph, &[1, 2, 3, 4, 5, 6, 7]);
    let (n1, n2, n3, n4, n5, n6, n7) = (ids[0], ids[1], ids[2], ids[3], ids[4], ids[5], ids[6]);

    link(&mut graph, n1, &[n2, n3]);
    link(&mut graph, n2, &[n4]);
    link(&mut graph, n3, &[n5, n6]);
    link(&mut graph, n4, &[n7]);

    // Search pattern from Node1 to either Node6 or Node7, through any
    // number of intermediate nodes.
    let pattern = SearchPattern::new(vec![
        SearchCondition::new(|n| n.id == 1),
        SearchCondition::any().repeated(1, 1_000_000),
        SearchCondition::new(|n| n.id == 6 || n.id == 7),
    ]);
    let paths = pattern.find_matches(&graph);

    assert_eq!(paths.len(), 2);
    assert!(paths.contains(&vec![n1, n2, n4, n7]));
    assert!(paths.contains(&vec![n1, n3, n6]));
}

#[test]
fn find_multiple_same_subpath() {
    let lang_graph = dummy_lang_graph();
    let (mut graph, ids) = bare_graph(lang_graph, &[1, 2, 3, 4, 5]);
    let (n1, n2, n3, n4, n5) = (ids[0], ids[1], ids[2], ids[3], ids[4]);

    link(&mut graph, n1, &[n2, n3]);
    link(&mut graph, n2, &[n4]);
    link(&mut graph, n3, &[n5]);

    // Search pattern from Node1 to any node, through zero or more
    // intermediate nodes.
    let pattern = SearchPattern::new(vec![
        SearchCondition::new(|n| n.id == 1),
        SearchCondition::new(|_| true).repeated(0, 1_000_000),
        SearchCondition::new(|n| matches!(n.id, 2..=5)),
    ]);
    let paths = pattern.find_matches(&graph);

    assert!(paths.contains(&vec![n1, n2, n4]));
    assert!(paths.contains(&vec![n1, n3, n5]));
    assert!(paths.contains(&vec![n1, n2]));
    assert!(paths.contains(&vec![n1, n3]));
}

#[test]
fn two_same_start_end_node() {
    let lang_graph = dummy_lang_graph();
    let (mut graph, ids) = bare_graph(lang_graph, &[1, 2, 3, 4]);
    let (n1, n2, n3, n4) = (ids[0], ids[1], ids[2], ids[3]);

    link(&mut graph, n1, &[n2, n3]);
    link(&mut graph, n2, &[n4]);
    link(&mut graph, n3, &[n4]);

    let pattern = SearchPattern::new(vec![
        SearchCondition::new(|n| n.id == 1),
        SearchCondition::any(),
        SearchCondition::new(|n| n.id == 4),
    ]);
    let paths = pattern.find_matches(&graph);

    assert!(paths.contains(&vec![n1, n2, n4]));
    assert!(paths.contains(&vec![n1, n3, n4]));
}
