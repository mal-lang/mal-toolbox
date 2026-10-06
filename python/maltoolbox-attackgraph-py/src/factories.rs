//! Port of `maltoolbox/attackgraph/factories.py::create_attack_graph`.
//!
//! Unlike the Rust core's `maltoolbox_attackgraph::factories::create_attack_graph`
//! (path-only, returns `(AttackGraph, Model)` since the core doesn't store
//! `model` on `AttackGraph`), this mirrors Python's signature: `lang`/`model`
//! each accept either a path string or an already-loaded object, and only
//! the `AttackGraph` is returned (with `.model`/`.lang_graph` set via this
//! compat layer's own back-reference).
//!
//! The debug-dump side effects of Python's original
//! (`log_configs['langspec_file']`/etc.) are dropped - that config/logging
//! subsystem isn't ported anywhere in this project.

use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;

use maltoolbox_language_py::PyLanguageGraph;
use maltoolbox_model_py::PyModel;

use crate::graph::PyAttackGraph;

#[pyfunction]
pub fn create_attack_graph(py: Python<'_>, lang: &Bound<'_, PyAny>, model: &Bound<'_, PyAny>) -> PyResult<PyAttackGraph> {
    let lang_graph_py: Py<PyLanguageGraph> = if let Ok(lg) = lang.extract::<Py<PyLanguageGraph>>() {
        lg
    } else if let Ok(path) = lang.extract::<String>() {
        let graph = match maltoolbox_language::from_mar_archive(&path) {
            Ok(g) => g,
            Err(_) => maltoolbox_language::from_mal_spec(&path).map_err(maltoolbox_language_py::exceptions::load_error_to_py)?,
        };
        Py::new(py, PyLanguageGraph::wrap(graph))?
    } else {
        return Err(PyTypeError::new_err("`lang` must be either string or LanguageGraph"));
    };

    let model_py: Py<PyModel> = if let Ok(m) = model.extract::<Py<PyModel>>() {
        m
    } else if let Ok(path) = model.extract::<String>() {
        let loaded = PyModel::load_from_file(py, std::path::PathBuf::from(&path), lang_graph_py.clone_ref(py))?;
        Py::new(py, loaded)?
    } else {
        return Err(PyTypeError::new_err("`model` must be either string or Model"));
    };

    PyAttackGraph::new(py, Some(lang_graph_py), Some(model_py))
}
