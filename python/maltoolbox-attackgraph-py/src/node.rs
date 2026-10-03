//! Mirrors `maltoolbox/attackgraph/node.py`'s `AttackGraphNode`. A
//! handle - per Phase 3 decision 3, holds `owner_py: Py<PyAttackGraph>`
//! (not a bare `Rc<RefCell<AttackGraph>>`), resolving the core's
//! `AttackGraphNodeId` slotmap key from the stable, Python-facing `i64`
//! id on every access, same "no cache" discipline as `PyModelAsset`.
//! Also hosts `PyAttackGraphNodesView`, the Phase 3 decision 2 lazy
//! read-only Mapping-protocol wrapper for `PyAttackGraph.nodes`.

use pyo3::basic::CompareOp;
use pyo3::exceptions::{PyKeyError, PyLookupError, PyNotImplementedError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySet};
use pyo3::IntoPyObjectExt;

use maltoolbox_attackgraph::ids::AttackGraphNodeId;
use maltoolbox_attackgraph::AttackGraph;
use maltoolbox_language_py::handle::composite_hash;
use maltoolbox_language_py::PyLanguageGraphAttackStep;
use maltoolbox_model_py::PyModelAsset;

use crate::detector_support::{build_py_detector, detector_snapshots_for};
use crate::graph::PyAttackGraph;

#[pyclass(name = "AttackGraphNode", unsendable, skip_from_py_object)]
pub struct PyAttackGraphNode {
    pub owner_py: Py<PyAttackGraph>,
    pub id: i64,
}

impl PyAttackGraphNode {
    pub fn new(owner_py: Py<PyAttackGraph>, id: i64) -> Self {
        PyAttackGraphNode { owner_py, id }
    }

    /// `Py<PyAttackGraph>` isn't plain `Clone` (pyo3 requires a GIL token
    /// to bump its refcount safely - `clone_ref`, not `clone`), so this
    /// type can't `#[derive(Clone)]`; this is the manual equivalent.
    pub fn clone_ref(&self, py: Python<'_>) -> Self {
        PyAttackGraphNode {
            owner_py: self.owner_py.clone_ref(py),
            id: self.id,
        }
    }

    fn owner_ptr(&self, py: Python<'_>) -> usize {
        let owner = self.owner_py.borrow(py);
        std::rc::Rc::as_ptr(&owner.inner) as usize
    }

    fn not_found(&self) -> PyErr {
        PyLookupError::new_err(format!("Attack graph node with id {} not found.", self.id))
    }

    fn node_key(&self, graph: &AttackGraph) -> PyResult<AttackGraphNodeId> {
        graph.id_to_node.get(&self.id).copied().ok_or_else(|| self.not_found())
    }

    /// Borrows the owning graph transiently and runs `f` against the
    /// resolved node. No tombstone/post-removal fallback exists yet for
    /// nodes (see PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 3 status for
    /// this logged gap) - a removed node's id simply fails to resolve.
    fn with_node<R>(&self, py: Python<'_>, f: impl FnOnce(&AttackGraph, AttackGraphNodeId) -> PyResult<R>) -> PyResult<R> {
        let owner = self.owner_py.borrow(py);
        let graph = owner.inner.borrow();
        let key = self.node_key(&graph)?;
        f(&graph, key)
    }

    /// Like `with_node`, but also resolves `owner.model_py` (if any) down
    /// to a `&Model` in the same scope - needed for `full_name`/`to_dict`,
    /// which (like the core's own `full_name_of`/`to_dict`) need a model
    /// reference to resolve a node's asset-derived name.
    fn with_node_and_model<R>(
        &self,
        py: Python<'_>,
        f: impl FnOnce(&AttackGraph, AttackGraphNodeId, Option<&maltoolbox_model::Model>) -> PyResult<R>,
    ) -> PyResult<R> {
        let owner = self.owner_py.borrow(py);
        let graph = owner.inner.borrow();
        let key = self.node_key(&graph)?;
        match &owner.model_py {
            Some(m) => {
                let model_ref = m.borrow(py);
                let core_model = model_ref.inner.borrow();
                f(&graph, key, Some(&core_model))
            }
            None => f(&graph, key, None),
        }
    }

