//! Port of `tests/language/test_detectors.py` (language-only subset).
//!
//! Whole-stack detector tests that build a `Model`/`AttackGraph` on top of
//! the compiled language moved to `maltoolbox-attackgraph`'s test suite, so
//! this crate doesn't need dev-dependencies on its own downstream crates.

use maltoolbox_language::from_mal_spec;

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
