//! Diffs the Rust compiler's output against golden JSON produced by the
//! real Python mal-toolbox compiler (see tests/golden/*.json), for every
//! .mal fixture that compiles standalone.

use maltoolbox_language::compile_file;
use std::fs;
use std::path::Path;

fn fixtures_dir() -> &'static Path {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures"))
}

fn golden_dir() -> &'static Path {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/golden"))
}

#[test]
fn matches_python_oracle_for_all_fixtures() {
    let mut stems: Vec<String> = fs::read_dir(golden_dir())
        .expect("golden dir should exist")
        .filter_map(|entry| entry.ok())
        .filter_map(|entry| {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("json") {
                path.file_stem().map(|s| s.to_string_lossy().into_owned())
            } else {
                None
            }
        })
        .collect();
    stems.sort();
    assert!(!stems.is_empty(), "expected at least one golden fixture");

    let mut failures = Vec::new();

    for stem in &stems {
        let mal_path = fixtures_dir().join(format!("{stem}.mal"));
        let golden_path = golden_dir().join(format!("{stem}.json"));

        let expected: serde_json::Value =
            serde_json::from_str(&fs::read_to_string(&golden_path).unwrap()).unwrap();

        match compile_file(&mal_path) {
            Ok(actual) => {
                if actual != expected {
                    failures.push(format!(
                        "{stem}: mismatch\n--- expected ---\n{}\n--- actual ---\n{}",
                        serde_json::to_string_pretty(&expected).unwrap(),
                        serde_json::to_string_pretty(&actual).unwrap(),
                    ));
                }
            }
            Err(e) => failures.push(format!("{stem}: compile error: {e}")),
        }
    }

    assert!(
        failures.is_empty(),
        "{} of {} fixtures failed:\n\n{}",
        failures.len(),
        stems.len(),
        failures.join("\n\n")
    );
}
