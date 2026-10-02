//! Tests for the semantic analyzer (port of `mal_analyzer.py`,
//! `crates/maltoolbox-language/src/compiler/semantic.rs`).
//!
//! Every negative case below was checked against the real Python
//! mal-toolbox oracle (`MalCompiler().compile(...)`) before being ported:
//! each snippet does raise a `malAnalyzerException` (or, for
//! `distributions`, a `DistributionsException`) there too, with an
//! equivalent error condition - exact diagnostic text isn't part of the
//! wire-compatibility contract this project maintains, so only pass/fail
//! is asserted here, not message content.
//!
//! One deliberate divergence, also oracle-confirmed: a two-file mutual
//! `include` cycle does *not* raise in Python, because `mal_compiler.py`'s
//! own `visited_files` dedup short-circuits the repeat include before the
//! analyzer's cycle-tracking logic ever runs - see the comment on
//! `compiler::mod::compile_inner`. Ported as observed, so no test asserts
//! an error for that case.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use maltoolbox_language::compile_file;

static COUNTER: AtomicU64 = AtomicU64::new(0);

fn tmp_dir(tag: &str) -> PathBuf {
    let unique = COUNTER.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!(
        "maltoolbox-semantic-test-{tag}-{}-{unique}",
        std::process::id()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

fn compile_src(tag: &str, src: &str) -> Result<serde_json::Value, String> {
    let dir = tmp_dir(tag);
    let path = dir.join("test.mal");
    std::fs::write(&path, src).unwrap();
    let result = compile_file(&path).map_err(|e| e.to_string());
    std::fs::remove_dir_all(&dir).ok();
    result
}

fn assert_rejected(tag: &str, src: &str) {
    let result = compile_src(tag, src);
    assert!(result.is_err(), "expected '{tag}' to be rejected, got {result:?}");
}

const HEADER: &str = "#id: \"test-lang\"\n#version: \"0.0.0\"\n\n";

#[test]
fn missing_id_define_rejected() {
    assert_rejected(
        "missing_id",
        "#version: \"0.0.0\"\n\ncategory C { asset A { | s1 } }",
    );
}

#[test]
fn missing_version_define_rejected() {
    assert_rejected(
        "missing_version",
        "#id: \"x\"\n\ncategory C { asset A { | s1 } }",
    );
}

#[test]
fn malformed_version_rejected() {
    assert_rejected(
        "bad_version",
        "#id: \"x\"\n#version: \"abc\"\n\ncategory C { asset A { | s1 } }",
    );
}

#[test]
fn extends_undefined_asset_rejected() {
    assert_rejected(
        "extends_undefined",
        &format!("{HEADER}category C {{ asset A extends B {{ | s1 }} }}"),
    );
}

#[test]
fn circular_extends_rejected() {
    assert_rejected(
        "circular_extends",
        &format!(
            "{HEADER}category C {{ asset A extends B {{ | s1 }} asset B extends A {{ | s2 }} }}"
        ),
    );
}

#[test]
fn duplicate_asset_name_rejected() {
    assert_rejected(
        "dup_asset",
        &format!("{HEADER}category C {{ asset A {{ | s1 }} asset A {{ | s2 }} }}"),
    );
}

#[test]
fn duplicate_meta_key_rejected() {
    assert_rejected(
        "dup_meta",
        &format!(
            "{HEADER}category C {{ asset A meta info: \"x\" meta info: \"y\" {{ | s1 }} }}"
        ),
    );
}

#[test]
fn duplicate_custom_define_rejected() {
    assert_rejected(
        "dup_define",
        "#id: \"x\"\n#version: \"0.0.0\"\n#author: \"a\"\n#author: \"b\"\n\ncategory C { asset A { | s1 } }",
    );
}

#[test]
fn duplicate_attack_step_name_rejected() {
    assert_rejected(
        "dup_step",
        &format!("{HEADER}category C {{ asset A {{ | s1 | s1 }} }}"),
    );
}

#[test]
fn duplicate_variable_name_rejected() {
    assert_rejected(
        "dup_var",
        &format!("{HEADER}category C {{ asset A {{ let x = (A) | s1 let x = (A) }} }}"),
    );
}

#[test]
fn variable_redefinition_across_hierarchy_rejected() {
    assert_rejected(
        "var_redef_hierarchy",
        &format!(
            "{HEADER}category C {{ \
                asset Z {{ | zs }} \
                asset A {{ let x = (zfield) | s1 }} \
                asset B extends A {{ let x = (zfield) | s2 }} \
            }}\nassociations {{ A [afield] 1 <-- R1 --> 1 [zfield] Z }}"
        ),
    );
}

#[test]
fn association_to_undefined_asset_rejected() {
    assert_rejected(
        "assoc_undefined_asset",
        &format!(
            "{HEADER}category C {{ asset A {{ | s1 }} }}\nassociations {{ A [left] 1 <-- R --> 1 [right] B }}"
        ),
    );
}

#[test]
fn field_colliding_with_attack_step_rejected() {
    assert_rejected(
        "field_collides_step",
        &format!(
            "{HEADER}category C {{ asset A {{ | right }} asset B {{ | s1 }} }}\nassociations {{ A [left] 1 <-- R --> 1 [right] B }}"
        ),
    );
}

#[test]
fn append_reaches_without_base_rejected() {
    assert_rejected(
        "append_without_base",
        &format!("{HEADER}category C {{ asset A {{ | s1 +> s2 }} }}"),
    );
}

#[test]
fn attack_step_override_type_mismatch_rejected() {
    assert_rejected(
        "override_type_mismatch",
        &format!("{HEADER}category C {{ asset A {{ | s1 }} asset B extends A {{ & s1 }} }}"),
    );
}

/// Port of `test_compiler_non_existing_step` (`tests/language/
/// test_compiler.py`), previously un-ported because it depends on this
/// analyzer.
#[test]
fn reaches_to_nonexisting_step_rejected() {
    assert_rejected(
        "reaches_nonexisting_step",
        &format!("{HEADER}category C {{ asset A {{ | s1 -> nonExisting }} }}"),
    );
}

#[test]
fn cia_on_defense_step_rejected() {
    assert_rejected(
        "cia_on_defense",
        &format!("{HEADER}category C {{ asset A {{ # s1 {{C}} }} }}"),
    );
}

#[test]
fn defense_with_disallowed_ttc_rejected() {
    assert_rejected(
        "defense_bad_ttc",
        &format!("{HEADER}category C {{ asset A {{ # s1 [Exponential(1.0)] }} }}"),
    );
}

#[test]
fn enabled_distribution_on_and_step_rejected() {
    assert_rejected(
        "enabled_on_and",
        &format!("{HEADER}category C {{ asset A {{ & s1 [Enabled] }} }}"),
    );
}

#[test]
fn bernoulli_in_subtraction_rejected() {
    assert_rejected(
        "bernoulli_in_subtraction",
        &format!("{HEADER}category C {{ asset A {{ & s1 [1.0 - Bernoulli(0.5)] }} }}"),
    );
}

#[test]
fn invalid_distribution_parameters_rejected() {
    // Bernoulli's probability parameter must be in [0, 1] - exercises the
    // ported `distributions::validate` arity/range checks, not just the
    // analyzer's structural checks.
    assert_rejected(
        "bad_bernoulli_param",
        &format!("{HEADER}category C {{ asset A {{ & s1 [Bernoulli(2.0)] }} }}"),
    );
}

#[test]
fn requires_on_non_exist_step_rejected() {
    assert_rejected(
        "requires_on_and",
        &format!(
            "{HEADER}category C {{ asset A {{ | right\n & s1 <- right }} }}"
        ),
    );
}

#[test]
fn exist_step_without_requires_rejected() {
    assert_rejected(
        "exist_without_requires",
        &format!("{HEADER}category C {{ asset A {{ E s1 }} }}"),
    );
}

#[test]
fn variable_cycle_rejected() {
    assert_rejected(
        "var_cycle",
        &format!(
            "{HEADER}category C {{ asset A {{ let x = (y()) let y = (x()) | s1 }} }}"
        ),
    );
}

#[test]
fn variable_not_pointing_to_asset_rejected() {
    assert_rejected(
        "var_not_asset",
        &format!("{HEADER}category C {{ asset A {{ let x = (nonexistentfield) | s1 }} }}"),
    );
}

/// Intentional divergence from the Python oracle (see PORTING_NOTES.md
/// §4): `mal_compiler.py`'s own `visited_files` dedup intercepts a
/// repeated include *before* the analyzer's `_include_stack` cycle check
/// can ever see it, so a simple two-file mutual include silently
/// compiles in the real implementation. This Rust port implements real
/// cycle detection instead and rejects it.
#[test]
fn mutual_include_raises() {
    let dir = tmp_dir("include_cycle");
    let a_path = dir.join("cyc_a.mal");
    let b_path = dir.join("cyc_b.mal");
    std::fs::write(
        &a_path,
        format!("{HEADER}include \"cyc_b.mal\"\ncategory C {{ asset A {{ | s1 }} }}"),
    )
    .unwrap();
    std::fs::write(
        &b_path,
        "include \"cyc_a.mal\"\ncategory D { asset B { | s2 } }",
    )
    .unwrap();

    let result = compile_file(&a_path);
    assert!(result.is_err(), "expected mutual include to be rejected, got {result:?}");
    let message = result.unwrap_err().to_string();
    assert!(message.contains("cycle"), "expected cycle error, got {message:?}");
    std::fs::remove_dir_all(&dir).ok();
}

/// Non-cyclic repeated includes (a "diamond": both B and C include A)
/// must still compile - only an actual cycle through the active include
/// stack should be rejected.
#[test]
fn diamond_include_does_not_error() {
    let dir = tmp_dir("include_diamond");
    let root_path = dir.join("diamond_root.mal");
    let b_path = dir.join("diamond_b.mal");
    let c_path = dir.join("diamond_c.mal");
    let shared_path = dir.join("diamond_shared.mal");
    std::fs::write(
        &root_path,
        format!(
            "{HEADER}include \"diamond_b.mal\"\ninclude \"diamond_c.mal\"\ncategory C {{ asset Root {{ | s1 }} }}"
        ),
    )
    .unwrap();
    std::fs::write(
        &b_path,
        "include \"diamond_shared.mal\"\ncategory D { asset B { | s2 } }",
    )
    .unwrap();
    std::fs::write(
        &c_path,
        "include \"diamond_shared.mal\"\ncategory E { asset C { | s3 } }",
    )
    .unwrap();
    std::fs::write(&shared_path, "category F { asset Shared { | s4 } }").unwrap();

    let result = compile_file(&root_path);
    assert!(result.is_ok(), "expected diamond include to compile, got {result:?}");
    std::fs::remove_dir_all(&dir).ok();
}

fn fixtures_dir() -> &'static Path {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures"))
}

/// Every pre-existing valid fixture must still compile cleanly with the
/// analyzer wired in - a regression guard distinct from `compiler_golden`/
/// `graph_golden` (which diff output *shape*, not merely success).
#[test]
fn all_fixtures_still_compile_valid() {
    for name in [
        "actions_effects_lang.mal",
        "assocChainLang.mal",
        "association_lang.mal",
        "attackstep_inherit.mal",
        "attackstep_override.mal",
        "detector_lang.mal",
        "inherited_vars.mal",
        "interleaved_vars.mal",
        "multiplicity_lang.mal",
        "prob_dists.mal",
        "set_ops_adv.mal",
        "set_ops_collect_left.mal",
        "set_ops.mal",
        "shared_assoc_sibling.mal",
        "subtype_attack_step.mal",
        "transitive_advanced.mal",
        "transitive.mal",
        "wiperLang.mal",
    ] {
        let path = fixtures_dir().join(name);
        compile_file(&path).unwrap_or_else(|e| panic!("{name} should still compile: {e}"));
    }
}
