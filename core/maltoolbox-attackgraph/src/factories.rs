//! Port of `maltoolbox/attackgraph/factories.py`.
//!
//! The Python original's `maltoolbox.yml`-driven debug dumps of the
//! loaded langspec/langgraph/model are not ported; that config/logging
//! subsystem has no equivalent here.

use std::path::Path;
use std::rc::Rc;

use maltoolbox_model::Model;

use crate::{AttackGraph, GraphError};

#[derive(Debug, thiserror::Error)]
pub enum FactoryError {
    #[error("{0}")]
    LanguageLoad(#[from] maltoolbox_language::LanguageLoadError),
    #[error("{0}")]
    ModelLoad(#[from] maltoolbox_model::LoadError),
    #[error("{0}")]
    Graph(#[from] GraphError),
}

/// Build an [`AttackGraph`] from a language file path (`.mar` or `.mal`,
/// trying `.mar` first and falling back to `.mal` on failure) and a model
/// file path.
///
/// Returns the loaded [`Model`] alongside the graph, since callers need
/// it for anything that resolves node names from model assets, e.g.
/// `AttackGraph::to_dict`/`save_to_file`.
pub fn create_attack_graph(
    lang_path: impl AsRef<Path>,
    model_path: impl AsRef<Path>,
) -> Result<(AttackGraph, Model), FactoryError> {
    let lang_path = lang_path.as_ref();
    let lang_graph = match maltoolbox_language::from_mar_archive(lang_path) {
        Ok(graph) => graph,
        Err(_) => maltoolbox_language::from_mal_spec(lang_path)?,
    };
    let lang_graph = Rc::new(lang_graph);

    let model = maltoolbox_model::load_from_file(model_path, lang_graph)?;
    let attack_graph = AttackGraph::from_model(&model)?;

    Ok((attack_graph, model))
}
