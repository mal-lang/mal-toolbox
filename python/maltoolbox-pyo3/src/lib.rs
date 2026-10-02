//! Umbrella crate: assembles each layer's compat crate
//! (`maltoolbox-language-py`, and `maltoolbox-model-py`/
//! `maltoolbox-attackgraph-py` once they land) into the single
//! importable native extension module, `maltoolbox._native`. See
//! PYTHON_BINDINGS_IMPLEMENTATION.md at the repo root.
//!
//! This is the only crate in `python/` that enables pyo3's
//! `extension-module` feature - the layer crates stay plain `rlib`s so
//! they (and their tests) link against libpython normally.

use pyo3::prelude::*;

#[pymodule]
fn _native(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    maltoolbox_language_py::register(py, m)?;
    maltoolbox_model_py::register(py, m)?;
    Ok(())
}
