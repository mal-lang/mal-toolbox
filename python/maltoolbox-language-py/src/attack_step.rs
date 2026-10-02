//! Mirrors `maltoolbox/language/language_graph_attack_step.py`'s
//! `LanguageGraphAttackStep`. A handle (`owner` + `AttackStepId`), not a
//! cache - see `handle.rs` / PYTHON_BINDINGS_IMPLEMENTATION.md.

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::basic::CompareOp;
use pyo3::exceptions::PyNotImplementedError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3::IntoPyObjectExt;

use maltoolbox_language::graph::ids::AttackStepId;
use maltoolbox_language::graph::LanguageGraph;

use crate::asset::PyLanguageGraphAsset;
use crate::exceptions::graph_error_to_py;
use crate::handle::composite_hash;

#[pyclass(name = "LanguageGraphAttackStep", unsendable, skip_from_py_object)]
#[derive(Clone)]
pub struct PyLanguageGraphAttackStep {
    pub owner: Rc<RefCell<LanguageGraph>>,
    pub id: AttackStepId,
}

impl PyLanguageGraphAttackStep {
    pub fn new(owner: Rc<RefCell<LanguageGraph>>, id: AttackStepId) -> Self {
        PyLanguageGraphAttackStep { owner, id }
    }

    fn owner_ptr(&self) -> usize {
        Rc::as_ptr(&self.owner) as usize
    }

    /// Pythonizes a `Vec<Option<ExpressionsChain>>` (an `own_children`/
    /// `own_parents` value) into `list[dict | None]`. The chains
    /// themselves are exposed via their serialized `to_dict()` form, not
    /// a live `ExpressionsChain` wrapper object - see
    /// PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 1 status for why.
    fn chains_to_pylist<'py>(
        py: Python<'py>,
        graph: &LanguageGraph,
        chains: &[Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>],
    ) -> PyResult<Bound<'py, PyList>> {
        let mut items = Vec::new();
        for chain in chains {
            let value = match chain {
                Some(c) => c.to_dict(graph).map_err(graph_error_to_py)?,
                None => serde_json::Value::Null,
            };
            items.push(pythonize::pythonize(py, &value).map_err(|e| {
                graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(e.to_string()))
            })?);
        }
        PyList::new(py, items)
    }

    fn step_map_to_pydict<'py>(
        &self,
        py: Python<'py>,
        graph: &LanguageGraph,
        map: &std::collections::HashMap<
            AttackStepId,
            Vec<Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>>,
        >,
    ) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        for (step_id, chains) in map {
            let handle = PyLanguageGraphAttackStep::new(self.owner.clone(), *step_id);
            let list = Self::chains_to_pylist(py, graph, chains)?;
            dict.set_item(handle, list)?;
        }
        Ok(dict)
    }
}

#[pymethods]
impl PyLanguageGraphAttackStep {
    #[getter]
    fn name(&self) -> String {
        self.owner.borrow().step(self.id).name.clone()
    }

    #[getter(r#type)]
    fn step_type(&self) -> &'static str {
        self.owner.borrow().step(self.id).step_type.as_str()
    }

    #[getter]
    fn asset(&self) -> PyLanguageGraphAsset {
        let asset_id = self.owner.borrow().step(self.id).asset;
        PyLanguageGraphAsset::new(self.owner.clone(), asset_id)
    }

    #[getter]
    fn causal_mode(&self) -> Option<&'static str> {
        self.owner.borrow().step(self.id).causal_mode.map(|m| m.as_str())
    }

    #[getter]
    fn ttc<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.owner.borrow();
        match &graph.step(self.id).ttc {
            Some(v) => pythonize::pythonize(py, v).map_err(|e| {
                graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(e.to_string()))
            }),
            None => Ok(py.None().into_bound(py)),
        }
    }

    #[getter]
    fn overrides(&self) -> bool {
        self.owner.borrow().step(self.id).overrides
    }

    #[getter]
    fn info<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (k, v) in &graph.step(self.id).info {
            dict.set_item(k, v)?;
        }
        Ok(dict)
    }

    #[getter]
    fn tags(&self) -> Vec<String> {
        self.owner.borrow().step(self.id).tags.clone()
    }

    #[getter]
    fn inherits(&self) -> Option<PyLanguageGraphAttackStep> {
        let graph = self.owner.borrow();
        graph
            .step(self.id)
            .inherits
            .map(|id| PyLanguageGraphAttackStep::new(self.owner.clone(), id))
    }

    #[getter]
    fn own_children<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        self.step_map_to_pydict(py, &graph, &graph.step(self.id).own_children)
    }

    #[getter]
    fn own_parents<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        self.step_map_to_pydict(py, &graph, &graph.step(self.id).own_parents)
    }

    /// Own + inherited children.
    #[getter]
    fn children<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let all = graph.step(self.id).children(&graph);
        self.step_map_to_pydict(py, &graph, &all)
    }

    /// Matches the Python original exactly: fetching `.parents` always
    /// raises - it was never implemented there either.
    #[getter]
    fn parents(&self) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(
            "Fetching parents is not supported.",
        ))
    }

    #[getter]
    fn own_requires<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let graph = self.owner.borrow();
        let reqs = &graph.step(self.id).own_requires;
        let wrapped: Vec<Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>> =
            reqs.iter().cloned().map(Some).collect();
        Self::chains_to_pylist(py, &graph, &wrapped)
    }

    /// Own + inherited requirements.
    #[getter]
    fn requires<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let graph = self.owner.borrow();
        let reqs = graph.step(self.id).requires(&graph);
        let wrapped: Vec<Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>> =
            reqs.into_iter().map(Some).collect();
        Self::chains_to_pylist(py, &graph, &wrapped)
    }

    #[getter]
    fn full_name(&self) -> String {
        let graph = self.owner.borrow();
        graph.step(self.id).full_name(&graph)
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.owner.borrow();
        let dict = graph.step(self.id).to_dict(&graph).map_err(graph_error_to_py)?;
        pythonize::pythonize(py, &dict).map_err(|e| {
            graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(e.to_string()))
        })
    }

    pub fn __repr__(&self) -> String {
        format!(
            "LanguageGraphAttackStep(name: \"{}\", type: \"{}\")",
            self.name(),
            self.step_type()
        )
    }

    fn __hash__(&self) -> isize {
        composite_hash(self.owner_ptr(), self.id)
    }

    fn __richcmp__(
        &self,
        other: &PyLanguageGraphAttackStep,
        op: CompareOp,
        py: Python<'_>,
    ) -> PyResult<Py<PyAny>> {
        let eq = self.owner_ptr() == other.owner_ptr() && self.id == other.id;
        match op {
            CompareOp::Eq => eq.into_py_any(py),
            CompareOp::Ne => (!eq).into_py_any(py),
            _ => Ok(py.NotImplemented()),
        }
    }
}
