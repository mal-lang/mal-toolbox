//! Port of `tests/attackgraph/test_partial_regeneration.py`'s
//! integration-style tests: for each, mutate a `Model`, call
//! `partially_regenerate_graph`, then independently build a fresh
//! `AttackGraph` from scratch and assert the two are equivalent. Several
//! of these are regression tests for real historical bugs in the Python
//! original's partial regeneration (see the per-test comments there) -
//! kept in full since they're exactly the kind of case oracle-golden
//! tests over a single snapshot wouldn't catch.
//!
//! Not ported: the low-level unit tests calling private
//! `partially_generate` helpers directly with hand-built
//! `ExpressionsChain`s (`test_assoc_affected_expr_chain_*`,
//! `test_affected_root_assets_subtype`) - the same logic is already
//! exercised end-to-end by the integration tests below, and
//! constructing raw `ExpressionsChain` values to test in isolation adds
//! little over that. Two cheap error-path unit tests are kept
//! (`switch_fieldname`/`nodes_to_be_removed` raising on bad input).

use indexmap::IndexMap;
use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use maltoolbox_attackgraph::{AttackGraph, AttackGraphNodeId};
use maltoolbox_language::graph::LanguageGraph;
use maltoolbox_model::Model;

fn lang_fixtures_dir() -> &'static std::path::Path {
    std::path::Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../maltoolbox-language/tests/fixtures"
    ))
}

fn ag_fixtures_dir() -> &'static std::path::Path {
    std::path::Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures"))
}

fn training_lang() -> Rc<LanguageGraph> {
    Rc::new(maltoolbox_language::from_mar_archive(ag_fixtures_dir().join("org.mal-lang.trainingLang-1.0.0.mar")).unwrap())
}

fn corelang() -> Rc<LanguageGraph> {
    Rc::new(maltoolbox_language::from_mar_archive(lang_fixtures_dir().join("org.mal-lang.coreLang-1.0.0.mar")).unwrap())
}

fn compile_lang(name: &str) -> Rc<LanguageGraph> {
    let spec = maltoolbox_language::compile_file(lang_fixtures_dir().join(name)).unwrap();
    Rc::new(maltoolbox_language::generate_graph(spec).unwrap())
}

/// Captures a [`maltoolbox_model::AssetSnapshot`] per id from the
/// still-live `model`, for tests that call `partially_regenerate_graph`
/// before `model.remove_asset` (both orders are valid; `snapshot` just
/// captures from wherever the asset currently lives instead of from
/// `remove_asset`'s return value).
fn snapshot(model: &Model, ids: &HashSet<i64>) -> HashMap<i64, maltoolbox_model::AssetSnapshot> {
    ids.iter()
        .map(|&id| {
            let asset = model.get_asset_by_id(id).unwrap();
            (
                id,
                maltoolbox_model::AssetSnapshot {
                    name: asset.name.clone(),
                    lg_asset: asset.lg_asset,
                    final_state: asset.clone(),
                },
            )
        })
        .collect()
}

/// Port of `check_graph_equivalence`: asserts two attack graphs have the
/// same node set and the same children/parents relationships, by full
/// name (ids are allowed to differ between an incrementally-updated
/// graph and a freshly-generated one).
fn check_graph_equivalence(model: &Model, expected: &AttackGraph, actual: &AttackGraph) {
    assert_eq!(
        expected.nodes.len(),
        actual.nodes.len(),
        "Number of nodes differ: expected {} != actual {}",
        expected.nodes.len(),
        actual.nodes.len()
    );

    let expected_names: HashSet<&String> = expected.full_name_to_node.keys().collect();
    let actual_names: HashSet<&String> = actual.full_name_to_node.keys().collect();
    assert_eq!(
        expected_names, actual_names,
        "Node full names differ: only in expected: {:?}; only in actual: {:?}",
        expected_names.difference(&actual_names),
        actual_names.difference(&expected_names)
    );

    let names_of = |graph: &AttackGraph, ids: &HashSet<AttackGraphNodeId>| -> HashSet<String> {
        ids.iter().map(|&id| graph.full_name_of(id, Some(model))).collect()
    };

    for (full_name, &expected_key) in &expected.full_name_to_node {
        let actual_key = *actual
            .full_name_to_node
            .get(full_name)
            .unwrap_or_else(|| panic!("{full_name} not in partially regenerated graph"));

        let expected_children = names_of(expected, &expected.nodes[expected_key].children);
        let actual_children = names_of(actual, &actual.nodes[actual_key].children);
        assert_eq!(expected_children, actual_children, "different children for {full_name}");

        let expected_parents = names_of(expected, &expected.nodes[expected_key].parents);
        let actual_parents = names_of(actual, &actual.nodes[actual_key].parents);
        assert_eq!(expected_parents, actual_parents, "different parents for {full_name}");
    }
}

