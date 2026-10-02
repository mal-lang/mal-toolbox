//! Port of `tests/attackgraph/test_attackgraph.py`.
//!
//! Not ported:
//! - `test_attackgraph_init` (mocks Python internals, not a meaningful
//!   check in Rust)
//! - `test_load_attack_graph`/`test_attackgraph_save_load_no_model_given`/
//!   `test_attackgraph_save_and_load_json_yml_model_given` (need
//!   `AttackGraph` deserialization - `load_from_file`/`from_dict` were
//!   never ported, only `save_to_file`; out of scope for the CLI too)
//! - `test_attackgraph_generate_graph` (redundant with the oracle-verified
//!   `graph_golden.rs`/`partial_regen_golden.rs`, which already check
//!   full regeneration produces the right node set)
//! - `test_attackgraph_deepcopy`/`test_deepcopy_memo_test` (Python
//!   `copy.deepcopy` semantics have no meaningful Rust equivalent here)
//! - `test_attackgraph_pickle`/`test_model_pickle` (no Rust equivalent)
//!
//! `test_create_dynamic_ag` is ported as `create_dynamic_ag` below, but
//! only its first half (asserting the `Wiper:test` node's
//! `additive_model_effects` structure) - the Python original's second
//! half manually walks the traversal chain and calls `model.add_asset`/
//! `add_associated_assets` as a *demonstration* of how a downstream
//! consumer (e.g. mal-simulator) would apply the effect; it doesn't
//! exercise any new behavior of this crate, since those `Model` methods
//! are already covered by `maltoolbox-model`'s own test suite. Also uses
//! a minimal hand-built model (one `Device`, one `Wiper`) rather than
//! the oracle's full `wiper_model.yml` topology, since the model-effect
//! structure being checked is a language-graph-level property, the same
//! for every `Wiper:test` node regardless of which model it's attached
//! to.

use std::collections::HashSet;
use std::rc::Rc;

use maltoolbox_attackgraph::AttackGraph;
use maltoolbox_language::from_mar_archive;
use maltoolbox_model::Model;

fn fixtures_dir() -> &'static std::path::Path {
    std::path::Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures"))
}

fn lang_fixtures_dir() -> &'static std::path::Path {
    std::path::Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../maltoolbox-language/tests/fixtures"
    ))
}

fn corelang() -> Rc<maltoolbox_language::graph::LanguageGraph> {
    Rc::new(from_mar_archive(lang_fixtures_dir().join("org.mal-lang.coreLang-1.0.0.mar")).expect("load corelang"))
}

