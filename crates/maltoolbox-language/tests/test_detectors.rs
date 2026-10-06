//! Port of `tests/language/test_detectors.py`.
//!
//! Four tests here (`detector_unlabeled_context`, `multiple_detectors`,
//! `only_tpr`, `only_fpr`) exercise an *unlabeled* detector context, e.g.
//! `! logExploit (computerOfApp.authenticate) [tpr: 0.1]` with no label
//! before `[tpr...]`. Under `tree-sitter-mal` 1.3.0 (both the crates.io
//! release and a from-source build of the `v1.3.0` git tag) that construct
//! produced a parse error (a missing/error node between `)` and `[`),
//! despite parsing cleanly under Python's `tree_sitter_mal` 1.3.0 wheel -
//! an upstream grammar gap, not something worked around in this compiler
//! port. Fixed upstream in `tree-sitter-mal` 1.3.1; these tests were
//! `#[ignore]`d against 1.3.0 and un-ignored once the workspace picked up
//! 1.3.1.

use std::collections::HashSet;
use std::rc::Rc;

use maltoolbox_attackgraph::AttackGraph;
use maltoolbox_language::from_mal_spec;
use maltoolbox_model::Model;

fn fixtures_dir() -> &'static std::path::Path {
    std::path::Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures"))
}

fn tmp_lang_file(tag: &str, src: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "maltoolbox-detector-test-{tag}-{}",
        std::process::id()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("lang.mal");
    std::fs::write(&path, src).unwrap();
    path
}

#[test]
fn detector_presence() {
    let lang_graph =
        Rc::new(from_mal_spec(fixtures_dir().join("detector_lang.mal")).expect("compile"));
    let mut model = Model::new("Example Model", lang_graph);
    let comp1 = model
        .add_asset(
            "Computer",
            Some("Computer 1".into()),
            None,
            None,
            None,
            true,
        )
        .unwrap();
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
        .add_associated_assets(comp1, "computerApps", HashSet::from([app1]))
        .unwrap();
    model
        .add_associated_assets(app1, "toApplications", HashSet::from([app2]))
        .unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");

    let app1_exploit = attack_graph
        .get_node_by_full_name("Application 1:exploit")
        .expect("node");
    let node = &attack_graph.nodes[app1_exploit];
    assert!(!node.detectors.is_empty(), "expected detectors on exploit");

    let log_exploit = node
        .detectors
        .get("logExploit")
        .expect("logExploit detector");
    assert_eq!(log_exploit.tprate, Some(0.9));
    assert_eq!(log_exploit.fprate, Some(0.1));
    assert!(!log_exploit.potential_context.is_empty());

    let comp_nodes = log_exploit
        .potential_context
        .get("comp")
        .expect("comp context");
    assert_eq!(comp_nodes.len(), 1);
    let comp_node_key = *comp_nodes.iter().next().unwrap();
    assert_eq!(
        attack_graph.full_name_of(comp_node_key, Some(&model)),
        "Computer 1:authenticate"
    );
}

#[test]
fn detector_unlabeled_context() {
    let lang_str = r#"
    #id: "test-actions-effects"
    #version: "0.0.0"

    category System{
        asset Computer {
        & physicalAccess
            -> attemptAuthenticate

        | attemptAuthenticate [HardAndCertain]
            -> authenticate

        & effect authenticate
            -> computerApps.attemptExploit
        }

        asset Application {
        # shutDown
            -> exploit

        | attemptExploit [HardAndCertain]
            -> exploit

        & effect exploit
            ! logExploit (computerOfApp.authenticate) [tpr: 0.9, fpr: 0.1]
            -> toApplications.attemptExploit,
            dataOnApp.read
        }

        asset Data {
        | read
        }
    }

    associations {
        Computer [computerOfApp] * <-- appExecution --> * [computerApps] Application
        Application [fromApplications] * <-- AppToAppCommunication --> * [toApplications] Application
        Data [dataOnApp] * <-- AppData --> * [appWithData] Application
    }
    "#;
    let path = tmp_lang_file("unlabeled-context", lang_str);
    let lang_graph = Rc::new(from_mal_spec(&path).expect("compile"));
    let mut model = Model::new("Test Model", lang_graph);
    let comp1 = model
        .add_asset(
            "Computer",
            Some("Computer 1".into()),
            None,
            None,
            None,
            true,
        )
        .unwrap();
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
    model
        .add_associated_assets(comp1, "computerApps", HashSet::from([app1]))
        .unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");
    let app1_exploit = attack_graph
        .get_node_by_full_name("Application 1:exploit")
        .expect("node");
    let detectors = &attack_graph.nodes[app1_exploit].detectors;
    assert!(!detectors.is_empty());
    let log_exploit = &detectors["logExploit"];
    assert_eq!(log_exploit.fprate, Some(0.1));
    assert_eq!(log_exploit.tprate, Some(0.9));

    let computer1_authenticate = attack_graph
        .get_node_by_full_name("Computer 1:authenticate")
        .expect("node");
    assert_eq!(log_exploit.potential_context.len(), 1);
    assert_eq!(
        log_exploit
            .potential_context
            .get("computerOfApp.authenticate"),
        Some(&HashSet::from([computer1_authenticate]))
    );
}