    /// Owner-ptr+id equality, usable without a pyo3 richcmp dance -
    /// shared by `PyDetector::__richcmp__` (comparing its `node` field)
    /// and this type's own `__richcmp__`/native `PartialEq`-style use.
    pub fn eq_with(&self, other: &PyAttackGraphNode, py: Python<'_>) -> bool {
        self.owner_ptr(py) == other.owner_ptr(py) && self.id == other.id
    }

    /// Best-effort `full_name`, falling back to the id if the node can no
    /// longer be resolved - used only for `__repr__`-style display (e.g.
    /// inside `PyDetector::__repr__`), never for anything that needs to be
    /// correct, just non-panicking.
    pub fn full_name_or_fallback(&self, py: Python<'_>) -> String {
        self.with_node(py, |g, k| Ok(g.full_name_of(k, None)))
            .unwrap_or_else(|_| format!("{}:<removed>", self.id))
    }
}

#[pymethods]
impl PyAttackGraphNode {
    #[getter]
    fn id(&self) -> i64 {
        self.id
    }

    #[getter]
    fn name(&self, py: Python<'_>) -> PyResult<String> {
        self.with_node(py, |g, k| Ok(g.nodes[k].name.clone()))
    }

    #[getter(r#type)]
    fn step_type(&self, py: Python<'_>) -> PyResult<&'static str> {
        self.with_node(py, |g, k| Ok(g.nodes[k].step_type.as_str()))
    }

    #[getter]
    fn lg_attack_step(&self, py: Python<'_>) -> PyResult<PyLanguageGraphAttackStep> {
        let step_id = self.with_node(py, |g, k| Ok(g.nodes[k].lg_attack_step))?;
        let lang_graph_rc = {
            let owner = self.owner_py.borrow(py);
            let rc = owner.lang_graph_py.borrow(py).inner.clone();
            rc
        };
        Ok(PyLanguageGraphAttackStep::new(lang_graph_rc, step_id))
    }

    #[getter]
    fn causal_mode(&self, py: Python<'_>) -> PyResult<Option<&'static str>> {
        self.with_node(py, |g, k| Ok(g.nodes[k].causal_mode.map(|m| m.as_str())))
    }

    #[getter]
    fn ttc<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.with_node(py, |g, k| match &g.nodes[k].ttc {
            Some(v) => pythonize::pythonize(py, v).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string())),
            None => Ok(py.None().into_bound(py)),
        })
    }

    #[getter]
    fn tags(&self, py: Python<'_>) -> PyResult<Vec<String>> {
        self.with_node(py, |g, k| Ok(g.nodes[k].tags.clone()))
    }

    /// Matches the Python original exactly for the common (empty) case -
    /// `None` when there are no model effects. When non-empty, raises
    /// `NotImplementedError`: exposing these faithfully needs a multi-class
    /// wrapper hierarchy over `LanguageGraphModelEffect`/`AssocTraversalChain`
    /// (nested traversal/set/glob elements, each potentially resolving a
    /// `LanguageGraphAsset`) that nothing in the mal-simulator acceptance
    /// surface touches - confirmed by grep - though `tests/attackgraph/
    /// test_attackgraph.py::test_create_dynamic_ag` *does* exercise this on
    /// the (untouched, still pure-Python) oracle. Logged as an open gap,
    /// not silently dropped - see PYTHON_BINDINGS_IMPLEMENTATION.md's
    /// Phase 3 status.
    #[getter]
    fn additive_model_effects(&self, py: Python<'_>) -> PyResult<Option<Py<PyAny>>> {
        self.with_node(py, |g, k| match &g.nodes[k].additive_model_effects {
            None => Ok(None),
            Some(_) => Err(PyNotImplementedError::new_err(
                "additive_model_effects is not yet implemented for non-empty effects in the native bindings",
            )),
        })
    }

    #[getter]
    fn subtractive_model_effects(&self, py: Python<'_>) -> PyResult<Option<Py<PyAny>>> {
        self.with_node(py, |g, k| match &g.nodes[k].subtractive_model_effects {
            None => Ok(None),
            Some(_) => Err(PyNotImplementedError::new_err(
                "subtractive_model_effects is not yet implemented for non-empty effects in the native bindings",
            )),
        })
    }

    #[getter]
    fn model_asset(&self, py: Python<'_>) -> PyResult<Option<PyModelAsset>> {
        let asset_id = self.with_node(py, |g, k| Ok(g.nodes[k].model_asset))?;
        let Some(asset_id) = asset_id else { return Ok(None) };
        let owner = self.owner_py.borrow(py);
        let Some(model_py) = owner.model_py.as_ref() else { return Ok(None) };
        let model = model_py.borrow(py);
        let asset = PyModelAsset::new(
            model.inner.clone(),
            asset_id,
            model.lang_graph_py.borrow(py).inner.clone(),
            model.tombstones.clone(),
        );
        Ok(Some(asset))
    }

    #[getter]
    fn existence_status(&self, py: Python<'_>) -> PyResult<Option<bool>> {
        self.with_node(py, |g, k| Ok(g.nodes[k].existence_status))
    }

    #[getter]
    fn children<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PySet>> {
        let ids: Vec<i64> = self.with_node(py, |g, k| {
            Ok(g.nodes[k].children.iter().map(|&c| g.nodes[c].id).collect())
        })?;
        let set = PySet::empty(py)?;
        for id in ids {
            set.add(PyAttackGraphNode::new(self.owner_py.clone_ref(py), id))?;
        }
        Ok(set)
    }

    #[getter]
    fn parents<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PySet>> {
        let ids: Vec<i64> = self.with_node(py, |g, k| {
            Ok(g.nodes[k].parents.iter().map(|&p| g.nodes[p].id).collect())
        })?;
        let set = PySet::empty(py)?;
        for id in ids {
            set.add(PyAttackGraphNode::new(self.owner_py.clone_ref(py), id))?;
        }
        Ok(set)
    }

    #[getter]
    fn extras<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.with_node(py, |g, k| {
            pythonize::pythonize(py, &serde_json::Value::Object(g.nodes[k].extras.clone()))
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
        })
    }

    /// Live, mutable per-node dict (Phase 3 decision 1): lazily seeded
    /// from the core's generation-time detector data on first access,
    /// then the same `Py<PyDict>` object is returned every subsequent
    /// access, so external `node.detectors['x'] = Detector(...)`
    /// mutation is visible to later reads - matching confirmed real
    /// mal-simulator usage (`test_logger_attacks_false_negative`).
    #[getter]
    fn detectors(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let owner = self.owner_py.borrow(py);
        {
            let table = owner.node_detectors.borrow();
            if let Some(existing) = table.get(&self.id) {
                return Ok(existing.clone_ref(py));
            }
        }
        let snapshot = self.with_node(py, |g, k| Ok(detector_snapshots_for(g, &[k])))?;
        let dict = PyDict::new(py);
        for snap in &snapshot {
            let det = build_py_detector(py, &self.owner_py, snap)?;
            dict.set_item(&snap.label, det)?;
        }
        owner.node_detectors.borrow_mut().insert(self.id, dict.clone().unbind());
        Ok(dict.unbind())
    }

    #[getter]
    fn full_name(&self, py: Python<'_>) -> PyResult<String> {
        self.with_node_and_model(py, |g, k, model| Ok(g.full_name_of(k, model)))
    }

    #[getter]
    fn info<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let step_id = self.with_node(py, |g, k| Ok(g.nodes[k].lg_attack_step))?;
        let lang_graph = {
            let owner = self.owner_py.borrow(py);
            let rc = owner.lang_graph_py.borrow(py).inner.clone();
            rc
        };
        let graph = lang_graph.borrow();
        let dict = PyDict::new(py);
        for (k, v) in &graph.step(step_id).info {
            dict.set_item(k, v)?;
        }
        Ok(dict)
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let dict = self.with_node_and_model(py, |g, k, model| Ok(g.node_to_dict(k, model)))?;
        pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        self.with_node_and_model(py, |g, k, model| {
            let node = &g.nodes[k];
            Ok(format!(
                "AttackGraphNode(name: \"{}\", id: {}, type: {})",
                g.full_name_of(k, model),
                node.id,
                node.step_type.as_str()
            ))
        })
    }

    fn __hash__(&self, py: Python<'_>) -> isize {
        composite_hash(self.owner_ptr(py), self.id)
    }

    fn __richcmp__(&self, other: &PyAttackGraphNode, op: CompareOp, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let eq = self.eq_with(other, py);
        match op {
            CompareOp::Eq => eq.into_py_any(py),
            CompareOp::Ne => (!eq).into_py_any(py),
            _ => Ok(py.NotImplemented()),
        }
    }

    /// Phase 3 decision 4: delegate to `(owner_py, id)` rather than
    /// snapshotting this node's own data - correct *and* simpler, since
    /// `owner_py` is a real, identity-stable object that pickle's own
    /// protocol memoizes automatically within one combined pickle call
    /// (e.g. the same graph reachable both directly and via one of its
    /// nodes).
    #[allow(clippy::type_complexity)]
    fn __reduce__(&self, py: Python<'_>) -> PyResult<(Py<PyAny>, (Py<PyAttackGraph>, i64))> {
        // Looked up by the real, eventual import path
        // (`maltoolbox._native`, already valid today too - see Phase
        // 0/1's `.so`-copy workaround) rather than hardcoding a
        // `Py<PyFunction>` reference, so this survives the Phase 5
        // packaging fix the same way the exception `__module__` strings
        // were already set up to.
        let func = py.import("maltoolbox._native")?.getattr("_rebuild_attack_graph_node")?.unbind();
        Ok((func, (self.owner_py.clone_ref(py), self.id)))
    }
}