#[test]
fn partial_regeneration_training_lang() {
    let lang_graph = training_lang();
    let mut model = Model::new("Test Model", lang_graph.clone());
    let network = model.add_asset("Network", Some("LAN".into()), None, None, None, true).unwrap();
    let mut ag = AttackGraph::from_model(&model).unwrap();

    macro_rules! check {
        () => {
            let regenerated = AttackGraph::from_model(&model).unwrap();
            check_graph_equivalence(&model, &regenerated, &ag);
        };
    }

    let host0 = model.add_asset("Host", Some("Host0".into()), None, None, None, true).unwrap();
    model.add_associated_assets(network, "hosts", HashSet::from([host0])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([host0]), &HashSet::from([(network, "hosts".to_string(), host0)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    let user0 = model.add_asset("User", Some("User0".into()), None, None, None, true).unwrap();
    model.add_associated_assets(host0, "users", HashSet::from([user0])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([user0]), &HashSet::from([(host0, "users".to_string(), user0)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    let data0 = model.add_asset("Data", Some("Data0".into()), None, None, None, true).unwrap();
    model.add_associated_assets(host0, "data", HashSet::from([data0])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([data0]), &HashSet::from([(host0, "data".to_string(), data0)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    // Add a second host to the already existing network: requires
    // relinking of the pre-existing Network:LAN:access node's children.
    let host1 = model.add_asset("Host", Some("Host1".into()), None, None, None, true).unwrap();
    model.add_associated_assets(network, "hosts", HashSet::from([host1])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([host1]), &HashSet::from([(network, "hosts".to_string(), host1)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    // Associate the same user with the second host: relinking of an
    // existing node (User0:compromise) to a new child.
    model.add_associated_assets(host1, "users", HashSet::from([user0])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(host1, "users".to_string(), user0)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    // A second Data asset on Host1, and another on Host0 (already has
    // Data0): fresh host/data pairing plus a host gaining another child.
    let data1 = model.add_asset("Data", Some("Data1".into()), None, None, None, true).unwrap();
    let data2 = model.add_asset("Data", Some("Data2".into()), None, None, None, true).unwrap();
    model.add_associated_assets(host1, "data", HashSet::from([data1])).unwrap();
    model.add_associated_assets(host0, "data", HashSet::from([data2])).unwrap();
    ag.partially_regenerate_graph(
        &model,
        &HashSet::from([data1, data2]),
        &HashSet::from([(host1, "data".to_string(), data1), (host0, "data".to_string(), data2)]),
        &HashMap::new(),
        &HashSet::new()).unwrap();
    check!();

    let network2 = model.add_asset("Network", Some("WAN".into()), None, None, None, true).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([network2]), &HashSet::new(), &HashMap::new(), &HashSet::new()).unwrap();
    model.add_associated_assets(network, "toNetworks", HashSet::from([network2])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(network, "toNetworks".to_string(), network2)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    // Now tear everything back down.
    model.remove_associated_assets(network, "toNetworks", &HashSet::from([network2])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(network, "toNetworks".to_string(), network2)])).unwrap();
    check!();

    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &HashSet::from([network2])), &HashSet::new()).unwrap();
    model.remove_asset(network2).unwrap();
    check!();

    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &HashSet::from([data1])), &HashSet::from([(host1, "data".to_string(), data1)])).unwrap();
    model.remove_asset(data1).unwrap();
    check!();

    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &HashSet::from([data2])), &HashSet::from([(host0, "data".to_string(), data2)])).unwrap();
    model.remove_asset(data2).unwrap();
    check!();

    model.remove_associated_assets(host1, "users", &HashSet::from([user0])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(host1, "users".to_string(), user0)])).unwrap();
    check!();

    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &HashSet::from([host1])), &HashSet::from([(network, "hosts".to_string(), host1)])).unwrap();
    model.remove_asset(host1).unwrap();
    check!();

    model.remove_associated_assets(host0, "data", &HashSet::from([data0])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(host0, "data".to_string(), data0)])).unwrap();
    check!();

    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &HashSet::from([data0])), &HashSet::new()).unwrap();
    model.remove_asset(data0).unwrap();
    check!();

    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &HashSet::from([user0])), &HashSet::from([(host0, "users".to_string(), user0)])).unwrap();
    model.remove_asset(user0).unwrap();
    check!();

    model.remove_associated_assets(network, "hosts", &HashSet::from([host0])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(network, "hosts".to_string(), host0)])).unwrap();
    check!();

    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &HashSet::from([host0])), &HashSet::new()).unwrap();
    model.remove_asset(host0).unwrap();
    check!();

    assert_eq!(model.assets.len(), 1);
    assert!(model.assets.contains_key(&network));
}

