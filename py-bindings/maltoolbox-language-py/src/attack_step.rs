//! Mirrors `maltoolbox/language/language_graph_attack_step.py`'s
//! `LanguageGraphAttackStep`. A handle (`owner` + `AttackStepId`), cached
//! per-owner (`caches.steps`) so repeated lookups for the same id return
//! the identical Python object; see `handle.rs`.

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
use crate::detector::detector_to_py;
use crate::exceptions::graph_error_to_py;
use crate::expr_chain::expr_chain_to_py;
use crate::handle::{cached_handle, composite_hash, SharedLangGraphCaches};
use crate::model_effect::{model_effect_to_py, PyLanguageGraphModelEffect};

#[pyclass(name = "LanguageGraphAttackStep", unsendable, skip_from_py_object)]
#[derive(Clone)]
pub struct PyLanguageGraphAttackStep {
    pub owner: Rc<RefCell<LanguageGraph>>,
    pub id: AttackStepId,
    pub caches: SharedLangGraphCaches,
}

impl PyLanguageGraphAttackStep {
    pub fn new(
        owner: Rc<RefCell<LanguageGraph>>,
        id: AttackStepId,
        caches: SharedLangGraphCaches,
    ) -> Self {
        PyLanguageGraphAttackStep { owner, id, caches }
    }

    fn owner_ptr(&self) -> usize {
        Rc::as_ptr(&self.owner) as usize
    }

    fn step_handle(
        &self,
        py: Python<'_>,
        id: AttackStepId,
    ) -> PyResult<Py<PyLanguageGraphAttackStep>> {
        let owner = self.owner.clone();
        let caches = self.caches.clone();
        cached_handle(&self.caches.steps, py, id, move || {
            PyLanguageGraphAttackStep::new(owner, id, caches)
        })
    }

    fn asset_handle(
        &self,
        py: Python<'_>,
        id: maltoolbox_language::graph::ids::AssetId,
    ) -> PyResult<Py<PyLanguageGraphAsset>> {
        let owner = self.owner.clone();
        let caches = self.caches.clone();
        cached_handle(&self.caches.assets, py, id, move || {
            PyLanguageGraphAsset::new(owner, id, caches)
        })
    }

