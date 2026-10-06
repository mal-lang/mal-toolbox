//! Port of `tests/language/test_compiler.py`.
//!
//! `test_compiler_non_existing_step` is ported in `test_semantic.rs`
//! (`reaches_to_nonexisting_step_rejected`) alongside the rest of the
//! semantic-analyzer test suite, now that `mal_analyzer.py` is ported
//! (see `src/compiler/semantic.rs`).
//!
//! `test_compile_wiperlang`'s model-effect assertions are ported as
//! `compile_wiperlang_model_effects`, and `test_compile_multiplicity_lang`
//! as `compile_multiplicity_lang`, now that model effects
//! (`append_reaches`/`remove_reaches`, `src/graph/model_effect.rs`) are
//! ported. Everything else here is a pure parser/langgraph-level check.

use std::path::Path;

use maltoolbox_language::{compile_file, from_mal_spec};

fn fixtures_dir() -> &'static Path {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures"))
}

fn compile_lang(dir: &Path, src: &str) -> Result<serde_json::Value, String> {
    let path = dir.join("test.mal");
    std::fs::write(&path, src).unwrap();
    compile_file(&path).map_err(|e| e.to_string())
}

fn tmp_dir(tag: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "maltoolbox-compiler-test-{tag}-{}",
        std::process::id()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

#[test]
fn illegal_asset_names_are_rejected() {
    for asset_id in ["asset-name", "asset.name", "asset name", "asset$"] {
        let dir = tmp_dir(&format!(
            "illegal-{}",
            asset_id.replace([' ', '.', '$'], "_")
        ));
        let lang = format!(
            "#id: \"test-lang\"\n#version: \"0.0.0\"\n\ncategory TestCategory {{\n    asset {asset_id} {{\n        | step1\n    }}\n}}\n"
        );
        let result = compile_lang(&dir, &lang);
        assert!(
            result.is_err(),
            "expected '{asset_id}' to be rejected, got {result:?}"
        );
        std::fs::remove_dir_all(&dir).ok();
    }
}

#[test]
fn valid_asset_name_control() {
    let dir = tmp_dir("valid");
    let lang = r#"
    #id: "test-lang"
    #version: "0.0.0"

    category TestCategory {
        asset Valid_Asset {
            | step1
        }
    }
    "#;
    compile_lang(&dir, lang).expect("valid asset name should compile");
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn compile_actions_effects() {
    let lang_graph =
        from_mal_spec(fixtures_dir().join("actions_effects_lang.mal")).expect("compile");

    let asset_a = lang_graph.asset_id("AssetA").expect("AssetA");
    let attack_step_id = lang_graph.asset(asset_a).attack_steps["attack"];
    assert_eq!(
        lang_graph.step(attack_step_id).causal_mode,
        Some(maltoolbox_language::graph::attack_step::CausalMode::Action)
    );

    let asset_b = lang_graph.asset_id("AssetB").expect("AssetB");
    let hack_id = lang_graph.asset(asset_b).attack_steps["hack"];
    assert_eq!(
        lang_graph.step(hack_id).causal_mode,
        Some(maltoolbox_language::graph::attack_step::CausalMode::Effect)
    );
    let attack_id = lang_graph.asset(asset_b).attack_steps["attack"];
    assert_eq!(
        lang_graph.step(attack_id).causal_mode,
        Some(maltoolbox_language::graph::attack_step::CausalMode::Action)
    );
    let test_id = lang_graph.asset(asset_b).attack_steps["test"];
    assert_eq!(lang_graph.step(test_id).causal_mode, None);
}

/// Port of `test_compile_wiperlang`, limited to the parts that don't
/// depend on model effects (see module docs): the raw langspec shape for
/// `reaches`, and the resulting language graph's `own_children`/
/// `own_parents` links (including through inheritance).
#[test]
fn compile_wiperlang_reaches_and_children() {
    let spec = compile_file(fixtures_dir().join("wiperLang.mal")).expect("compile");

    let assets = spec["assets"].as_array().unwrap();
    let device_asset = assets
        .iter()
        .find(|a| a["name"] == "Device")
        .expect("Device asset");
    let infect_step = device_asset["attackSteps"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["name"] == "infect")
        .expect("infect step");

    assert_eq!(
        infect_step["reaches"]["stepExpressions"][0]["lhs"]["name"],
        "malware"
    );
    assert_eq!(
        infect_step["reaches"]["stepExpressions"][0]["rhs"]["name"],
        "activate"
    );

    let lang_graph = maltoolbox_language::generate_graph(spec).expect("build graph");

    let device = lang_graph.asset_id("Device").expect("Device");
    let wiper = lang_graph.asset_id("Wiper").expect("Wiper");

    let wiper_activate = lang_graph.asset(wiper).attack_steps["activate"];
    let wiper_exfiltrate = lang_graph.asset(wiper).attack_steps["exfiltrate"];
    let wiper_propagate = lang_graph.asset(wiper).attack_steps["propagate"];
    assert!(lang_graph
        .step(wiper_activate)
        .own_children
        .contains_key(&wiper_exfiltrate));
    assert!(lang_graph
        .step(wiper_activate)
        .own_children
        .contains_key(&wiper_propagate));

    // Wiper's `activate` overrides Malware's and inherits from it; Malware's
    // own `activate` still links to `trigger` and is itself a child of
    // Device:infect (the "malware" field resolves to the declared asset
    // type Malware, not the Wiper subtype, since "infect"'s reaches has no
    // subtype filter - unlike "propagate", which explicitly filters to
    // `malware[Wiper]` and so links to Wiper:activate specifically).
    let malware = lang_graph
        .asset(wiper)
        .own_super_asset
        .expect("Wiper extends Malware");
    let malware_activate = lang_graph.asset(malware).attack_steps["activate"];
    let malware_trigger = lang_graph.asset(malware).attack_steps["trigger"];
    assert_eq!(
        lang_graph.step(wiper_activate).inherits,
        Some(malware_activate)
    );
    assert!(lang_graph
        .step(malware_activate)
        .own_children
        .contains_key(&malware_trigger));

    let device_infect = lang_graph.asset(device).attack_steps["infect"];
    assert!(lang_graph
        .step(device_infect)
        .own_children
        .contains_key(&malware_activate));
    assert!(lang_graph
        .step(malware_activate)
        .own_parents
        .contains_key(&device_infect));
    assert!(lang_graph
        .step(wiper_activate)
        .own_parents
        .contains_key(&wiper_propagate));
}

/// Port of `test_compile_wiperlang`'s model-effect assertions.
#[test]
fn compile_wiperlang_model_effects() {
    use maltoolbox_language::graph::model_effect::AssocTraversalElem;

    let lang_graph =
        maltoolbox_language::from_mal_spec(fixtures_dir().join("wiperLang.mal")).expect("compile");

    let device = lang_graph.asset_id("Device").expect("Device");
    let wiper = lang_graph.asset_id("Wiper").expect("Wiper");

    let device_infect = lang_graph.asset(device).attack_steps["infect"];
    let device_infect_effects = lang_graph
        .step(device_infect)
        .own_additive_model_effects
        .clone();
    match &device_infect_effects[0].base[0] {
        AssocTraversalElem::Traversal(t) => assert_eq!(t.field_name, "self"),
        other => panic!("expected a plain traversal, got {other:?}"),
    }
    let target = &device_infect_effects[0].targets[0];
    assert!(!target.assoc_op);
    match &target.assoc_traversal[0] {
        AssocTraversalElem::Traversal(t) => {
            assert_eq!(t.field_name, "malware");
            assert_eq!(t.asset_filter, Some(wiper));
        }
        other => panic!("expected a plain traversal, got {other:?}"),
    }

    let wiper_exfiltrate = lang_graph.asset(wiper).attack_steps["exfiltrate"];
    let wiper_exfiltrate_effects = lang_graph
        .step(wiper_exfiltrate)
        .own_additive_model_effects
        .clone();
    let effect = &wiper_exfiltrate_effects[0];
    match &effect.base[0] {
        AssocTraversalElem::Traversal(t) => assert_eq!(t.field_name, "victim"),
        other => panic!("expected a plain traversal, got {other:?}"),
    }
    match &effect.base[1] {
        AssocTraversalElem::Traversal(t) => assert_eq!(t.field_name, "data"),
        other => panic!("expected a plain traversal, got {other:?}"),
    }

    let target = &effect.targets[0];
    assert!(target.assoc_op);
    let c2server = lang_graph.asset_id("C2Server").expect("C2Server");
    let expect_field =
        |elem: &AssocTraversalElem,
         expected_name: &str,
         expected_filter: Option<maltoolbox_language::graph::AssetId>| {
            match elem {
                AssocTraversalElem::Traversal(t) => {
                    assert_eq!(t.field_name, expected_name);
                    assert_eq!(t.asset_filter, expected_filter);
                }
                other => panic!("expected a plain traversal, got {other:?}"),
            }
        };
    expect_field(&target.assoc_traversal[0], "victim", None);
    expect_field(&target.assoc_traversal[1], "inet", None);
    expect_field(&target.assoc_traversal[2], "hosts", Some(c2server));
    expect_field(&target.assoc_traversal[3], "data", None);
}

/// Port of `test_compile_multiplicity_lang`.
#[test]
fn compile_multiplicity_lang() {
    use maltoolbox_language::graph::model_effect::{AssocTraversalElem, QuantityFilter};

    let lang_graph =
        maltoolbox_language::from_mal_spec(fixtures_dir().join("multiplicity_lang.mal"))
            .expect("compile");

    let host = lang_graph.asset_id("Host").expect("Host");
    let create_random_files = lang_graph.asset(host).attack_steps["createRandomFiles"];
    let effects = lang_graph
        .step(create_random_files)
        .additive_model_effects(&lang_graph);
    match effects[0].targets[0]
        .assoc_traversal
        .last()
        .expect("non-empty traversal")
    {
        AssocTraversalElem::Traversal(t) => {
            assert_eq!(t.quantity_filter, Some(QuantityFilter::Range(4, 10)))
        }
        other => panic!("expected a plain traversal, got {other:?}"),
    }

    // `createFile`'s `A> onHost / files, self / ~(openFiles - onHost.procs.openFiles):1`
    // is two comma-separated dyn_sentences (hence two separate model
    // effects, not two targets on one effect). The second's target is
    // `~(...)：1`: `~` is the assoc_op marker (not a transitive `*`), so
    // the multiplicity lands on the outermost difference (`AssocSet`),
    // the last element of the traversal chain either way.
    let proc = lang_graph.asset_id("Proc").expect("Proc");
    let create_file = lang_graph.asset(proc).attack_steps["createFile"];
    let effects = lang_graph
        .step(create_file)
        .additive_model_effects(&lang_graph);
    assert!(effects[1].targets[0].assoc_op);
    match effects[1].targets[0]
        .assoc_traversal
        .last()
        .expect("non-empty traversal")
    {
        AssocTraversalElem::Set(s) => assert_eq!(s.quantity_filter, Some(QuantityFilter::Exact(1))),
        other => panic!("expected a set traversal, got {other:?}"),
    }
}

#[test]
fn compile_basic_dynamal_languages() {
    compile_all_in_dir("dynamal_test_langs/basic");
}

#[test]
fn compile_intermediate_dynamal_languages() {
    compile_all_in_dir("dynamal_test_langs/intermediate");
}

#[test]
fn compile_advanced_dynamal_languages() {
    compile_all_in_dir("dynamal_test_langs/advanced");
}

fn compile_all_in_dir(rel: &str) {
    let dir = fixtures_dir().join(rel);
    let mut count = 0;
    for entry in std::fs::read_dir(&dir).unwrap_or_else(|e| panic!("reading {dir:?}: {e}")) {
        let path = entry.unwrap().path();
        if path.extension().and_then(|e| e.to_str()) != Some("mal") {
            continue;
        }
        from_mal_spec(&path).unwrap_or_else(|e| panic!("failed to compile {path:?}: {e}"));
        count += 1;
    }
    assert!(count > 0, "expected at least one .mal file in {dir:?}");
}