#[test]
fn multiple_detectors() {
    let lang_str = r#"
    #id: "test-actions-effects"
    #version: "0.0.0"

    category System{
        asset Computer {
        & physicalAccess
            ! physicalAccessDetector [tpr: 0.8, fpr: 0.2]
            -> attemptAuthenticate

        | attemptAuthenticate [HardAndCertain]
            -> authenticate

        & effect authenticate
            -> computerApps.attemptExploit
        }

        asset Application {
        # shutDown
            -> exploit

        | attemptExploit [HardAndCertain]
            -> exploit

        & effect exploit
            ! logExploit (computerOfApp.authenticate) [tpr: 0.9, fpr: 0.1]
            ! logExploit2
            -> toApplications.attemptExploit,
            dataOnApp.read
        }

        asset Data {
        | read
        }
    }

    associations {
        Computer [computerOfApp] * <-- appExecution --> * [computerApps] Application
        Application [fromApplications] * <-- AppToAppCommunication --> * [toApplications] Application
        Data [dataOnApp] * <-- AppData --> * [appWithData] Application
    }
    "#;
    let path = tmp_lang_file("multiple-detectors", lang_str);
    let lang_graph = Rc::new(from_mal_spec(&path).expect("compile"));
    let mut model = Model::new("Test Model", lang_graph);
    let comp1 = model
        .add_asset(
            "Computer",
            Some("Computer 1".into()),
            None,
            None,
            None,
            true,
        )
        .unwrap();
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
    model
        .add_associated_assets(comp1, "computerApps", HashSet::from([app1]))
        .unwrap();

    let attack_graph = AttackGraph::from_model(&model).expect("build attack graph");

    let comp1_physical_access = attack_graph
        .get_node_by_full_name("Computer 1:physicalAccess")
        .expect("node");
    assert!(attack_graph.nodes[comp1_physical_access]
        .detectors
        .contains_key("physicalAccessDetector"));

    let app1_exploit = attack_graph
        .get_node_by_full_name("Application 1:exploit")
        .expect("node");
    let detectors = &attack_graph.nodes[app1_exploit].detectors;
    assert!(detectors.contains_key("logExploit"));
    assert!(detectors.contains_key("logExploit2"));
    assert_eq!(detectors["logExploit"].tprate, Some(0.9));
    assert_eq!(detectors["logExploit"].fprate, Some(0.1));
    assert_eq!(detectors["logExploit2"].tprate, None);
    assert_eq!(detectors["logExploit2"].fprate, None);

    let physical_access_detector =
        &attack_graph.nodes[comp1_physical_access].detectors["physicalAccessDetector"];
    assert_eq!(physical_access_detector.tprate, Some(0.8));
    assert_eq!(physical_access_detector.fprate, Some(0.2));
}

fn single_rate_lang(rate_clause: &str) -> String {
    format!(
        r#"
    #id: "test-actions-effects"
    #version: "0.0.0"

    category System{{
        asset Computer {{
        & physicalAccess
            -> attemptAuthenticate

        | attemptAuthenticate [HardAndCertain]
            -> authenticate

        & effect authenticate
            -> computerApps.attemptExploit
        }}

        asset Application {{
        # shutDown
            -> exploit

        | attemptExploit [HardAndCertain]
            -> exploit

        & effect exploit
            ! logExploit (computerOfApp.authenticate) [{rate_clause}]
            -> toApplications.attemptExploit,
            dataOnApp.read
        }}

        asset Data {{
        | read
        }}
    }}

    associations {{
        Computer [computerOfApp] * <-- appExecution --> * [computerApps] Application
        Application [fromApplications] * <-- AppToAppCommunication --> * [toApplications] Application
        Data [dataOnApp] * <-- AppData --> * [appWithData] Application
    }}
    "#
    )
}

#[test]
fn only_tpr() {
    let path = tmp_lang_file("only-tpr", &single_rate_lang("tpr: 0.1"));
    let lang_graph = from_mal_spec(&path).expect("compile");
    let app = lang_graph.asset_id("Application").unwrap();
    let step = lang_graph.asset(app).attack_steps["exploit"];
    let det = &lang_graph.step(step).detectors["logExploit"];
    assert_eq!(det.tprate, Some(0.1));
    assert_eq!(det.fprate, None);
}

#[test]
fn only_fpr() {
    let path = tmp_lang_file("only-fpr", &single_rate_lang("fpr: 0.1"));
    let lang_graph = from_mal_spec(&path).expect("compile");
    let app = lang_graph.asset_id("Application").unwrap();
    let step = lang_graph.asset(app).attack_steps["exploit"];
    let det = &lang_graph.step(step).detectors["logExploit"];
    assert_eq!(det.tprate, None);
    assert_eq!(det.fprate, Some(0.1));
}

#[test]
fn wrong_labels_rejected() {
    let path = tmp_lang_file("wrong-labels", &single_rate_lang("fnl: 0.9, nft: 0.1"));
    let result = from_mal_spec(&path);
    assert!(
        result.is_err(),
        "expected invalid tp/fp rate labels to be rejected"
    );
}
