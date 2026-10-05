//! Shared plumbing for seeding the Phase 3 decision 1 "live, compat-layer-
//! owned" detector containers (`PyAttackGraph.detectors`,
//! `PyAttackGraphNode.detectors`) from the Rust core's generation-time
//! data - see `graph.rs`/`node.rs`'s `.detectors` getters and
//! PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 3 decision 1.
//!
//! The core's [`maltoolbox_attackgraph::Detector`] stores the *label* it
//! was generated under only as the surrounding `HashMap`'s key, and
//! identifies its own node/context via [`maltoolbox_attackgraph::ids::AttackGraphNodeId`]
//! (a slotmap key, not the stable Python-facing `i64`) - both need
//! resolving against a live `&AttackGraph` borrow. [`DetectorSnapshot`]
//! captures everything needed to build a `PyDetector` with no further
//! core-graph borrow, so seeding never needs to hold a `graph.inner`
//! borrow while also constructing Python objects (which could otherwise
//! re-borrow the same `RefCell` reentrantly).

use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PySet};

use maltoolbox_attackgraph::ids::AttackGraphNodeId;
use maltoolbox_attackgraph::AttackGraph;

use crate::detector::PyDetector;
use crate::graph::PyAttackGraph;

#[derive(Clone)]
pub struct DetectorSnapshot {
    pub label: String,
    pub node_id: i64,
    pub name: Option<String>,
    /// fieldname -> ids of the nodes it could potentially refer to.
    pub potential_context: HashMap<String, Vec<i64>>,
    pub tprate: Option<f64>,
    pub fprate: Option<f64>,
}

/// Snapshots every detector on the given nodes (identified by core
/// slotmap key) into owned, borrow-free data.
pub fn detector_snapshots_for(graph: &AttackGraph, keys: &[AttackGraphNodeId]) -> Vec<DetectorSnapshot> {
    let mut out = Vec::new();
    for &key in keys {
        let Some(node) = graph.nodes.get(key) else { continue };
        for (label, det) in &node.detectors {
            let mut potential_context = HashMap::new();
            for (fieldname, ids) in &det.potential_context {
                let resolved: Vec<i64> = ids.iter().filter_map(|&k| graph.nodes.get(k).map(|n| n.id)).collect();
                potential_context.insert(fieldname.clone(), resolved);
            }
            out.push(DetectorSnapshot {
                label: label.clone(),
                node_id: node.id,
                name: det.name.clone(),
                potential_context,
                tprate: det.tprate,
                fprate: det.fprate,
            });
        }
    }
    out
}

/// Builds a real `PyDetector` from a snapshot - safe to call with no
/// outstanding `AttackGraph` borrow.
pub fn build_py_detector(py: Python<'_>, owner_py: &Py<PyAttackGraph>, snap: &DetectorSnapshot) -> PyResult<Py<PyDetector>> {
    let graph = owner_py.borrow(py);
    let node = graph.node_handle(owner_py, py, snap.node_id)?;
    let context_dict = PyDict::new(py);
    for (fieldname, ids) in &snap.potential_context {
        let set = PySet::empty(py)?;
        for &id in ids {
            set.add(graph.node_handle(owner_py, py, id)?)?;
        }
        context_dict.set_item(fieldname, set)?;
    }
    drop(graph);
    Py::new(
        py,
        PyDetector::new(
            snap.name.clone(),
            node,
            context_dict.unbind(),
            snap.tprate,
            snap.fprate,
        ),
    )
}
