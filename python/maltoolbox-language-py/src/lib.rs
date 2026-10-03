//! PyO3 compatibility layer mirroring `maltoolbox/language/`'s public
//! surface (class names, method names/signatures, exception hierarchy)
//! on top of the pure-Rust `maltoolbox-language` crate.
//!
//! This is a *faithfulness* layer, not a natural Rust API: see
//! `PYTHON_BINDINGS_IMPLEMENTATION.md` at the repo root for the overall
//! plan, status, and the reasoning behind choices like `Rc<RefCell<_>>`
//! containers and on-demand (uncached) child handles.

mod asset;
mod assoc;
mod attack_step;
mod detector;
pub mod exceptions;
pub mod expr_chain;
pub mod handle;
mod language_graph;
pub mod model_effect;

use pyo3::prelude::*;

pub use asset::PyLanguageGraphAsset;
pub use assoc::{PyLanguageGraphAssociation, PyLanguageGraphAssociationField};
pub use attack_step::PyLanguageGraphAttackStep;
pub use detector::{detector_to_py, PyLanguageGraphContextItem, PyLanguageGraphDetector};
pub use expr_chain::{expr_chain_to_py, PyExpressionsChain};
pub use language_graph::PyLanguageGraph;
pub use model_effect::{
    model_effect_to_py, PyAssocSet, PyAssocTraversal, PyDynTarget, PyGlobAssocTraversal, PyLanguageGraphModelEffect,
};

/// Registers this layer's classes/exceptions onto the umbrella
/// `_native` module, including the nested `language.compiler.exceptions`/
/// `language.compiler.mal_analyzer` submodules (so Phase 4's eventual
/// re-export shims can present them at the same import path Python code
/// uses today: `maltoolbox.language.compiler.exceptions.MalCompilerError`,
/// `maltoolbox.language.compiler.mal_analyzer.malAnalyzerException`).
/// Called from `maltoolbox-pyo3`'s `#[pymodule]`.
pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyLanguageGraph>()?;
    m.add_class::<PyLanguageGraphAsset>()?;
    m.add_class::<PyLanguageGraphAttackStep>()?;
    m.add_class::<PyLanguageGraphAssociation>()?;
    m.add_class::<PyLanguageGraphAssociationField>()?;
    m.add_class::<PyAssocTraversal>()?;
    m.add_class::<PyGlobAssocTraversal>()?;
    m.add_class::<PyAssocSet>()?;
    m.add_class::<PyDynTarget>()?;
    m.add_class::<PyLanguageGraphModelEffect>()?;
    m.add_class::<PyExpressionsChain>()?;
    m.add_class::<PyLanguageGraphDetector>()?;
    m.add_class::<PyLanguageGraphContextItem>()?;
    m.add_function(wrap_pyfunction!(asset::_rebuild_language_graph_asset, m)?)?;
    m.add_function(wrap_pyfunction!(attack_step::_rebuild_language_graph_attack_step, m)?)?;
    exceptions::register(py, m)?;

    let sys_modules = py.import("sys")?.getattr("modules")?;

    let language_mod = PyModule::new(py, "language")?;
    m.add_submodule(&language_mod)?;
    sys_modules.set_item("maltoolbox._native.language", &language_mod)?;

    let compiler_mod = PyModule::new(py, "compiler")?;
    language_mod.add_submodule(&compiler_mod)?;
    sys_modules.set_item("maltoolbox._native.language.compiler", &compiler_mod)?;

    let compiler_exceptions_mod = PyModule::new(py, "exceptions")?;
    exceptions::register_compiler_exceptions(py, &compiler_exceptions_mod)?;
    compiler_mod.add_submodule(&compiler_exceptions_mod)?;
    sys_modules.set_item(
        "maltoolbox._native.language.compiler.exceptions",
        &compiler_exceptions_mod,
    )?;

    let mal_analyzer_mod = PyModule::new(py, "mal_analyzer")?;
    exceptions::register_analyzer_exceptions(py, &mal_analyzer_mod)?;
    compiler_mod.add_submodule(&mal_analyzer_mod)?;
    sys_modules.set_item(
        "maltoolbox._native.language.compiler.mal_analyzer",
        &mal_analyzer_mod,
    )?;

    Ok(())
}
