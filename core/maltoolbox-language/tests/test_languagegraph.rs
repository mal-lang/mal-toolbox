//! Port of `tests/language/test_languagegraph.py`, minus:
//! - the pickle tests (no meaningful Rust equivalent to Python pickling)
//! - `test_load_from_git*` (network-dependent, `@pytest.mark.integration`
//!   in the Python original too, and `language_graph_from_git_url` is
//!   out of scope for this rewrite - see `graph::file` module docs)
//! - `test_languagegraph_save_load` (redundant with
//!   `file_io_golden.rs`'s coreLang JSON round-trip, which covers the
//!   same property)
//! - `test_mallib_mal` (disabled/commented out in the Python original
//!   too)

use std::path::Path;

use maltoolbox_language::{
    compile_file, from_mal_spec, from_mar_archive, language_graph_to_dict,
    save_language_graph_to_file, save_language_graph_to_mar_archive,
};

fn fixtures_dir() -> &'static Path {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures"))
}

fn tmp_dir(tag: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "maltoolbox-langgraph-test-{tag}-{}",
        std::process::id()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

#[test]
fn languagegraph_to_dict_detectors() {
    let graph = from_mal_spec(fixtures_dir().join("detector_lang.mal")).expect("compile");
    let dir = tmp_dir("detectors");
    save_language_graph_to_file(&graph, dir.join("detector_lang.json")).expect("save");
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn languagegraph_save_load_mar() {
    let graph =
        from_mar_archive(fixtures_dir().join("org.mal-lang.coreLang-1.0.0.mar")).expect("load");
    let dir = tmp_dir("save-load-mar");
    let path = dir.join("langgraph.mar");

    save_language_graph_to_mar_archive(&graph, &path).expect("save .mar");
    let reloaded = from_mar_archive(&path).expect("reload .mar");

    assert_eq!(
        language_graph_to_dict(&graph).unwrap(),
        language_graph_to_dict(&reloaded).unwrap()
    );
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn corelang_with_union_different_assets_same_super_asset() {
    // An attack step in IAMObject contains a union between Identity and
    // Group, which should be allowed since they share the same super asset.
    from_mar_archive(fixtures_dir().join("corelang-union-common-ancestor.mar")).expect("load");
}

#[test]
fn interleaved_vars() {
    // Two interleaved variables (A2 contains B1, B2 contains A1) must
    // resolve correctly.
    let spec = compile_file(fixtures_dir().join("interleaved_vars.mal")).expect("compile");
    let graph = maltoolbox_language::generate_graph(spec).expect("build graph");

    let asset_a = graph.asset_id("AssetA").expect("AssetA");
    let asset_b = graph.asset_id("AssetB").expect("AssetB");

    let vars_a = &graph.asset(asset_a).own_variables;
    let vars_b = &graph.asset(asset_b).own_variables;
    assert!(vars_a.contains_key("A1"));
    assert!(vars_a.contains_key("A2"));
    assert!(vars_b.contains_key("B1"));
    assert!(vars_b.contains_key("B2"));

    let (var_a2_target, var_a2_chain) = &vars_a["A2"];
    assert_eq!(*var_a2_target, asset_a);
    let right_fieldname = |chain: &maltoolbox_language::graph::ExpressionsChain| match chain {
        maltoolbox_language::graph::ExpressionsChain::Binary { right: Some(r), .. } => {
            match r.as_ref() {
                maltoolbox_language::graph::ExpressionsChain::Field { fieldname, .. } => {
                    fieldname.clone()
                }
                _ => panic!("expected right_link to be a Field chain"),
            }
        }
        _ => panic!("expected a binary chain"),
    };
    assert_eq!(right_fieldname(var_a2_chain.as_ref().unwrap()), "fieldA");

    let (var_b2_target, var_b2_chain) = &vars_b["B2"];
    assert_eq!(*var_b2_target, asset_b);
    assert_eq!(right_fieldname(var_b2_chain.as_ref().unwrap()), "fieldB");
}

#[test]
fn inherited_vars() {
    let spec = compile_file(fixtures_dir().join("inherited_vars.mal")).expect("compile");
    maltoolbox_language::generate_graph(spec).expect("build graph");
}

#[test]
fn associations() {
    let spec = compile_file(fixtures_dir().join("association_lang.mal")).expect("compile");
    let graph = maltoolbox_language::generate_graph(spec).expect("build graph");

    let mut names: std::collections::HashSet<String> = std::collections::HashSet::new();
    for &asset_id in &graph.asset_order {
        for assoc in graph.asset(asset_id).own_associations.values() {
            names.insert(assoc.name.clone());
        }
    }

    let expected: std::collections::HashSet<String> = [
        "AssocAC", "AssocAB", "AssocBC", "AssocBB", "AssocCC", "AssocCB", "AssocDC", "AssocDB",
    ]
    .into_iter()
    .map(String::from)
    .collect();
    assert_eq!(names, expected);
}

#[test]
fn attackstep_inherit() {
    let spec = compile_file(fixtures_dir().join("attackstep_inherit.mal")).expect("compile");
    let graph = maltoolbox_language::generate_graph(spec).expect("build graph");

    let bb = graph.asset_id("BB").expect("BB");
    let cc = graph.asset_id("CC").expect("CC");
    let bb_s1 = graph.asset(bb).attack_steps["s1"];
    let cc_s2 = graph.asset(cc).attack_steps["s2"];

    let children = graph.step(bb_s1).children(&graph);
    assert!(children.contains_key(&cc_s2));
    assert_eq!(graph.step(bb_s1).own_children.len(), 1);
    assert_eq!(children.len(), 1);

    let chains_to_cc_s2 = &children[&cc_s2];
    assert_eq!(chains_to_cc_s2.len(), 2);
    let fieldname_of = |chain: &Option<maltoolbox_language::graph::ExpressionsChain>| match chain {
        Some(maltoolbox_language::graph::ExpressionsChain::Field { fieldname, .. }) => {
            fieldname.clone()
        }
        other => panic!("expected a Field chain, got {other:?}"),
    };
    assert_eq!(fieldname_of(&chains_to_cc_s2[0]), "c_of_B");
    assert_eq!(fieldname_of(&chains_to_cc_s2[1]), "c_of_A");
}

#[test]
fn attackstep_override() {
    let spec = compile_file(fixtures_dir().join("attackstep_override.mal")).expect("compile");
    let graph = maltoolbox_language::generate_graph(spec).expect("build graph");

    for name in [
        "EmptyParent",
        "Child1",
        "Child2",
        "Child3",
        "Child4",
        "FinalChild",
    ] {
        assert!(graph.asset_id(name).is_some(), "missing asset {name}");
    }

    let ep = graph.asset_id("EmptyParent").unwrap();
    let c1 = graph.asset_id("Child1").unwrap();
    let c2 = graph.asset_id("Child2").unwrap();
    let c3 = graph.asset_id("Child3").unwrap();
    let c4 = graph.asset_id("Child4").unwrap();
    let fc = graph.asset_id("FinalChild").unwrap();

    let ep_target1 = graph.asset(ep).attack_steps["target1"];
    for step in ["target1", "target2", "target3", "target4"] {
        assert!(graph.asset(ep).attack_steps.contains_key(step));
    }

    for step in [
        "attack_step_with_child",
        "attackstep",
        "target1",
        "target2",
        "target3",
        "target4",
    ] {
        assert!(graph.asset(c1).attack_steps.contains_key(step));
    }
    let c1_attackstep = graph.asset(c1).attack_steps["attackstep"];
    assert!(graph.step(c1_attackstep).own_children.is_empty());
    assert!(graph.step(c1_attackstep).children(&graph).is_empty());

    // attack_step_with_child is defined in the parent with target1 as a child.
    let c1_parent_attackstep = graph.asset(c1).attack_steps["attack_step_with_child"];
    assert!(graph.step(c1_parent_attackstep).own_children.is_empty());
    assert_eq!(
        graph
            .step(c1_parent_attackstep)
            .children(&graph)
            .keys()
            .copied()
            .collect::<std::collections::HashSet<_>>(),
        std::collections::HashSet::from([ep_target1])
    );

    for step in [
        "attack_step_with_child",
        "attackstep",
        "target1",
        "target2",
        "target3",
        "target4",
    ] {
        assert!(graph.asset(c2).attack_steps.contains_key(step));
    }
    let c2_attackstep = graph.asset(c2).attack_steps["attackstep"];
    assert_eq!(graph.step(c2_attackstep).inherits, Some(c1_attackstep));
    assert!(graph.step(c2_attackstep).own_children.is_empty());

    for step in [
        "attack_step_with_child",
        "attackstep",
        "target1",
        "target2",
        "target3",
        "target4",
    ] {
        assert!(graph.asset(c3).attack_steps.contains_key(step));
    }
    let c3_attackstep = graph.asset(c3).attack_steps["attackstep"];
    assert_eq!(graph.step(c3_attackstep).inherits, Some(c2_attackstep));
    let c3_target1 = graph.asset(c3).attack_steps["target1"];
    let c3_target2 = graph.asset(c3).attack_steps["target2"];
    let c3_target3 = graph.asset(c3).attack_steps["target3"];
    let c3_target4 = graph.asset(c3).attack_steps["target4"];
    assert!(graph
        .step(c3_attackstep)
        .own_children
        .contains_key(&c3_target1));
    assert!(!graph
        .step(c3_attackstep)
        .own_children
        .contains_key(&c3_target2));
    assert!(!graph
        .step(c3_attackstep)
        .own_children
        .contains_key(&c3_target3));
    assert!(!graph
        .step(c3_attackstep)
        .own_children
        .contains_key(&c3_target4));

    for step in [
        "attack_step_with_child",
        "attackstep",
        "target1",
        "target2",
        "target3",
        "target4",
    ] {
        assert!(graph.asset(c4).attack_steps.contains_key(step));
    }
    let c4_attackstep = graph.asset(c4).attack_steps["attackstep"];
    assert_eq!(graph.step(c4_attackstep).inherits, Some(c3_attackstep));
    assert!(graph.step(c4_attackstep).own_children.is_empty());

    let fc_attackstep = graph.asset(fc).attack_steps["attackstep"];
    assert_eq!(graph.step(fc_attackstep).inherits, Some(c4_attackstep));
    let fc_target1 = graph.asset(fc).attack_steps["target1"];
    let fc_target2 = graph.asset(fc).attack_steps["target2"];
    let fc_target3 = graph.asset(fc).attack_steps["target3"];
    let fc_target4 = graph.asset(fc).attack_steps["target4"];
    for target in [fc_target1, fc_target2, fc_target3, fc_target4] {
        assert!(graph.step(fc_attackstep).own_children.contains_key(&target));
    }
}

#[test]
fn probability_distributions() {
    let spec = compile_file(fixtures_dir().join("prob_dists.mal")).expect("compile");
    let graph = maltoolbox_language::generate_graph(spec).expect("build graph");
    let dir = tmp_dir("prob-dists");
    save_language_graph_to_file(&graph, dir.join("prob_dists_lg.yml")).expect("save");
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn attack_step_types_are_valid() {
    use maltoolbox_language::graph::attack_step::AttackStepType;

    let graph =
        from_mar_archive(fixtures_dir().join("org.mal-lang.coreLang-1.0.0.mar")).expect("load");
    for &asset_id in &graph.asset_order {
        for &step_id in graph.asset(asset_id).attack_steps.values() {
            let step_type = graph.step(step_id).step_type;
            assert!(matches!(
                step_type,
                AttackStepType::Or
                    | AttackStepType::And
                    | AttackStepType::Defense
                    | AttackStepType::Exist
                    | AttackStepType::NotExist
            ));
        }
    }
}

#[test]
fn attack_graph_node_causal_mode_inheritance() {
    use maltoolbox_language::graph::attack_step::CausalMode;

    let dir = tmp_dir("causal-mode");
    let lang_path = dir.join("lang.mal");
    std::fs::write(
        &lang_path,
        r#"
    #id: "test-actions-effects"
    #version: "0.0.0"

    category Test{
        asset AssetA {
          | action attackstep1
            -> attackstep2

          | action attackstep2
        }

        asset AssetB extends AssetA {
          | effect attackstep2
        }
    }
    "#,
    )
    .unwrap();

    let spec = compile_file(&lang_path).expect("compile");
    let graph = maltoolbox_language::generate_graph(spec).expect("build graph");

    let asset_a = graph.asset_id("AssetA").unwrap();
    let asset_b = graph.asset_id("AssetB").unwrap();
    let a_step1 = graph.asset(asset_a).attack_steps["attackstep1"];
    let a_step2 = graph.asset(asset_a).attack_steps["attackstep2"];
    let b_step1 = graph.asset(asset_b).attack_steps["attackstep1"];
    let b_step2 = graph.asset(asset_b).attack_steps["attackstep2"];

    assert_eq!(graph.step(a_step1).causal_mode, Some(CausalMode::Action));
    assert_eq!(graph.step(a_step2).causal_mode, Some(CausalMode::Action));
    assert_eq!(graph.step(b_step1).causal_mode, Some(CausalMode::Action)); // inherited
    assert_eq!(graph.step(b_step2).causal_mode, Some(CausalMode::Effect)); // overridden

    std::fs::remove_dir_all(&dir).ok();
}
