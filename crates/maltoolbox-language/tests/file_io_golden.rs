//! Exercises the file-loading paths (`from_mar_archive`,
//! `language_graph_from_dict` round-trip) against real fixtures.

use maltoolbox_language::{
    from_mar_archive, generate_graph, language_graph_from_dict, language_graph_to_dict,
};
use serde_json::Value;
use std::path::Path;

fn fixture_path(name: &str) -> std::path::PathBuf {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures")).join(name)
}

/// Loading a real-world language (coreLang, 19 assets) from its `.mar`
/// archive must match the Python oracle's `language_graph_to_dict`
/// output exactly - a much larger, real-world cross-check than the
/// hand-picked synthetic .mal fixtures used elsewhere.
#[test]
fn mar_archive_matches_python_oracle_for_corelang() {
    let graph = from_mar_archive(fixture_path("org.mal-lang.coreLang-1.0.0.mar")).expect("load .mar");
    let actual = language_graph_to_dict(&graph).expect("to_dict");

    let golden_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/golden_graph_mar/coreLang.json");
    let expected: Value = serde_json::from_str(&std::fs::read_to_string(golden_path).unwrap()).unwrap();

    assert_eq!(actual, expected);
}

/// Serializing a built graph and deserializing it back via
/// `language_graph_from_dict` must reproduce the same `to_dict` output -
/// exercises the from_dict path (used by `load_from_file` for
/// already-compiled .json/.yaml language graph files) independently of
/// any Python oracle, since it's a self-consistency property.
#[test]
fn round_trips_through_to_dict_and_from_dict() {
    let spec = maltoolbox_language::compile_file(
        Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/wiperLang.mal")),
    )
    .expect("compile");
    let graph = generate_graph(spec).expect("build graph");
    let dict = language_graph_to_dict(&graph).expect("to_dict");

    let reloaded = language_graph_from_dict(&dict).expect("from_dict");
    let reloaded_dict = language_graph_to_dict(&reloaded).expect("to_dict again");

    assert_eq!(dict, reloaded_dict);
}

/// Same round-trip property, over coreLang, for extra confidence on a
/// much larger and more structurally varied graph (deep inheritance,
/// many associations, detectors).
#[test]
fn round_trips_corelang_through_to_dict_and_from_dict() {
    let graph = from_mar_archive(fixture_path("org.mal-lang.coreLang-1.0.0.mar")).expect("load .mar");
    let dict = language_graph_to_dict(&graph).expect("to_dict");

    let reloaded = language_graph_from_dict(&dict).expect("from_dict");
    let reloaded_dict = language_graph_to_dict(&reloaded).expect("to_dict again");

    assert_eq!(dict, reloaded_dict);
}