#[test]
fn partial_regeneration_with_assoc_chain_lang() {
    let lang_graph = compile_lang("assocChainLang.mal");
    let mut model = Model::new("Test Model", lang_graph.clone());

    let mut parent = model.add_asset("A", Some("A:0".into()), None, None, None, true).unwrap();
    // (child type to create, fieldname on `parent` pointing to it) - Python
    // derives the fieldname directly as `asset_type.lower()`.
    let children = ["B", "C", "D", "E", "F", "G", "H", "I"];
    for asset_type in children {
        let fieldname = asset_type.to_lowercase();
        let child = model.add_asset(asset_type, Some(format!("{asset_type}:0")), None, None, None, true).unwrap();
        model.add_associated_assets(parent, &fieldname, HashSet::from([child])).unwrap();
        parent = child;
    }
    let mut ag = AttackGraph::from_model(&model).unwrap();

    // (parent type, fieldname on parent pointing to the next child in the chain)
    let chain = [("A", "b"), ("B", "c"), ("C", "d"), ("D", "e"), ("E", "f"), ("F", "g"), ("G", "h"), ("H", "i")];
    for &(asset_type, fieldname) in &chain {
        let parent_id = model.get_asset_by_name(&format!("{asset_type}:0")).unwrap().id;
        let child_id = model.get_asset_by_name(&format!("{}:0", fieldname.to_uppercase())).unwrap().id;

        model.remove_associated_assets(parent_id, fieldname, &HashSet::from([child_id])).unwrap();
        ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(parent_id, fieldname.to_string(), child_id)])).unwrap();
        let regenerated = AttackGraph::from_model(&model).unwrap();
        check_graph_equivalence(&model, &regenerated, &ag);

        model.add_associated_assets(parent_id, fieldname, HashSet::from([child_id])).unwrap();
        ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(parent_id, fieldname.to_string(), child_id)]), &HashMap::new(), &HashSet::new()).unwrap();
        let regenerated = AttackGraph::from_model(&model).unwrap();
        check_graph_equivalence(&model, &regenerated, &ag);
    }
}

