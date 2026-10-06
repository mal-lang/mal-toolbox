//! PyO3 compatibility layer mirroring `maltoolbox/attackgraph/`'s public
//! surface (`AttackGraph`, `AttackGraphNode`, `Detector`,
//! `create_attack_graph`) on top of the pure-Rust `maltoolbox-attackgraph`
//! crate. See `python/maltoolbox-language-py/src/lib.rs`'s module doc for
//! the shared conventions this follows.

mod detector;
mod detector_support;
mod exceptions;
mod factories;
mod graph;
mod node;

use pyo3::prelude::*;

pub use detector::PyDetector;
pub use graph::PyAttackGraph;
pub use node::PyAttackGraphNode;

/// Registers this layer's classes/exceptions/functions onto the umbrella
/// `_native` module. Called from `maltoolbox-pyo3`'s `#[pymodule]`.
pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyAttackGraph>()?;
    m.add_class::<PyAttackGraphNode>()?;
    m.add_class::<PyDetector>()?;
    m.add_function(wrap_pyfunction!(node::_rebuild_attack_graph_node, m)?)?;
    m.add_function(wrap_pyfunction!(factories::create_attack_graph, m)?)?;
    exceptions::register(py, m)?;
    Ok(())
}
