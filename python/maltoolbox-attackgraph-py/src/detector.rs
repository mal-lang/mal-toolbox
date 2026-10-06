//! Mirrors `maltoolbox/attackgraph/detector.py`'s `Detector`. Unlike other
//! wrappers in this layer, `Detector` is a freely constructible value type
//! (`#[new]`), since it only ever wraps a reference to an *existing*
//! `AttackGraphNode` handle and never needs detached construction.

use pyo3::basic::CompareOp;
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::IntoPyObjectExt;

use serde_json::{json, Value};

use crate::node::PyAttackGraphNode;

#[pyclass(name = "Detector", module = "maltoolbox._native", unsendable, skip_from_py_object)]
pub struct PyDetector {
    pub name: Option<String>,
    /// The owner-cached `Py<PyAttackGraphNode>` handle, so `.node` returns
    /// the identical Python object every time.
    pub node: Py<PyAttackGraphNode>,
    pub potential_context: Py<PyDict>,
    pub tprate: Option<f64>,
    pub fprate: Option<f64>,
}

impl PyDetector {
    pub fn new(
        name: Option<String>,
        node: Py<PyAttackGraphNode>,
        potential_context: Py<PyDict>,
        tprate: Option<f64>,
        fprate: Option<f64>,
    ) -> Self {
        PyDetector {
            name,
            node,
            potential_context,
            tprate,
            fprate,
        }
    }
}

#[pymethods]
impl PyDetector {
    #[new]
    #[pyo3(signature = (name, node, potential_context, tprate=None, fprate=None))]
    fn py_new(
        py: Python<'_>,
        name: Option<String>,
        node: PyRef<'_, PyAttackGraphNode>,
        potential_context: Py<PyDict>,
        tprate: Option<f64>,
        fprate: Option<f64>,
    ) -> PyResult<Self> {
        // Route through the node's owner cache so the stored handle is the
        // canonical cached node object, not a detached copy. A `Detector`
        // always references a real node in a real graph, so a `Detached`
        // node here is a programming error.
        let (owner_py, id) = match &node.repr {
            crate::node::NodeRepr::Owned { owner_py, id } => (owner_py.clone_ref(py), *id),
            crate::node::NodeRepr::Detached(_) => {
                return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                    "Detector cannot be constructed from a detached AttackGraphNode (one with no owning AttackGraph).",
                ))
            }
        };
        drop(node);
        let graph = owner_py.borrow(py);
        let cached_node = graph.node_handle(&owner_py, py, id)?;
        drop(graph);
        Ok(PyDetector::new(name, cached_node, potential_context, tprate, fprate))
    }

    #[getter]
    fn name(&self) -> Option<String> {
        self.name.clone()
    }

    #[getter]
    fn node(&self, py: Python<'_>) -> Py<PyAttackGraphNode> {
        self.node.clone_ref(py)
    }

    #[getter]
    fn potential_context(&self, py: Python<'_>) -> Py<PyDict> {
        self.potential_context.clone_ref(py)
    }

    #[getter]
    fn tprate(&self) -> Option<f64> {
        self.tprate
    }

    #[getter]
    fn fprate(&self) -> Option<f64> {
        self.fprate
    }

    /// Matches the core's simplified node-detector serialization
    /// (`node_to_dict`'s detector branch in `graph.rs`), not Python's own
    /// `Detector.to_dict()`, which embeds live object references and
    /// isn't actually JSON-serializable.
    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let dict: Value = json!({ "name": self.name, "tprate": self.tprate });
        pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self, py: Python<'_>) -> String {
        format!("Detector(name: {:?}, node: {})", self.name, self.node.borrow(py).full_name_or_fallback(py))
    }

    /// `potential_context` is a `dict`, which is unhashable, so Python's
    /// own dataclass `__hash__` would raise the same `TypeError`.
    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Detector'"))
    }

    /// `PyDetector`'s `#[new]` requires mandatory arguments, so pickle's
    /// default `copyreg.__newobj__` protocol can't construct one without
    /// this. The class itself is directly callable with these positional
    /// args, so no `_from_pickle_state` indirection is needed; the nested
    /// `node` field pickles via its own `__reduce__`.
    #[allow(clippy::type_complexity)]
    fn __reduce__<'py>(
        &self,
        py: Python<'py>,
    ) -> PyResult<(Bound<'py, PyAny>, (Option<String>, Py<PyAttackGraphNode>, Py<PyDict>, Option<f64>, Option<f64>))> {
        let cls = py.get_type::<PyDetector>().into_any();
        Ok((
            cls,
            (
                self.name.clone(),
                self.node.clone_ref(py),
                self.potential_context.clone_ref(py),
                self.tprate,
                self.fprate,
            ),
        ))
    }

    fn __richcmp__(&self, other: &PyDetector, op: CompareOp, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let eq = match op {
            CompareOp::Eq | CompareOp::Ne => {
                let fields_eq = self.name == other.name
                    && self.node.borrow(py).eq_with(&other.node.borrow(py), py)
                    && self.tprate == other.tprate
                    && self.fprate == other.fprate;
                fields_eq
                    && self
                        .potential_context
                        .bind(py)
                        .eq(other.potential_context.bind(py))?
            }
            _ => return Ok(py.NotImplemented()),
        };
        match op {
            CompareOp::Eq => eq.into_py_any(py),
            CompareOp::Ne => (!eq).into_py_any(py),
            _ => unreachable!(),
        }
    }
}