#[test]
fn partial_regeneration_transitive() {
    let lang_graph = compile_lang("transitive.mal");
    let mut model = Model::new("Test Model", lang_graph.clone());

    let mut root = model.add_asset("TestAsset", Some("RootTestAsset".into()), None, None, None, true).unwrap();
    let mut ag = AttackGraph::from_model(&model).unwrap();

    let mut chain = vec![root];
    for i in 0..20 {
        let next = model.add_asset("TestAsset", Some(format!("TestAsset:{i}")), None, None, None, true).unwrap();
        model.add_associated_assets(root, "field2", HashSet::from([next])).unwrap();
        ag.partially_regenerate_graph(&model, &HashSet::from([next]), &HashSet::from([(root, "field2".to_string(), next)]), &HashMap::new(), &HashSet::new()).unwrap();
        let regenerated = AttackGraph::from_model(&model).unwrap();
        check_graph_equivalence(&model, &regenerated, &ag);
        root = next;
        chain.push(next);
    }

    for i in (0..20).step_by(2).rev() {
        let child_id = chain[i + 1];
        let parent_id = *model
            .get_asset_by_id(child_id)
            .unwrap()
            .associated_assets["field1"]
            .iter()
            .next()
            .unwrap();
        model.remove_associated_assets(parent_id, "field2", &HashSet::from([child_id])).unwrap();
        ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(parent_id, "field2".to_string(), child_id)])).unwrap();
        let regenerated = AttackGraph::from_model(&model).unwrap();
        check_graph_equivalence(&model, &regenerated, &ag);
    }
}

#[test]
fn partial_regeneration_set_ops_adv() {
    let lang_graph = compile_lang("set_ops_adv.mal");
    let mut model = Model::new("Test Model", lang_graph.clone());

    let hub1 = model.add_asset("Hub", Some("Hub 1".into()), None, None, None, true).unwrap();
    let hub2 = model.add_asset("Hub", Some("Hub 2".into()), None, None, None, true).unwrap();
    let hub3 = model.add_asset("Hub", Some("Hub 3".into()), None, None, None, true).unwrap();
    let t1 = model.add_asset("Target", Some("Target 1".into()), None, None, None, true).unwrap();
    let t2 = model.add_asset("Target", Some("Target 2".into()), None, None, None, true).unwrap();
    let t3 = model.add_asset("Target", Some("Target 3".into()), None, None, None, true).unwrap();

    model.add_associated_assets(hub2, "setA", HashSet::from([t1, t2])).unwrap();
    model.add_associated_assets(hub3, "setB", HashSet::from([t2, t3])).unwrap();
    model.add_associated_assets(hub1, "siblings", HashSet::from([hub2, hub3])).unwrap();

    let mut ag = AttackGraph::from_model(&model).unwrap();

    model.remove_associated_assets(hub3, "setB", &HashSet::from([t2])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(hub3, "setB".to_string(), t2)])).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);

    model.add_associated_assets(hub3, "setB", HashSet::from([t2])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(hub3, "setB".to_string(), t2)]), &HashMap::new(), &HashSet::new()).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);

    model.remove_associated_assets(hub1, "siblings", &HashSet::from([hub3])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(hub1, "siblings".to_string(), hub3)])).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);

    model.add_associated_assets(hub1, "siblings", HashSet::from([hub3])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(hub1, "siblings".to_string(), hub3)]), &HashMap::new(), &HashSet::new()).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);
}

#[test]
fn partial_regeneration_set_ops_collect_left() {
    // Chain has a difference nested on the left side of a collect
    // ((setA - setB).next.reach) - a position where the reverse walk in
    // assoc_left_assets is unsafe if more than one association changes
    // in the same call.
    let lang_graph = compile_lang("set_ops_collect_left.mal");
    let mut model = Model::new("Test Model", lang_graph.clone());

    let origin = model.add_asset("Origin", Some("Origin".into()), None, None, None, true).unwrap();
    let node1 = model.add_asset("Node", Some("Node 1".into()), None, None, None, true).unwrap();
    let node2 = model.add_asset("Node", Some("Node 2".into()), None, None, None, true).unwrap();
    let target1 = model.add_asset("Target", Some("Target 1".into()), None, None, None, true).unwrap();
    let target2 = model.add_asset("Target", Some("Target 2".into()), None, None, None, true).unwrap();

    model.add_associated_assets(origin, "setA", HashSet::from([node1, node2])).unwrap();
    model.add_associated_assets(origin, "setB", HashSet::from([node2])).unwrap();
    model.add_associated_assets(node1, "next", HashSet::from([target1])).unwrap();
    model.add_associated_assets(node2, "next", HashSet::from([target2])).unwrap();

    let mut ag = AttackGraph::from_model(&model).unwrap();
    let check_node = ag.get_node_by_full_name("Origin:check").unwrap();
    assert!(ag.nodes[check_node].children.contains(&ag.get_node_by_full_name("Target 1:reach").unwrap()));
    assert!(!ag.nodes[check_node].children.contains(&ag.get_node_by_full_name("Target 2:reach").unwrap()));

    model.remove_associated_assets(node1, "next", &HashSet::from([target1])).unwrap();
    model.remove_associated_assets(node2, "next", &HashSet::from([target2])).unwrap();
    ag.partially_regenerate_graph(
        &model,
        &HashSet::new(),
        &HashSet::new(),
        &HashMap::new(),
        &HashSet::from([(node1, "next".to_string(), target1), (node2, "next".to_string(), target2)])).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);

    model.add_associated_assets(node1, "next", HashSet::from([target1])).unwrap();
    model.add_associated_assets(node2, "next", HashSet::from([target2])).unwrap();
    ag.partially_regenerate_graph(
        &model,
        &HashSet::new(),
        &HashSet::from([(node1, "next".to_string(), target1), (node2, "next".to_string(), target2)]),
        &HashMap::new(),
        &HashSet::new()).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);
}