#[test]
fn get_node_by_full_name_suggests_similar() {
    let lang_graph = corelang();
    let mut model = Model::new("Test Model", lang_graph);
    let app1 = model.add_asset("Application", Some("Application 1".into()), None, None, None, true).unwrap();
    let app2 = model.add_asset("Application", Some("Application 2".into()), None, None, None, true).unwrap();
    model.add_associated_assets(app1, "appExecutedApps", HashSet::from([app2])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");

    let err = attack_graph.get_node_by_full_name("Application 2").unwrap_err();
    let msg = err.to_string();
    assert!(msg.contains("Could not find node with name \"Application 2\""));
    assert!(msg.contains("Did you mean"));
    // Both of "Application 2:read" and "Application 2:deny" are
    // equidistant (by Levenshtein) from the query; which one Rust's
    // HashMap iterates first isn't guaranteed to match Python's dict
    // order, so just check both appear as candidates somewhere.
    assert!(msg.contains("Application 2:"));
}

#[test]
fn create_dynamic_ag() {
    use maltoolbox_language::graph::model_effect::AssocTraversalElem;

    let lang = Rc::new(
        maltoolbox_language::from_mal_spec(lang_fixtures_dir().join("wiperLang.mal"))
            .expect("compile wiperLang"),
    );
    let mut model = Model::new("Wiper Model", lang.clone());

    let device = model.add_asset("Device", Some("InfectedDevice".into()), None, None, None, true).unwrap();
    let wiper = model.add_asset("Wiper", Some("Wiper".into()), None, None, None, true).unwrap();
    model.add_associated_assets(device, "malware", HashSet::from([wiper])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");
    let wiper_test = attack_graph
        .get_node_by_full_name("Wiper:test")
        .expect("Wiper:test node");
    let node = &attack_graph.nodes[wiper_test];

    let effects = node
        .additive_model_effects
        .as_ref()
        .expect("Wiper:test should have additive model effects (own + inherited from Malware)");

    // Two effects are expected: one inherited from `Malware`'s own
    // `test` (`A> self / victim[Device]`), one from `Wiper`'s own `test`
    // declaration (`+A> self / victim[C2Server]`) - an *append*, so it
    // adds to the inherited effect rather than replacing it.
    assert_eq!(effects.len(), 2);
    let mut seen_filters = HashSet::new();

    for model_effect in effects {
        assert_eq!(
            model_effect.base.len(),
            1,
            "Too many assoc traversals for base in dynamic statement"
        );
        match &model_effect.base[0] {
            AssocTraversalElem::Traversal(t) => {
                assert_eq!(t.field_name, "self", "Base field name is not correct for dynamic statement")
            }
            other => panic!("expected a plain traversal for base, got {other:?}"),
        }

        for dyn_target in &model_effect.targets {
            assert!(!dyn_target.assoc_op, "Dynamic target should not operate on associations");
            assert_eq!(
                dyn_target.assoc_traversal.len(),
                1,
                "Dynamic target should have exactly one assoc traversal"
            );
            match &dyn_target.assoc_traversal[0] {
                AssocTraversalElem::Traversal(t) => {
                    assert_eq!(
                        t.field_name, "victim",
                        "Dynamic target assoc traversal field name is not correct"
                    );
                    let filter_id = t.asset_filter.expect("expected an asset type filter");
                    let filter_name = lang.asset(filter_id).name.clone();
                    assert!(
                        matches!(filter_name.as_str(), "C2Server" | "Device"),
                        "unexpected asset filter {filter_name}"
                    );
                    seen_filters.insert(filter_name);
                }
                other => panic!("expected a plain traversal for the dynamic target, got {other:?}"),
            }
        }
    }

    assert_eq!(seen_filters, HashSet::from(["C2Server".to_string(), "Device".to_string()]));
}

#[test]
fn according_to_corelang() {
    let lang_graph = corelang();
    let mut model = Model::new("Test Model", lang_graph);
    let app1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let app2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model.add_associated_assets(app1, "appExecutedApps", HashSet::from([app2])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");

    let expected_names: HashSet<&str> = [
        "notPresent", "attemptUseVulnerability", "successfulUseVulnerability", "useVulnerability",
        "attemptReverseReach", "successfulReverseReach", "reverseReach", "localConnect",
        "networkConnectUninspected", "networkConnectInspected", "networkConnect",
        "specificAccessNetworkConnect", "accessNetworkAndConnections", "attemptNetworkConnectFromResponse",
        "networkConnectFromResponse", "specificAccessFromLocalConnection", "specificAccessFromNetworkConnection",
        "specificAccess", "bypassContainerization", "authenticate", "specificAccessAuthenticate",
        "localAccess", "networkAccess", "fullAccess", "physicalAccessAchieved", "attemptUnsafeUserActivity",
        "successfulUnsafeUserActivity", "unsafeUserActivity", "attackerUnsafeUserActivityCapability",
        "attackerUnsafeUserActivityCapabilityWithReverseReach", "attackerUnsafeUserActivityCapabilityWithoutReverseReach",
        "supplyChainAuditing", "bypassSupplyChainAuditing", "supplyChainAuditingBypassed",
        "attemptFullAccessFromSupplyChainCompromise", "fullAccessFromSupplyChainCompromise",
        "attemptReadFromSoftProdVulnerability", "attemptModifyFromSoftProdVulnerability",
        "attemptDenyFromSoftProdVulnerability", "softwareCheck", "softwareProductVulnerabilityLocalAccessAchieved",
        "softwareProductVulnerabilityNetworkAccessAchieved", "softwareProductVulnerabilityPhysicalAccessAchieved",
        "softwareProductVulnerabilityLowPrivilegesAchieved", "softwareProductVulnerabilityHighPrivilegesAchieved",
        "softwareProductVulnerabilityUserInteractionAchieved", "attemptSoftwareProductAbuse",
        "softwareProductAbuse", "readFromSoftProdVulnerability", "modifyFromSoftProdVulnerability",
        "denyFromSoftProdVulnerability", "attemptApplicationRespondConnectThroughData",
        "successfulApplicationRespondConnectThroughData", "applicationRespondConnectThroughData",
        "attemptAuthorizedApplicationRespondConnectThroughData", "successfulAuthorizedApplicationRespondConnectThroughData",
        "authorizedApplicationRespondConnectThroughData", "attemptRead", "successfulRead", "read",
        "specificAccessRead", "attemptModify", "successfulModify", "modify", "specificAccessModify",
        "attemptDeny", "successfulDeny", "deny", "specificAccessDelete", "denyFromNetworkingAsset",
        "denyFromLockout",
    ]
    .into_iter()
    .collect();

    let actual_names: HashSet<&str> = attack_graph.nodes.values().map(|n| n.name.as_str()).collect();
    assert_eq!(actual_names, expected_names);

    let expected_notpresent_children: HashSet<&str> = [
        "successfulUseVulnerability", "successfulReverseReach", "networkConnectFromResponse",
        "specificAccessFromLocalConnection", "specificAccessFromNetworkConnection", "localAccess",
        "networkAccess", "successfulUnsafeUserActivity", "fullAccessFromSupplyChainCompromise",
        "readFromSoftProdVulnerability", "modifyFromSoftProdVulnerability", "denyFromSoftProdVulnerability",
        "successfulApplicationRespondConnectThroughData", "successfulAuthorizedApplicationRespondConnectThroughData",
        "successfulRead", "successfulModify", "successfulDeny",
    ]
    .into_iter()
    .collect();

    let notpresent = attack_graph
        .nodes
        .values()
        .find(|n| n.name == "notPresent")
        .expect("notPresent node");
    let notpresent_children: HashSet<&str> = notpresent
        .children
        .iter()
        .map(|&id| attack_graph.nodes[id].name.as_str())
        .collect();
    assert_eq!(notpresent_children, expected_notpresent_children);
}

#[test]
fn remove_node() {
    let lang_graph = corelang();
    let mut model = Model::new("Test Model", lang_graph);
    let app1 = model.add_asset("Application", None, None, None, None, true).unwrap();
    let app2 = model.add_asset("Application", None, None, None, None, true).unwrap();
    model.add_associated_assets(app1, "appExecutedApps", HashSet::from([app2])).unwrap();

    let mut attack_graph = AttackGraph::from_model(&model).expect("build attack graph");

    let node_to_remove = attack_graph.nodes.keys().next().unwrap();
    let parents: Vec<_> = attack_graph.nodes[node_to_remove].parents.iter().copied().collect();
    let children: Vec<_> = attack_graph.nodes[node_to_remove].children.iter().copied().collect();

    attack_graph.remove_node(node_to_remove).unwrap();

    assert!(!attack_graph.nodes.contains_key(node_to_remove));
    for parent in parents {
        assert!(!attack_graph.nodes[parent].children.contains(&node_to_remove));
    }
    for child in children {
        assert!(!attack_graph.nodes[child].parents.contains(&node_to_remove));
    }
}

#[test]
fn subtype() {
    let spec = maltoolbox_language::compile_file(lang_fixtures_dir().join("subtype_attack_step.mal")).unwrap();
    let lang_graph = Rc::new(maltoolbox_language::generate_graph(spec).unwrap());
    let mut model = Model::new("Test Model", lang_graph);

    let base1 = model.add_asset("BaseAsset", Some("BaseAsset 1".into()), None, None, None, true).unwrap();
    let sub1 = model.add_asset("SubAsset", Some("SubAsset 1".into()), None, None, None, true).unwrap();
    let other1 = model.add_asset("OtherAsset", Some("OtherAsset 1".into()), None, None, None, true).unwrap();

    model.add_associated_assets(sub1, "field2", HashSet::from([other1])).unwrap();
    model.add_associated_assets(base1, "field2", HashSet::from([other1])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).unwrap();

    let ba1_base1 = attack_graph.get_node_by_full_name("BaseAsset 1:base_step1").unwrap();
    let ba1_base2 = attack_graph.get_node_by_full_name("BaseAsset 1:base_step2").unwrap();
    let sa1_base1 = attack_graph.get_node_by_full_name("SubAsset 1:base_step1").unwrap();
    let sa1_base2 = attack_graph.get_node_by_full_name("SubAsset 1:base_step2").unwrap();
    let sa1_sub1 = attack_graph.get_node_by_full_name("SubAsset 1:subasset_step1").unwrap();
    let oa1_other1 = attack_graph.get_node_by_full_name("OtherAsset 1:other_step1").unwrap();

    let children = &attack_graph.nodes[oa1_other1].children;
    assert!(children.contains(&ba1_base1));
    assert!(!children.contains(&ba1_base2));
    assert!(children.contains(&sa1_base1));
    assert!(children.contains(&sa1_base2));
    assert!(children.contains(&sa1_sub1));
}

#[test]
fn setops() {
    let spec = maltoolbox_language::compile_file(lang_fixtures_dir().join("set_ops.mal")).unwrap();
    let lang_graph = Rc::new(maltoolbox_language::generate_graph(spec).unwrap());
    let mut model = Model::new("Test Model", lang_graph);

    let origin = model.add_asset("Origin", Some("Origin".into()), None, None, None, true).unwrap();
    let t1 = model.add_asset("Target", Some("Target 1".into()), None, None, None, true).unwrap();
    let t2 = model.add_asset("Target", Some("Target 2".into()), None, None, None, true).unwrap();
    let t3 = model.add_asset("Target", Some("Target 3".into()), None, None, None, true).unwrap();

    model.add_associated_assets(origin, "setA", HashSet::from([t1, t2])).unwrap();
    model.add_associated_assets(origin, "setB", HashSet::from([t2, t3])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).unwrap();
    let check = attack_graph.get_node_by_full_name("Origin:check").unwrap();
    let children = &attack_graph.nodes[check].children;

    let get = |name: &str| attack_graph.get_node_by_full_name(name).unwrap();
    assert!(children.contains(&get("Target 1:unionResult")));
    assert!(!children.contains(&get("Target 1:intersectionResult")));
    assert!(children.contains(&get("Target 1:differenceResult")));
    assert!(children.contains(&get("Target 2:unionResult")));
    assert!(children.contains(&get("Target 2:intersectionResult")));
    assert!(!children.contains(&get("Target 2:differenceResult")));
    assert!(children.contains(&get("Target 3:unionResult")));
    assert!(!children.contains(&get("Target 3:intersectionResult")));
    assert!(!children.contains(&get("Target 3:differenceResult")));
}

#[test]
fn setops_adv() {
    let spec = maltoolbox_language::compile_file(lang_fixtures_dir().join("set_ops_adv.mal")).unwrap();
    let lang_graph = Rc::new(maltoolbox_language::generate_graph(spec).unwrap());
    let mut model = Model::new("Test Model", lang_graph);

    let hub1 = model.add_asset("Hub", Some("Hub 1".into()), None, None, None, true).unwrap();
    let hub2 = model.add_asset("Hub", Some("Hub 2".into()), None, None, None, true).unwrap();
    let hub3 = model.add_asset("Hub", Some("Hub 3".into()), None, None, None, true).unwrap();
    let t1 = model.add_asset("Target", Some("Target 1".into()), None, None, None, true).unwrap();
    let t2 = model.add_asset("Target", Some("Target 2".into()), None, None, None, true).unwrap();
    let t3 = model.add_asset("Target", Some("Target 3".into()), None, None, None, true).unwrap();

    model.add_associated_assets(hub2, "setA", HashSet::from([t1, t2])).unwrap();
    model.add_associated_assets(hub3, "setB", HashSet::from([t2, t3])).unwrap();
    model.add_associated_assets(hub1, "siblings", HashSet::from([hub2, hub3])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).unwrap();

    let get = |name: &str| attack_graph.get_node_by_full_name(name).unwrap();
    let hub1_inner = get("Hub 1:innerIntersection");
    let hub1_outer = get("Hub 1:outerIntersection");

    let inner_children = &attack_graph.nodes[hub1_inner].children;
    assert!(!inner_children.contains(&get("Target 1:intersectionResult")));
    assert!(!inner_children.contains(&get("Target 2:intersectionResult")));
    assert!(!inner_children.contains(&get("Target 3:intersectionResult")));

    let outer_children = &attack_graph.nodes[hub1_outer].children;
    assert!(!outer_children.contains(&get("Target 1:intersectionResult")));
    assert!(outer_children.contains(&get("Target 2:intersectionResult")));
    assert!(!outer_children.contains(&get("Target 3:intersectionResult")));
}

#[test]
fn transitive() {
    let spec = maltoolbox_language::compile_file(lang_fixtures_dir().join("transitive.mal")).unwrap();
    let lang_graph = Rc::new(maltoolbox_language::generate_graph(spec).unwrap());
    let mut model = Model::new("Test Model", lang_graph);

    let assets: Vec<i64> = (1..=6)
        .map(|i| {
            model
                .add_asset("TestAsset", Some(format!("TestAsset {i}")), None, None, None, true)
                .unwrap()
        })
        .collect();
    let (a1, a2, a3, a4, a5, a6) = (assets[0], assets[1], assets[2], assets[3], assets[4], assets[5]);

    model.add_associated_assets(a1, "field2", HashSet::from([a2])).unwrap();
    model.add_associated_assets(a2, "field2", HashSet::from([a3])).unwrap();
    model.add_associated_assets(a3, "field2", HashSet::from([a4])).unwrap();
    model.add_associated_assets(a3, "field2", HashSet::from([a5])).unwrap();
    model.add_associated_assets(a6, "field2", HashSet::from([a1])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).unwrap();
    let step = |i: usize| attack_graph.get_node_by_full_name(&format!("TestAsset {i}:test_step")).unwrap();

    let expected_reachable: [&[usize]; 6] = [
        &[1, 2, 3, 4, 5],
        &[2, 3, 4, 5],
        &[3, 4, 5],
        &[4],
        &[5],
        &[1, 2, 3, 4, 5, 6],
    ];

    for (i, reachable) in expected_reachable.iter().enumerate() {
        let from = step(i + 1);
        let children = &attack_graph.nodes[from].children;
        for j in 1..=6 {
            let expects_reachable = reachable.contains(&j);
            assert_eq!(
                children.contains(&step(j)),
                expects_reachable,
                "TestAsset {}:test_step -> TestAsset {}:test_step",
                i + 1,
                j
            );
        }
    }
}

#[test]
fn transitive_advanced() {
    let spec = maltoolbox_language::compile_file(lang_fixtures_dir().join("transitive_advanced.mal")).unwrap();
    let lang_graph = Rc::new(maltoolbox_language::generate_graph(spec).unwrap());
    let mut model = Model::new("Test Model", lang_graph);

    let a1 = model.add_asset("TestAsset", Some("TestAsset 1".into()), None, None, None, true).unwrap();
    let a2 = model.add_asset("TestAsset", Some("TestAsset 2".into()), None, None, None, true).unwrap();
    let a3 = model.add_asset("TestAsset", Some("TestAsset 3".into()), None, None, None, true).unwrap();
    let a4 = model.add_asset("TestAsset", Some("TestAsset 4".into()), None, None, None, true).unwrap();

    model.add_associated_assets(a1, "fieldA2", HashSet::from([a2, a3])).unwrap();
    model.add_associated_assets(a1, "fieldB2", HashSet::from([a3, a4])).unwrap();

    let attack_graph = AttackGraph::from_model(&model).unwrap();
    let step = |n: &str| attack_graph.get_node_by_full_name(&format!("{n}:test_step")).unwrap();
    let children = &attack_graph.nodes[step("TestAsset 1")].children;

    assert!(children.contains(&step("TestAsset 1")));
    assert!(!children.contains(&step("TestAsset 2")));
    assert!(children.contains(&step("TestAsset 3")));
    assert!(!children.contains(&step("TestAsset 4")));
}

#[test]
fn create_attack_graph_wrapper() {
    let mar = lang_fixtures_dir().join("org.mal-lang.coreLang-1.0.0.mar");
    let model = fixtures_dir().join("simple_example_model.yml");
    maltoolbox_attackgraph::create_attack_graph(mar, model).expect("create_attack_graph should not error");
}

#[test]
fn create_ag_from_model() {
    // Predefined model in trainingLang:
    // User:3 --- Host:0 --- Network:3 --- Host:1
    //              |
    //            Data:2
    let mar = fixtures_dir().join("org.mal-lang.trainingLang-1.0.0.mar");
    let model_path = fixtures_dir().join("simple_traininglang_model.yml");
    let (attack_graph, model) = maltoolbox_attackgraph::create_attack_graph(mar, model_path).unwrap();

    let full_names: HashSet<String> = attack_graph
        .nodes
        .keys()
        .map(|k| attack_graph.full_name_of(k, Some(&model)))
        .collect();
    let expected: HashSet<String> = [
        "Host:0:notPresent", "Host:0:authenticate", "Host:0:connect", "Host:0:access",
        "Host:1:notPresent", "Host:1:authenticate", "Host:1:connect", "Host:1:access",
        "Data:2:notPresent", "Data:2:read", "Data:2:modify",
        "User:3:notPresent", "User:3:compromise", "User:3:phishing",
        "Network:3:access",
    ]
    .into_iter()
    .map(String::from)
    .collect();
    assert_eq!(full_names, expected);

    let check = |parent_fn: &str, children_fns: &[&str]| {
        let parent = attack_graph.get_node_by_full_name(parent_fn).unwrap();
        let actual_children: HashSet<String> = attack_graph.nodes[parent]
            .children
            .iter()
            .map(|&c| attack_graph.full_name_of(c, Some(&model)))
            .collect();
        let expected_children: HashSet<String> = children_fns.iter().map(|s| s.to_string()).collect();
        assert_eq!(actual_children, expected_children, "children of {parent_fn}");

        for child_fn in children_fns {
            let child = attack_graph.get_node_by_full_name(child_fn).unwrap();
            let parent_names: HashSet<String> = attack_graph.nodes[child]
                .parents
                .iter()
                .map(|&p| attack_graph.full_name_of(p, Some(&model)))
                .collect();
            assert!(parent_names.contains(parent_fn), "{child_fn} should have parent {parent_fn}");
        }
    };

    check("Host:0:notPresent", &["Host:0:connect", "Host:0:access"]);
    check("Host:0:authenticate", &["Host:0:access"]);
    check("Host:0:connect", &["Host:0:access"]);
    check("Host:0:access", &["Data:2:modify", "Data:2:read", "Network:3:access"]);
    check("Host:1:notPresent", &["Host:1:connect", "Host:1:access"]);
    check("Host:1:authenticate", &["Host:1:access"]);
    check("Host:1:connect", &["Host:1:access"]);
    check("Host:1:access", &["Network:3:access"]);
    check("Data:2:notPresent", &["Data:2:read", "Data:2:modify"]);
    check("Data:2:read", &[]);
    check("Data:2:modify", &[]);
    check("User:3:notPresent", &["User:3:compromise"]);
    check("User:3:compromise", &["Host:0:authenticate"]);
    check("User:3:phishing", &["User:3:compromise"]);
    check("Network:3:access", &["Host:0:connect", "Host:1:connect"]);
}

#[test]
fn create_ag_step_lists() {
    let mar = fixtures_dir().join("org.mal-lang.trainingLang-1.0.0.mar");
    let model_path = fixtures_dir().join("simple_traininglang_model.yml");
    let (attack_graph, _model) = maltoolbox_attackgraph::create_attack_graph(mar, model_path).unwrap();

    let defenses: HashSet<_> = attack_graph
        .nodes
        .iter()
        .filter(|(_, n)| n.step_type == maltoolbox_language::graph::attack_step::AttackStepType::Defense)
        .map(|(k, _)| k)
        .collect();
    let attacks: HashSet<_> = attack_graph
        .nodes
        .iter()
        .filter(|(_, n)| {
            matches!(
                n.step_type,
                maltoolbox_language::graph::attack_step::AttackStepType::Or
                    | maltoolbox_language::graph::attack_step::AttackStepType::And
            )
        })
        .map(|(k, _)| k)
        .collect();

    assert_eq!(defenses, attack_graph.defense_steps.iter().copied().collect());
    assert_eq!(attacks, attack_graph.attack_steps.iter().copied().collect());
}
