//! PyO3 compatibility layer mirroring `maltoolbox/model.py`'s public
//! surface (`Model`, `ModelAsset`) on top of the pure-Rust
//! `maltoolbox-model` crate. See
//! `python/maltoolbox-language-py/src/lib.rs`'s module doc for the
//! shared conventions this follows, and
//! `PYTHON_BINDINGS_IMPLEMENTATION.md` for the plan/status.

mod asset;
mod exceptions;
mod model;

use pyo3::prelude::*;

pub use asset::PyModelAsset;
pub use model::PyModel;

/// Registers this layer's classes/exceptions onto the umbrella
/// `_native` module. Called from `maltoolbox-pyo3`'s `#[pymodule]`.
pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyModel>()?;
    m.add_class::<PyModelAsset>()?;
    exceptions::register(py, m)?;
    Ok(())
}
