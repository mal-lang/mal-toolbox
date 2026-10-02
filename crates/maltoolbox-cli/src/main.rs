//! Port of `maltoolbox/__main__.py`, minus the subcommands excluded
//! from this rewrite's scope:
//!
//! - `upgrade-model`: depends on `translators.updater`, out of scope.
//! - `visualize-model`: entirely visualization-dependent, out of scope.
//! - `generate-attack-graph`'s `--graphviz`/`--neo4j` flags: same.
//!
//! `generate-attack-graph` also takes an explicit `<output_file>`
//! argument here, where the Python original instead wrote to a
//! `maltoolbox.yml`-configured debug path (defaulting to
//! `logs/attackgraph.yml`) as a side effect - that config/logging
//! subsystem isn't ported (see `maltoolbox_attackgraph::factories`),
//! so an explicit argument is the straightforward replacement for an
//! otherwise-silent command.

use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "maltoolbox", version, about = "Command-line interface for MAL toolbox operations")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Compile a MAL language spec (.mal or .mar) and write the result to `output_file` (.json/.yml/.yaml).
    Compile {
        lang_file: PathBuf,
        output_file: PathBuf,
    },
    /// Generate an attack graph from `model_file` and `lang_file`, and write it to `output_file` (.json/.yml/.yaml).
    GenerateAttackGraph {
        model_file: PathBuf,
        lang_file: PathBuf,
        output_file: PathBuf,
    },
}

fn compile(lang_file: &std::path::Path, output_file: &std::path::Path) -> Result<(), String> {
    let lang_graph =
        maltoolbox_language::load_language_graph_from_file(lang_file).map_err(|e| e.to_string())?;
    maltoolbox_language::save_language_graph_to_file(&lang_graph, output_file)
        .map_err(|e| e.to_string())
}

fn generate_attack_graph(
    model_file: &std::path::Path,
    lang_file: &std::path::Path,
    output_file: &std::path::Path,
) -> Result<(), String> {
    let (attack_graph, model) = maltoolbox_attackgraph::create_attack_graph(lang_file, model_file)
        .map_err(|e| e.to_string())?;
    attack_graph
        .save_to_file(Some(&model), output_file)
        .map_err(|e| e.to_string())
}

fn main() -> ExitCode {
    let cli = Cli::parse();

    let result = match &cli.command {
        Command::Compile { lang_file, output_file } => compile(lang_file, output_file),
        Command::GenerateAttackGraph {
            model_file,
            lang_file,
            output_file,
        } => generate_attack_graph(model_file, lang_file, output_file),
    };

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("Error: {e}");
            ExitCode::FAILURE
        }
    }
}