    /// Builds a `list[ExpressionsChain | None]` of real wrapper objects,
    /// since callers access attributes like `.right_link.fieldname`/
    /// `.fieldname` directly on them rather than a pythonized dict form.
    fn chains_to_pylist<'py>(
        &self,
        py: Python<'py>,
        chains: &[Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>],
    ) -> PyResult<Bound<'py, PyList>> {
        let mut items: Vec<Py<PyAny>> = Vec::new();
        for chain in chains {
            let item = match chain {
                Some(c) => {
                    expr_chain_to_py(py, self.owner.clone(), self.caches.clone(), c)?.into_any()
                }
                None => py.None(),
            };
            items.push(item);
        }
        PyList::new(py, items)
    }

    fn step_map_to_pydict<'py>(
        &self,
        py: Python<'py>,
        _graph: &LanguageGraph,
        map: &indexmap::IndexMap<
            AttackStepId,
            Vec<Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>>,
        >,
    ) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        for (step_id, chains) in map {
            let handle = self.step_handle(py, *step_id)?;
            let list = self.chains_to_pylist(py, chains)?;
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
    fn asset(&self, py: Python<'_>) -> PyResult<Py<PyLanguageGraphAsset>> {
        let asset_id = self.owner.borrow().step(self.id).asset;
        self.asset_handle(py, asset_id)
    }

    #[getter]
    fn causal_mode(&self) -> Option<&'static str> {
        self.owner
            .borrow()
            .step(self.id)
            .causal_mode
            .map(|m| m.as_str())
    }

    #[getter]
    fn ttc<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.owner.borrow();
        match &graph.step(self.id).ttc {
            Some(v) => pythonize::pythonize(py, v).map_err(|e| {
                graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(
                    e.to_string(),
                ))
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
    fn inherits(&self, py: Python<'_>) -> PyResult<Option<Py<PyLanguageGraphAttackStep>>> {
        let inherits_id = self.owner.borrow().step(self.id).inherits;
        inherits_id.map(|id| self.step_handle(py, id)).transpose()
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
        self.chains_to_pylist(py, &wrapped)
    }

    /// Own + inherited requirements.
    #[getter]
    fn requires<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let graph = self.owner.borrow();
        let reqs = graph.step(self.id).requires(&graph);
        let wrapped: Vec<Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>> =
            reqs.into_iter().map(Some).collect();
        self.chains_to_pylist(py, &wrapped)
    }

    /// `own_*` is the step's own (non-inherited) list of model effects;
    /// the non-`own_` getters add inherited effects, mirroring the
    /// core's own `additive_model_effects(&graph)`/
    /// `subtractive_model_effects(&graph)`.
    #[getter]
    fn own_additive_model_effects(
        &self,
        py: Python<'_>,
    ) -> PyResult<Vec<Py<PyLanguageGraphModelEffect>>> {
        let graph = self.owner.borrow();
        graph
            .step(self.id)
            .own_additive_model_effects
            .iter()
            .map(|e| model_effect_to_py(py, self.owner.clone(), self.caches.clone(), e))
            .collect()
    }

    #[getter]
    fn own_subtractive_model_effects(
        &self,
        py: Python<'_>,
    ) -> PyResult<Vec<Py<PyLanguageGraphModelEffect>>> {
        let graph = self.owner.borrow();
        graph
            .step(self.id)
            .own_subtractive_model_effects
            .iter()
            .map(|e| model_effect_to_py(py, self.owner.clone(), self.caches.clone(), e))
            .collect()
    }

    #[getter]
    fn additive_model_effects(
        &self,
        py: Python<'_>,
    ) -> PyResult<Vec<Py<PyLanguageGraphModelEffect>>> {
        let graph = self.owner.borrow();
        graph
            .step(self.id)
            .additive_model_effects(&graph)
            .iter()
            .map(|e| model_effect_to_py(py, self.owner.clone(), self.caches.clone(), e))
            .collect()
    }

    #[getter]
    fn subtractive_model_effects(
        &self,
        py: Python<'_>,
    ) -> PyResult<Vec<Py<PyLanguageGraphModelEffect>>> {
        let graph = self.owner.borrow();
        graph
            .step(self.id)
            .subtractive_model_effects(&graph)
            .iter()
            .map(|e| model_effect_to_py(py, self.owner.clone(), self.caches.clone(), e))
            .collect()
    }

    #[getter]
    fn full_name(&self) -> String {
        let graph = self.owner.borrow();
        graph.step(self.id).full_name(&graph)
    }

    /// `{name: LanguageGraphDetector}`, matching the Python original's
    /// `detectors: dict[str, LanguageGraphDetector]` field shape.
    #[getter]
    fn detectors<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (name, det) in &graph.step(self.id).detectors {
            dict.set_item(
                name,
                detector_to_py(py, self.owner.clone(), self.caches.clone(), det)?,
            )?;
        }
        Ok(dict)
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.owner.borrow();
        let dict = graph
            .step(self.id)
            .to_dict(&graph)
            .map_err(graph_error_to_py)?;
        pythonize::pythonize(py, &dict).map_err(|e| {
            graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(
                e.to_string(),
            ))
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

    /// Pickles as `(owner, asset_name, step_name)`, where `owner` is a
    /// fresh temporary `PyLanguageGraph` (see
    /// `PyLanguageGraphAsset::__reduce__`). Unlike assets, attack steps
    /// are resolved by name rather than by raw slotmap ffi id: step
    /// insertion order (and hence ffi id) differs between
    /// `generate_graph`'s two-pass construction (own steps for all
    /// assets, then synthesized inherited copies) and
    /// `language_graph_from_dict`'s one-shot-per-asset construction, even
    /// though both produce the same logical graph. Resolving by name
    /// sidesteps that discrepancy.
    #[allow(clippy::type_complexity)]
    fn __reduce__(
        &self,
        py: Python<'_>,
    ) -> PyResult<(
        Py<PyAny>,
        (Py<crate::language_graph::PyLanguageGraph>, String, String),
    )> {
        let temp_owner = Py::new(
            py,
            crate::language_graph::PyLanguageGraph {
                inner: self.owner.clone(),
                caches: self.caches.clone(),
            },
        )?;
        let graph = self.owner.borrow();
        let step = graph.step(self.id);
        let asset_name = graph.asset(step.asset).name.clone();
        let step_name = step.name.clone();
        drop(graph);
        let func = py
            .import("maltoolbox._native")?
            .getattr("_rebuild_language_graph_attack_step")?
            .unbind();
        Ok((func, (temp_owner, asset_name, step_name)))
    }
}

/// Rebuilds a `PyLanguageGraphAttackStep` handle from a pickled
/// `(owner, asset_name, step_name)` triple - the `__reduce__` target; see
/// `PyLanguageGraphAttackStep::__reduce__` for why this resolves by name
/// instead of by raw ffi id.
#[pyfunction]
pub fn _rebuild_language_graph_attack_step(
    py: Python<'_>,
    owner: Py<crate::language_graph::PyLanguageGraph>,
    asset_name: String,
    step_name: String,
) -> PyResult<Py<PyLanguageGraphAttackStep>> {
    let graph = owner.borrow(py);
    let id = {
        let inner = graph.inner.borrow();
        let asset_id = inner.asset_id(&asset_name).ok_or_else(|| {
            graph_error_to_py(maltoolbox_language::graph::GraphError::Lookup(format!(
                "Unknown asset type \"{asset_name}\" while unpickling attack step"
            )))
        })?;
        inner
            .asset(asset_id)
            .attack_steps
            .get(&step_name)
            .copied()
            .ok_or_else(|| {
                graph_error_to_py(maltoolbox_language::graph::GraphError::Lookup(format!(
                "Unknown attack step \"{step_name}\" on asset \"{asset_name}\" while unpickling"
            )))
            })?
    };
    graph.step_handle(py, id)
}