#[test]
fn partial_regeneration_shared_assoc_sibling() {
    // Two sibling subtypes share an inherited association but only one
    // of them defines the attack step that uses it.
    let lang_graph = compile_lang("shared_assoc_sibling.mal");
    let mut model = Model::new("Test Model", lang_graph.clone());

    let a = model.add_asset("SiblingA", Some("A1".into()), None, None, None, true).unwrap();
    let b = model.add_asset("SiblingB", Some("B1".into()), None, None, None, true).unwrap();
    let t1 = model.add_asset("Target", Some("T1".into()), None, None, None, true).unwrap();

    model.add_associated_assets(b, "target", HashSet::from([t1])).unwrap();
    let mut ag = AttackGraph::from_model(&model).unwrap();

    model.remove_associated_assets(b, "target", &HashSet::from([t1])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(b, "target".to_string(), t1)])).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);

    model.add_associated_assets(b, "target", HashSet::from([t1])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(b, "target".to_string(), t1)]), &HashMap::new(), &HashSet::new()).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);

    model.add_associated_assets(a, "target", HashSet::from([t1])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(a, "target".to_string(), t1)]), &HashMap::new(), &HashSet::new()).unwrap();
    let regenerated = AttackGraph::from_model(&model).unwrap();
    check_graph_equivalence(&model, &regenerated, &ag);
}