/// Phase 3 decision 2: a small, read-only, lazy Mapping-protocol wrapper
/// for `PyAttackGraph.nodes` / (reused for) `.full_name_to_node`'s value
/// side - constructs a `PyAttackGraphNode` handle only for key(s) actually
/// touched, never materializing the whole collection upfront. Not part of
/// the public API surface (never `m.add_class`'d) - only ever handed out
/// by `PyAttackGraph.nodes`.
#[pyclass(name = "AttackGraphNodesView", unsendable)]
pub struct PyAttackGraphNodesView {
    pub owner_py: Py<PyAttackGraph>,
}

impl PyAttackGraphNodesView {
    fn ids(&self, py: Python<'_>) -> Vec<i64> {
        self.owner_py.borrow(py).inner.borrow().id_to_node.keys().copied().collect()
    }
}

#[pymethods]
impl PyAttackGraphNodesView {
    fn __getitem__(&self, py: Python<'_>, id: i64) -> PyResult<PyAttackGraphNode> {
        let present = self.owner_py.borrow(py).inner.borrow().id_to_node.contains_key(&id);
        if present {
            Ok(PyAttackGraphNode::new(self.owner_py.clone_ref(py), id))
        } else {
            Err(PyKeyError::new_err(id))
        }
    }

    fn __len__(&self, py: Python<'_>) -> usize {
        self.owner_py.borrow(py).inner.borrow().id_to_node.len()
    }

