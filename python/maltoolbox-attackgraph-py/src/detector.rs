//! Mirrors `maltoolbox/attackgraph/detector.py`'s `Detector`. Unlike
//! every other wrapper in this layer, `Detector` is a real, freely
//! constructible value type (`#[new]`) - confirmed necessary (not a
//! freeform-construction hazard like Phase 1/2's gaps) because it only
//! ever wraps a reference to an *existing* `AttackGraphNode` handle, it
//! never needs detached/self-contained construction. See
//! PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 3 decision 1.

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
    /// Per Phase 4 decision 1, this is the real, owner-cached
    /// `Py<PyAttackGraphNode>` object (not a detached copy of the
    /// handle's own data) - `.node` returns the identical Python object
    /// every time, same as every other path to the same node.
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
        // Route through the node's own owner cache, so a `Detector`
        // built directly from Python (e.g. mal-simulator's own tests)
        // still ends up holding the canonical cached node object, not a
        // detached copy - matching Phase 4 decision 1 for every path.
        // Requires an `Owned` node (a `Detector` always references a real
        // node in a real graph) - a `Detached` node here is a clear
        // programming error, not a supported path.
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

    /// Matches the core's own simplified node-detector serialization
    /// (`node_to_dict`'s detector branch in
    /// `crates/maltoolbox-attackgraph/src/graph.rs`), not Python's own
    /// `Detector.to_dict()` - which embeds the live `node`/
    /// `potential_context` object references directly and is not
    /// actually JSON-serializable (confirmed in `PORTING_NOTES.md`).
    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let dict: Value = json!({ "name": self.name, "tprate": self.tprate });
        pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self, py: Python<'_>) -> String {
        format!("Detector(name: {:?}, node: {})", self.name, self.node.borrow(py).full_name_or_fallback(py))
    }

    /// Mirrors the real runtime effect of Python's frozen-dataclass
    /// auto-generated `__hash__` here: `potential_context` is a `dict`,
    /// which is unhashable, so `hash(a_real_detector)` already raises
    /// `TypeError` there too - not a divergence, just a different
    /// mechanism producing the same outcome.
    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Detector'"))
    }

    /// Confirmed necessary by direct testing (not assumed): without this,
    /// `pickle.dumps(a_detector)` raises `TypeError: cannot pickle` -
    /// `PyDetector` has a `#[new]` but it requires mandatory arguments, so
    /// pickle's default `copyreg.__newobj__` protocol (which calls
    /// `cls.__new__(cls)` with none) can't construct one. Unlike the
    /// container types (`LanguageGraph`/`Model`/`AttackGraph`, which lack
    /// a usable `#[new]` entirely and need a dedicated
    /// `_from_pickle_state` staticmethod target), `Detector`'s own class
    /// *is* directly callable with exactly these positional args, so no
    /// extra indirection is needed here - the nested `node` field pickles
    /// via its own `__reduce__` automatically when this tuple is pickled.
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