#[test]
fn partial_regeneration_corelang() {
    let lang_graph = corelang();
    let mut model = Model::new("Test Model", lang_graph.clone());
    let corpnet = model.add_asset("Network", Some("CorpNet".into()), None, None, None, true).unwrap();
    let mut ag = AttackGraph::from_model(&model).unwrap();

    macro_rules! check {
        () => {
            let regenerated = AttackGraph::from_model(&model).unwrap();
            check_graph_equivalence(&model, &regenerated, &ag);
        };
    }

    let webapp = model.add_asset("Application", Some("WebApp".into()), None, None, None, true).unwrap();
    model.add_associated_assets(corpnet, "applications", HashSet::from([webapp])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([webapp]), &HashSet::from([(corpnet, "applications".to_string(), webapp)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    let webhw = model.add_asset("Hardware", Some("WebServer".into()), None, None, None, true).unwrap();
    model.add_associated_assets(webhw, "sysExecutedApps", HashSet::from([webapp])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([webhw]), &HashSet::from([(webhw, "sysExecutedApps".to_string(), webapp)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    let webdata = model.add_asset("Data", Some("WebAppData".into()), None, None, None, true).unwrap();
    model.add_associated_assets(webapp, "containedData", HashSet::from([webdata])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([webdata]), &HashSet::from([(webapp, "containedData".to_string(), webdata)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    let dbapp = model.add_asset("Application", Some("DBApp".into()), None, None, None, true).unwrap();
    model.add_associated_assets(corpnet, "applications", HashSet::from([dbapp])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::from([dbapp]), &HashSet::from([(corpnet, "applications".to_string(), dbapp)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    model.add_associated_assets(webapp, "appExecutedApps", HashSet::from([dbapp])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::from([(webapp, "appExecutedApps".to_string(), dbapp)]), &HashMap::new(), &HashSet::new()).unwrap();
    check!();

    let dbhw = model.add_asset("Hardware", Some("DBServer".into()), None, None, None, true).unwrap();
    let dbdata = model.add_asset("Data", Some("DBData".into()), None, None, None, true).unwrap();
    model.add_associated_assets(dbhw, "sysExecutedApps", HashSet::from([dbapp])).unwrap();
    model.add_associated_assets(dbhw, "hostedData", HashSet::from([dbdata])).unwrap();
    model.add_associated_assets(dbapp, "containedData", HashSet::from([dbdata])).unwrap();
    ag.partially_regenerate_graph(
        &model,
        &HashSet::from([dbhw, dbdata]),
        &HashSet::from([
            (dbhw, "sysExecutedApps".to_string(), dbapp),
            (dbhw, "hostedData".to_string(), dbdata),
            (dbapp, "containedData".to_string(), dbdata),
        ]),
        &HashMap::new(),
        &HashSet::new()).unwrap();
    check!();

    let netidps = model.add_asset("IDPS", Some("NetIDPS".into()), None, None, None, true).unwrap();
    model.add_associated_assets(netidps, "protectedApps", HashSet::from([webapp, dbapp])).unwrap();
    ag.partially_regenerate_graph(
        &model,
        &HashSet::from([netidps]),
        &HashSet::from([(netidps, "protectedApps".to_string(), webapp), (netidps, "protectedApps".to_string(), dbapp)]),
        &HashMap::new(),
        &HashSet::new()).unwrap();
    check!();

    let svcidentity = model.add_asset("Identity", Some("SvcIdentity".into()), None, None, None, true).unwrap();
    let svccreds = model.add_asset("Credentials", Some("SvcCreds".into()), None, None, None, true).unwrap();
    let alice = model.add_asset("User", Some("Alice".into()), None, None, None, true).unwrap();
    model.add_associated_assets(svcidentity, "credentials", HashSet::from([svccreds])).unwrap();
    model.add_associated_assets(alice, "userIds", HashSet::from([svcidentity])).unwrap();
    model.add_associated_assets(svcidentity, "readPrivData", HashSet::from([webdata])).unwrap();
    ag.partially_regenerate_graph(
        &model,
        &HashSet::from([svcidentity, svccreds, alice]),
        &HashSet::from([
            (svcidentity, "credentials".to_string(), svccreds),
            (alice, "userIds".to_string(), svcidentity),
            (svcidentity, "readPrivData".to_string(), webdata),
        ]),
        &HashMap::new(),
        &HashSet::new()).unwrap();
    check!();

    // --- Phase 2: change model (almost) completely ---
    let mut removed_assets = HashSet::new();
    let mut removed_associations = HashSet::new();
    for (&asset_id, asset) in &model.assets {
        for (fieldname, assoc_assets) in &asset.associated_assets {
            for &other_id in assoc_assets {
                removed_associations.insert((asset_id, fieldname.clone(), other_id));
            }
        }
    }
    for &asset_id in model.asset_order.clone().iter() {
        if asset_id != corpnet {
            removed_assets.insert(asset_id);
        }
    }
    // Strip the associations now (so partially_regenerate_graph sees the
    // post-removal truth when relinking), but defer actually deleting the
    // assets themselves until after that call runs - no ordering
    // contract requires this any more (`snapshot` below captures what's
    // needed regardless of order), it just keeps this test's structure
    // close to the Python original. `removed_associations` contains both
    // directions of each link; the second attempt at either direction is
    // expected to report "not associated" since the first already
    // cleared both sides - ignored here.
    for (asset_id, fieldname, other_id) in &removed_associations {
        let _ = model.remove_associated_assets(*asset_id, fieldname, &HashSet::from([*other_id]));
    }

    let mut new_assets = HashSet::new();
    let mut new_associations = HashSet::new();

    let dmz = model.add_asset("Network", Some("DMZ".into()), None, None, None, true).unwrap();
    let backup = model.add_asset("Network", Some("BackupNet".into()), None, None, None, true).unwrap();
    new_assets.extend([dmz, backup]);

    let cr1 = model.add_asset("ConnectionRule", Some("CR-CorpNet-DMZ".into()), None, None, None, true).unwrap();
    let cr2 = model.add_asset("ConnectionRule", Some("CR-DMZ-Backup".into()), None, None, None, true).unwrap();
    new_assets.extend([cr1, cr2]);
    model.add_associated_assets(cr1, "networks", HashSet::from([corpnet, dmz])).unwrap();
    model.add_associated_assets(cr2, "networks", HashSet::from([dmz, backup])).unwrap();
    new_associations.extend([
        (cr1, "networks".to_string(), corpnet),
        (cr1, "networks".to_string(), dmz),
        (cr2, "networks".to_string(), dmz),
        (cr2, "networks".to_string(), backup),
    ]);

    let proxyapp = model.add_asset("Application", Some("ProxyApp".into()), None, None, None, true).unwrap();
    let dmzapp = model.add_asset("Application", Some("DmzApp".into()), None, None, None, true).unwrap();
    let backupapp = model.add_asset("Application", Some("BackupApp".into()), None, None, None, true).unwrap();
    new_assets.extend([proxyapp, dmzapp, backupapp]);
    model.add_associated_assets(corpnet, "applications", HashSet::from([proxyapp])).unwrap();
    model.add_associated_assets(dmz, "applications", HashSet::from([dmzapp])).unwrap();
    model.add_associated_assets(backup, "applications", HashSet::from([backupapp])).unwrap();
    new_associations.extend([
        (corpnet, "applications".to_string(), proxyapp),
        (dmz, "applications".to_string(), dmzapp),
        (backup, "applications".to_string(), backupapp),
    ]);

    let proxyhw = model.add_asset("Hardware", Some("ProxyServer".into()), None, None, None, true).unwrap();
    new_assets.insert(proxyhw);
    model.add_associated_assets(proxyhw, "sysExecutedApps", HashSet::from([proxyapp])).unwrap();
    new_associations.insert((proxyhw, "sysExecutedApps".to_string(), proxyapp));

    let shareddata = model.add_asset("Data", Some("SharedData".into()), None, None, None, true).unwrap();
    new_assets.insert(shareddata);
    model.add_associated_assets(proxyapp, "containedData", HashSet::from([shareddata])).unwrap();
    model.add_associated_assets(shareddata, "hardware", HashSet::from([proxyhw])).unwrap();
    new_associations.extend([
        (proxyapp, "containedData".to_string(), shareddata),
        (shareddata, "hardware".to_string(), proxyhw),
    ]);

    let svcidentity2 = model.add_asset("Identity", Some("SvcIdentity2".into()), None, None, None, true).unwrap();
    let svccreds2 = model.add_asset("Credentials", Some("SvcCreds2".into()), None, None, None, true).unwrap();
    let bob = model.add_asset("User", Some("Bob".into()), None, None, None, true).unwrap();
    new_assets.extend([svcidentity2, svccreds2, bob]);
    model.add_associated_assets(svcidentity2, "credentials", HashSet::from([svccreds2])).unwrap();
    model.add_associated_assets(bob, "userIds", HashSet::from([svcidentity2])).unwrap();
    model.add_associated_assets(svcidentity2, "readPrivData", HashSet::from([shareddata])).unwrap();
    new_associations.extend([
        (svcidentity2, "credentials".to_string(), svccreds2),
        (bob, "userIds".to_string(), svcidentity2),
        (svcidentity2, "readPrivData".to_string(), shareddata),
    ]);

    let edgeidps = model.add_asset("IDPS", Some("EdgeIDPS".into()), None, None, None, true).unwrap();
    new_assets.insert(edgeidps);
    model.add_associated_assets(edgeidps, "protectedApps", HashSet::from([proxyapp, dmzapp])).unwrap();
    new_associations.extend([
        (edgeidps, "protectedApps".to_string(), proxyapp),
        (edgeidps, "protectedApps".to_string(), dmzapp),
    ]);

    ag.partially_regenerate_graph(&model, &new_assets, &new_associations, &snapshot(&model, &removed_assets), &removed_associations).unwrap();
    for &asset_id in &removed_assets {
        model.remove_asset(asset_id).unwrap();
    }
    check!();

    // --- Phase 3: teardown ---
    model.remove_associated_assets(edgeidps, "protectedApps", &HashSet::from([dmzapp])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(edgeidps, "protectedApps".to_string(), dmzapp)])).unwrap();
    check!();

    model.remove_associated_assets(svcidentity2, "readPrivData", &HashSet::from([shareddata])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(svcidentity2, "readPrivData".to_string(), shareddata)])).unwrap();
    check!();

    model.remove_associated_assets(shareddata, "hardware", &HashSet::from([proxyhw])).unwrap();
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &HashMap::new(), &HashSet::from([(shareddata, "hardware".to_string(), proxyhw)])).unwrap();
    check!();

    let mut removed_assets = HashSet::new();
    let mut removed_associations = HashSet::new();
    for &asset_id in &[backup, backupapp, cr2] {
        for (fieldname, assoc_assets) in &model.assets[&asset_id].associated_assets {
            for &other_id in assoc_assets {
                removed_associations.insert((asset_id, fieldname.clone(), other_id));
            }
        }
    }
    for (asset_id, fieldname, other_id) in &removed_associations {
        let _ = model.remove_associated_assets(*asset_id, fieldname, &HashSet::from([*other_id]));
    }
    for &asset_id in &[backup, backupapp, cr2] {
        removed_assets.insert(asset_id);
    }
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &removed_assets), &removed_associations).unwrap();
    for &asset_id in &[backup, backupapp, cr2] {
        model.remove_asset(asset_id).unwrap();
    }
    check!();

    // Final bulk teardown back to only CorpNet.
    let mut removed_assets = HashSet::new();
    let mut removed_associations = HashSet::new();
    for (&asset_id, asset) in &model.assets {
        for (fieldname, assoc_assets) in &asset.associated_assets {
            for &other_id in assoc_assets {
                removed_associations.insert((asset_id, fieldname.clone(), other_id));
            }
        }
    }
    for &asset_id in model.asset_order.clone().iter() {
        if asset_id != corpnet && model.assets.contains_key(&asset_id) {
            removed_assets.insert(asset_id);
        }
    }
    for (asset_id, fieldname, other_id) in &removed_associations {
        let _ = model.remove_associated_assets(*asset_id, fieldname, &HashSet::from([*other_id]));
    }
    ag.partially_regenerate_graph(&model, &HashSet::new(), &HashSet::new(), &snapshot(&model, &removed_assets), &removed_associations).unwrap();
    for &asset_id in &removed_assets {
        model.remove_asset(asset_id).unwrap();
    }
    check!();

    assert_eq!(model.assets.len(), 1);
    assert!(model.assets.contains_key(&corpnet));
}

#[test]
fn switch_fieldname_unknown_fieldname_raises() {
    let lang_graph = training_lang();
    let mut model = Model::new("Test Model", lang_graph);
    let network = model.add_asset("Network", Some("LAN".into()), None, None, None, true).unwrap();

    let err = maltoolbox_attackgraph::partially_generate::switch_fieldname(&model, network, "doesNotExist").unwrap_err();
    assert!(err.to_string().contains("not found in associations"));
}

#[test]
fn nodes_to_be_removed_missing_node_raises() {
    let lang_graph = training_lang();
    let mut model = Model::new("Test Model", lang_graph);
    let network = model.add_asset("Network", Some("LAN".into()), None, None, None, true).unwrap();

    let err = maltoolbox_attackgraph::partially_generate::nodes_to_be_removed(
        &snapshot(&model, &HashSet::from([network])),
        &model,
        &IndexMap::new(),
    )
    .unwrap_err();
    assert!(err.to_string().contains("Failed to find"));
}