    fn __contains__(&self, py: Python<'_>, id: i64) -> bool {
        self.owner_py.borrow(py).inner.borrow().id_to_node.contains_key(&id)
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let ids = self.ids(py);
        let list = PyList::new(py, ids)?;
        Ok(list.try_iter()?.into_any())
    }

    fn keys(&self, py: Python<'_>) -> Vec<i64> {
        self.ids(py)
    }

    fn values(&self, py: Python<'_>) -> Vec<PyAttackGraphNode> {
        self.ids(py)
            .into_iter()
            .map(|id| PyAttackGraphNode::new(self.owner_py.clone_ref(py), id))
            .collect()
    }

    fn items(&self, py: Python<'_>) -> Vec<(i64, PyAttackGraphNode)> {
        self.ids(py)
            .into_iter()
            .map(|id| (id, PyAttackGraphNode::new(self.owner_py.clone_ref(py), id)))
            .collect()
    }

    #[pyo3(signature = (id, default=None))]
    fn get(&self, py: Python<'_>, id: i64, default: Option<Py<PyAny>>) -> PyResult<Option<Py<PyAny>>> {
        let present = self.owner_py.borrow(py).inner.borrow().id_to_node.contains_key(&id);
        if present {
            Ok(Some(PyAttackGraphNode::new(self.owner_py.clone_ref(py), id).into_py_any(py)?))
        } else {
            Ok(default)
        }
    }
}

/// Rebuilds a node handle from a pickled `(owner, id)` pair - the
/// `__reduce__` target for `PyAttackGraphNode`. A plain function
/// (registered in `lib.rs`), not a method, since `__reduce__`'s callable
/// must be importable by name for pickle to locate it.
#[pyfunction]
pub fn _rebuild_attack_graph_node(owner: Py<PyAttackGraph>, id: i64) -> PyAttackGraphNode {
    PyAttackGraphNode::new(owner, id)
}
