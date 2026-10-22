//! Umbrella crate: assembles each layer's compat crate
//! (`maltoolbox-language-py`, `maltoolbox-model-py`,
//! `maltoolbox-attackgraph-py`) into the single importable native
//! extension module, `maltoolbox._native`.
//!
//! This is the only crate in `py-bindings/` that enables pyo3's
//! `extension-module` feature - the layer crates stay plain `rlib`s so
//! they (and their tests) link against libpython normally.

use pyo3::prelude::*;

#[pymodule]
fn _native(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    maltoolbox_language_py::register(py, m)?;
    maltoolbox_model_py::register(py, m)?;
    maltoolbox_attackgraph_py::register(py, m)?;
    Ok(())
}
