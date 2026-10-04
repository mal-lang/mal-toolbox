//! Mirrors `maltoolbox/attackgraph/node.py`'s `AttackGraphNode`. A
//! handle - per Phase 3 decision 3, holds `owner_py: Py<PyAttackGraph>`
//! (not a bare `Rc<RefCell<AttackGraph>>`), resolving the core's
//! `AttackGraphNodeId` slotmap key from the stable, Python-facing `i64`
//! id on every access. Cached per-owner (`PyAttackGraph::node_cache`) as
//! of Phase 4 decision 1 - repeated lookups for the same id return the
//! identical Python object; see `handle.rs`/PYTHON_BINDINGS_IMPLEMENTATION.md.
//! Also hosts `PyAttackGraphNodesView`, the Phase 3 decision 2 lazy
//! read-only Mapping-protocol wrapper for `PyAttackGraph.nodes`.

use pyo3::basic::CompareOp;
use pyo3::exceptions::{PyKeyError, PyLookupError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySet};
use pyo3::IntoPyObjectExt;

use maltoolbox_attackgraph::ids::AttackGraphNodeId;
use maltoolbox_attackgraph::AttackGraph;
use maltoolbox_language_py::handle::composite_hash;
use maltoolbox_language_py::{model_effect_to_py, PyLanguageGraphAttackStep, PyLanguageGraphModelEffect};
use maltoolbox_model_py::PyModelAsset;

use crate::detector_support::{build_py_detector, detector_snapshots_for};
use crate::graph::PyAttackGraph;

/// `children`/`parents` are `{other_node_id: other_node_full_name}` with
/// *integer* keys in the Python original (`{child.id: child.full_name
/// for child in self.children}`) - the core's `node_to_dict` can only
/// produce `serde_json::Map` (string keys only, a JSON limitation), so
/// `pythonize` hands back `{"132": "..."}` instead of `{132: "..."}`
/// unless corrected here, after pythonizing. Same pattern/root cause as
/// `maltoolbox-model-py`'s `fix_associated_assets_int_keys` - neither
/// Phase 3's own oracle diff nor its mal-simulator-pattern checks
/// happened to read `children`/`parents` by integer key directly, so
/// this wasn't caught until `tests/translators/test_networkx.py`
/// exercised it for real. Shared by `PyAttackGraphNode::to_dict` and
/// `PyAttackGraph::to_dict` (once per node either way).
pub fn fix_children_parents_int_keys(py: Python<'_>, node_dict: &Bound<'_, PyDict>) -> PyResult<()> {
    for field in ["children", "parents"] {
        let Some(value) = node_dict.get_item(field)? else {
            continue;
        };
        let Ok(sub_dict) = value.cast::<PyDict>() else {
            continue;
        };
        let fixed = PyDict::new(py);
        for (key, val) in sub_dict.iter() {
            let id: i64 = key
                .extract::<String>()?
                .parse()
                .map_err(|_| pyo3::exceptions::PyValueError::new_err(format!("non-integer key in {field}")))?;
            fixed.set_item(id, val)?;
        }
        node_dict.set_item(field, fixed)?;
    }
    Ok(())
}

/// A standalone, self-contained node built directly via
/// `AttackGraphNode(...)` from Python with no owning `AttackGraph` -
/// Phase 4 decision 8. Deliberately minimal: only what
/// `maltoolbox/patternfinder/attackgraph_patterns.py` (and its tests)
/// actually read - `.id`/`.name`/`.children`/`.parents` (get+set) plus
/// `__repr__`/default identity hash+eq. `lg_attack_step`/`model_asset`/
/// `ttc_dist`/`existence_status`/`full_name` are accepted by `__init__`
/// (matching the Python original's positional signature) but not all
/// stored - nothing in scope reads them back.
pub struct DetachedNode {
    pub id: i64,
    pub name: String,
    pub children: Py<PySet>,
    pub parents: Py<PySet>,
}

/// Either a live handle into an owning `AttackGraph` (`Owned`, the
/// pre-existing representation - see this module's top doc comment) or a
/// `Detached` standalone node with no owner, per Phase 4 decision 8.
pub enum NodeRepr {
    Owned { owner_py: Py<PyAttackGraph>, id: i64 },
    Detached(DetachedNode),
}

#[pyclass(name = "AttackGraphNode", unsendable, skip_from_py_object)]
pub struct PyAttackGraphNode {
    pub repr: NodeRepr,
}

impl PyAttackGraphNode {
    pub fn new(owner_py: Py<PyAttackGraph>, id: i64) -> Self {
        PyAttackGraphNode {
            repr: NodeRepr::Owned { owner_py, id },
        }
    }

    /// `Py<PyAttackGraph>` isn't plain `Clone` (pyo3 requires a GIL token
    /// to bump its refcount safely - `clone_ref`, not `clone`), so this
    /// type can't `#[derive(Clone)]`; this is the manual equivalent. Only
    /// meaningful for `Owned` handles (the only variant ever put in
    /// `node_cache`); panics if called on a `Detached` node, which is
    /// never cached.
    pub fn clone_ref(&self, py: Python<'_>) -> Self {
        match &self.repr {
            NodeRepr::Owned { owner_py, id } => PyAttackGraphNode {
                repr: NodeRepr::Owned {
                    owner_py: owner_py.clone_ref(py),
                    id: *id,
                },
            },
            NodeRepr::Detached(_) => unreachable!("Detached nodes are never cloned via clone_ref"),
        }
    }

    /// Unwraps the `Owned` fields, or a clear `NotImplementedError` for
    /// `Detached` - used by every method outside this minimal `Detached`
    /// scope (see this module's top doc comment / Phase 4 decision 8).
    fn owned(&self) -> PyResult<(&Py<PyAttackGraph>, i64)> {
        match &self.repr {
            NodeRepr::Owned { owner_py, id } => Ok((owner_py, *id)),
            NodeRepr::Detached(_) => Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "This operation is not supported on a detached AttackGraphNode (one constructed directly, with no owning AttackGraph).",
            )),
        }
    }

    fn owner_ptr(&self, py: Python<'_>) -> PyResult<usize> {
        let (owner_py, _) = self.owned()?;
        let owner = owner_py.borrow(py);
        Ok(std::rc::Rc::as_ptr(&owner.inner) as usize)
    }

    fn not_found(&self, id: i64) -> PyErr {
        PyLookupError::new_err(format!("Attack graph node with id {} not found.", id))
    }

    fn node_key(&self, graph: &AttackGraph, id: i64) -> PyResult<AttackGraphNodeId> {
        graph.id_to_node.get(&id).copied().ok_or_else(|| self.not_found(id))
    }

    /// Borrows the owning graph transiently and runs `f` against the
    /// resolved node. **No tombstone fallback** - a removed node's id
    /// simply fails to resolve here, unlike `with_node_value` below.
    /// This is the path for getters that ultimately need a *key* into
    /// the live graph (`full_name_of`/`node_to_dict`/
    /// `detector_snapshots_for` all take an `AttackGraphNodeId`, not an
    /// owned node value) or that cross-reference *other* nodes
    /// (`children`/`parents`) - extending the tombstone to cover these
    /// too would need further core-crate changes (those functions
    /// accepting a node value directly) not attempted in this pass. See
    /// `with_node_value` / PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 4
    /// status for the scope of what *is* tombstone-covered. `Owned`-only -
    /// see `owned()`.
    fn with_node<R>(&self, py: Python<'_>, f: impl FnOnce(&AttackGraph, AttackGraphNodeId) -> PyResult<R>) -> PyResult<R> {
        let (owner_py, id) = self.owned()?;
        let owner = owner_py.borrow(py);
        let graph = owner.inner.borrow();
        let key = self.node_key(&graph, id)?;
        f(&graph, key)
    }

    /// Like `with_node`, but resolves to the node's *own data* directly
    /// (`&AttackGraphNode`, not a graph+key pair) and **does** fall back
    /// to the owning graph's tombstone record when the live lookup
    /// misses - Phase 4 decision 4's post-removal readability fix,
    /// mirroring `PyModelAsset::with_asset`'s live-then-tombstone
    /// pattern. Used by every getter that only needs this node's own
    /// fields (not a graph-wide key lookup or cross-referencing other
    /// nodes) - see `with_node`'s doc comment for what's deliberately
    /// out of scope. `Owned`-only - see `owned()`.
    fn with_node_value<R>(&self, py: Python<'_>, f: impl FnOnce(&maltoolbox_attackgraph::AttackGraphNode) -> PyResult<R>) -> PyResult<R> {
        let (owner_py, id) = self.owned()?;
        let owner = owner_py.borrow(py);
        let graph = owner.inner.borrow();
        if let Some(&key) = graph.id_to_node.get(&id) {
            return f(&graph.nodes[key]);
        }
        drop(graph);
        let tombstones = owner.tombstones.borrow();
        if let Some(node) = tombstones.get(&id) {
            return f(node);
        }
        Err(self.not_found(id))
    }

    /// Like `with_node`, but also resolves `owner.model_py` (if any) down
    /// to a `&Model` in the same scope - needed for `full_name`/`to_dict`,
    /// which (like the core's own `full_name_of`/`to_dict`) need a model
    /// reference to resolve a node's asset-derived name. `Owned`-only -
    /// see `owned()`.
    fn with_node_and_model<R>(
        &self,
        py: Python<'_>,
        f: impl FnOnce(&AttackGraph, AttackGraphNodeId, Option<&maltoolbox_model::Model>) -> PyResult<R>,
    ) -> PyResult<R> {
        let (owner_py, id) = self.owned()?;
        let owner = owner_py.borrow(py);
        let graph = owner.inner.borrow();
        let key = self.node_key(&graph, id)?;
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
    /// `Owned`-only (both `PyDetector.node` and the historical use sites
    /// of this helper only ever hold `Owned` nodes); returns `false`
    /// rather than erroring if either side is `Detached`, since this is
    /// used for structural equality checks, not a context where raising
    /// is appropriate.
    pub fn eq_with(&self, other: &PyAttackGraphNode, py: Python<'_>) -> bool {
        match (self.owner_ptr(py), other.owner_ptr(py), self.owned(), other.owned()) {
            (Ok(a), Ok(b), Ok((_, self_id)), Ok((_, other_id))) => a == b && self_id == other_id,
            _ => false,
        }
    }

    /// Best-effort `full_name`, falling back to the id if the node can no
    /// longer be resolved - used only for `__repr__`-style display (e.g.
    /// inside `PyDetector::__repr__`), never for anything that needs to be
    /// correct, just non-panicking. Falls back the same way for
    /// `Detached` nodes (which have no `full_name` concept at all).
    pub fn full_name_or_fallback(&self, py: Python<'_>) -> String {
        match &self.repr {
            NodeRepr::Owned { id, .. } => self
                .with_node(py, |g, k| Ok(g.full_name_of(k, None)))
                .unwrap_or_else(|_| format!("{}:<removed>", id)),
            NodeRepr::Detached(d) => format!("{}:<detached>", d.id),
        }
    }

    /// Shared conversion for `additive_model_effects`/
    /// `subtractive_model_effects` (Phase 4 decision 3). `Owned`-only -
    /// see `owned()`.
    fn model_effects_to_py(
        &self,
        py: Python<'_>,
        effects: Option<Vec<maltoolbox_language::graph::model_effect::LanguageGraphModelEffect>>,
    ) -> PyResult<Option<Vec<Py<PyLanguageGraphModelEffect>>>> {
        let Some(effects) = effects else { return Ok(None) };
        let (owner_py, _) = self.owned()?;
        let owner = owner_py.borrow(py);
        let lang_graph = owner.lang_graph_py.borrow(py);
        let lang_owner = lang_graph.inner.clone();
        let lang_caches = lang_graph.caches.clone();
        effects
            .iter()
            .map(|e| model_effect_to_py(py, lang_owner.clone(), lang_caches.clone(), e))
            .collect::<PyResult<Vec<_>>>()
            .map(Some)
    }
}

#[pymethods]
impl PyAttackGraphNode {
    /// Matches the Python original's positional signature
    /// `(node_id, lg_attack_step, model_asset=None, ttc_dist=None,
    /// existence_status=None, full_name=None)`. Always builds a
    /// `Detached` node (Phase 4 decision 8) - `Owned` handles are only
    /// ever vended internally by an owning `PyAttackGraph`
    /// (`add_node`/`node_handle`/the nodes view), never constructed
    /// directly from Python.
    #[new]
    #[pyo3(signature = (node_id, lg_attack_step, model_asset=None, ttc_dist=None, existence_status=None, full_name=None))]
    #[allow(unused_variables, clippy::too_many_arguments)]
    fn py_new(
        py: Python<'_>,
        node_id: i64,
        lg_attack_step: &Bound<'_, PyAny>,
        model_asset: Option<&Bound<'_, PyAny>>,
        ttc_dist: Option<&Bound<'_, PyAny>>,
        existence_status: Option<bool>,
        full_name: Option<String>,
    ) -> PyResult<Self> {
        let name: String = lg_attack_step.getattr("name")?.extract()?;
        Ok(PyAttackGraphNode {
            repr: NodeRepr::Detached(DetachedNode {
                id: node_id,
                name,
                children: PySet::empty(py)?.unbind(),
                parents: PySet::empty(py)?.unbind(),
            }),
        })
    }

    #[getter]
    pub fn id(&self) -> i64 {
        match &self.repr {
            NodeRepr::Owned { id, .. } => *id,
            NodeRepr::Detached(d) => d.id,
        }
    }

    #[getter]
    fn name(&self, py: Python<'_>) -> PyResult<String> {
        match &self.repr {
            NodeRepr::Owned { .. } => self.with_node_value(py, |n| Ok(n.name.clone())),
            NodeRepr::Detached(d) => Ok(d.name.clone()),
        }
    }

    #[getter(r#type)]
    fn step_type(&self, py: Python<'_>) -> PyResult<&'static str> {
        self.with_node_value(py, |n| Ok(n.step_type.as_str()))
    }

    #[getter]
    fn lg_attack_step(&self, py: Python<'_>) -> PyResult<Py<PyLanguageGraphAttackStep>> {
        let step_id = self.with_node_value(py, |n| Ok(n.lg_attack_step))?;
        let (owner_py, _) = self.owned()?;
        let owner = owner_py.borrow(py);
        let lang_graph = owner.lang_graph_py.borrow(py);
        lang_graph.step_handle(py, step_id)
    }

    #[getter]
    fn causal_mode(&self, py: Python<'_>) -> PyResult<Option<&'static str>> {
        self.with_node_value(py, |n| Ok(n.causal_mode.map(|m| m.as_str())))
    }

    #[getter]
    fn ttc<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.with_node_value(py, |n| match &n.ttc {
            Some(v) => pythonize::pythonize(py, v).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string())),
            None => Ok(py.None().into_bound(py)),
        })
    }

    #[getter]
    fn tags(&self, py: Python<'_>) -> PyResult<Vec<String>> {
        self.with_node_value(py, |n| Ok(n.tags.clone()))
    }

    /// `None` when there are no model effects, else a list of
    /// `LanguageGraphModelEffect` wrappers - built for real per Phase 4
    /// decision 3 (previously raised `NotImplementedError` for the
    /// non-empty case; see `maltoolbox-language-py`'s `model_effect.rs`
    /// for the wrapper hierarchy).
    #[getter]
    fn additive_model_effects(&self, py: Python<'_>) -> PyResult<Option<Vec<Py<PyLanguageGraphModelEffect>>>> {
        let effects = self.with_node_value(py, |n| Ok(n.additive_model_effects.clone()))?;
        self.model_effects_to_py(py, effects)
    }

    #[getter]
    fn subtractive_model_effects(&self, py: Python<'_>) -> PyResult<Option<Vec<Py<PyLanguageGraphModelEffect>>>> {
        let effects = self.with_node_value(py, |n| Ok(n.subtractive_model_effects.clone()))?;
        self.model_effects_to_py(py, effects)
    }

    #[getter]
    fn model_asset(&self, py: Python<'_>) -> PyResult<Option<Py<PyModelAsset>>> {
        let asset_id = self.with_node_value(py, |n| Ok(n.model_asset))?;
        let Some(asset_id) = asset_id else { return Ok(None) };
        let (owner_py, _) = self.owned()?;
        let owner = owner_py.borrow(py);
        let Some(model_py) = owner.model_py.as_ref() else { return Ok(None) };
        let model = model_py.borrow(py);
        Ok(Some(model.asset_handle(py, asset_id)?))
    }

    #[getter]
    fn existence_status(&self, py: Python<'_>) -> PyResult<Option<bool>> {
        self.with_node_value(py, |n| Ok(n.existence_status))
    }

    /// `Owned`: derived live from the core graph on every access (as
    /// before). `Detached`: the plain mutable `Py<PySet>` set directly by
    /// Python code (`node1.children = {node2, node3}`) - see the
    /// `#[setter]` below and Phase 4 decision 8.
    #[getter]
    fn children<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PySet>> {
        match &self.repr {
            NodeRepr::Owned { owner_py, .. } => {
                let ids: Vec<i64> = self.with_node(py, |g, k| {
                    Ok(g.nodes[k].children.iter().map(|&c| g.nodes[c].id).collect())
                })?;
                let owner = owner_py.borrow(py);
                let set = PySet::empty(py)?;
                for id in ids {
                    set.add(owner.node_handle(owner_py, py, id)?)?;
                }
                Ok(set)
            }
            NodeRepr::Detached(d) => Ok(d.children.bind(py).clone()),
        }
    }

    #[setter]
    fn set_children(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        match &self.repr {
            NodeRepr::Owned { .. } => Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Setting .children directly is only supported on a detached AttackGraphNode.",
            )),
            NodeRepr::Detached(d) => {
                let set = PySet::new(py, value.try_iter()?.collect::<PyResult<Vec<_>>>()?)?;
                d.children.bind(py).clear();
                for item in set.iter() {
                    d.children.bind(py).add(item)?;
                }
                Ok(())
            }
        }
    }

    /// See `children`'s doc comment - same `Owned`/`Detached` split.
    #[getter]
    fn parents<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PySet>> {
        match &self.repr {
            NodeRepr::Owned { owner_py, .. } => {
                let ids: Vec<i64> = self.with_node(py, |g, k| {
                    Ok(g.nodes[k].parents.iter().map(|&p| g.nodes[p].id).collect())
                })?;
                let owner = owner_py.borrow(py);
                let set = PySet::empty(py)?;
                for id in ids {
                    set.add(owner.node_handle(owner_py, py, id)?)?;
                }
                Ok(set)
            }
            NodeRepr::Detached(d) => Ok(d.parents.bind(py).clone()),
        }
    }

    #[setter]
    fn set_parents(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        match &self.repr {
            NodeRepr::Owned { .. } => Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Setting .parents directly is only supported on a detached AttackGraphNode.",
            )),
            NodeRepr::Detached(d) => {
                let set = PySet::new(py, value.try_iter()?.collect::<PyResult<Vec<_>>>()?)?;
                d.parents.bind(py).clear();
                for item in set.iter() {
                    d.parents.bind(py).add(item)?;
                }
                Ok(())
            }
        }
    }

    /// Live, mutable per-node dict (same pattern as `.detectors` above,
    /// now also applied to `extras` - see `PyAttackGraph::node_extras`'s
    /// doc comment): lazily seeded from the core's `n.extras` on first
    /// access, then the same `Py<PyDict>` object is returned every
    /// subsequent access, so `node.extras['x'] = y` mutation is visible to
    /// later reads (`test_attackgraph_save_load_no_model_given`).
    #[getter]
    fn extras(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let (owner_py, id) = self.owned()?;
        let owner = owner_py.borrow(py);
        {
            let table = owner.node_extras.borrow();
            if let Some(existing) = table.get(&id) {
                return Ok(existing.clone_ref(py));
            }
        }
        let value = self.with_node_value(py, |n| Ok(serde_json::Value::Object(n.extras.clone())))?;
        let pythonized =
            pythonize::pythonize(py, &value).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let dict = pythonized.cast::<PyDict>()?;
        owner.node_extras.borrow_mut().insert(id, dict.clone().unbind());
        Ok(dict.clone().unbind())
    }

    /// Live, mutable per-node dict (Phase 3 decision 1): lazily seeded
    /// from the core's generation-time detector data on first access,
    /// then the same `Py<PyDict>` object is returned every subsequent
    /// access, so external `node.detectors['x'] = Detector(...)`
    /// mutation is visible to later reads - matching confirmed real
    /// mal-simulator usage (`test_logger_attacks_false_negative`).
    #[getter]
    fn detectors(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let (owner_py, id) = self.owned()?;
        let owner = owner_py.borrow(py);
        {
            let table = owner.node_detectors.borrow();
            if let Some(existing) = table.get(&id) {
                return Ok(existing.clone_ref(py));
            }
        }
        let snapshot = self.with_node(py, |g, k| Ok(detector_snapshots_for(g, &[k])))?;
        let dict = PyDict::new(py);
        for snap in &snapshot {
            let det = build_py_detector(py, owner_py, snap)?;
            dict.set_item(&snap.label, det)?;
        }
        owner.node_detectors.borrow_mut().insert(id, dict.clone().unbind());
        Ok(dict.unbind())
    }

    #[getter]
    fn full_name(&self, py: Python<'_>) -> PyResult<String> {
        self.with_node_and_model(py, |g, k, model| Ok(g.full_name_of(k, model)))
    }

    #[getter]
    fn info<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let step_id = self.with_node_value(py, |n| Ok(n.lg_attack_step))?;
        let (owner_py, _) = self.owned()?;
        let lang_graph = {
            let owner = owner_py.borrow(py);
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

    /// Overlays the live `node_extras` side-table entry (if seeded) onto
    /// the serialized `"extras"` field - see
    /// `PyAttackGraph::to_dict`'s doc comment for why this is needed
    /// (the core's own `node_to_dict` can't see compat-layer-side
    /// mutation of `.extras`).
    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let dict = self.with_node_and_model(py, |g, k, model| Ok(g.node_to_dict(k, model)))?;
        let pythonized = pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let pythonized = pythonized.cast::<PyDict>()?;
        fix_children_parents_int_keys(py, pythonized)?;
        if let Ok((owner_py, id)) = self.owned() {
            let owner = owner_py.borrow(py);
            let node_extras = owner.node_extras.borrow();
            if let Some(extras) = node_extras.get(&id) {
                let extras = extras.bind(py);
                if extras.len() > 0 {
                    pythonized.set_item("extras", extras)?;
                } else {
                    pythonized.del_item("extras").ok();
                }
            }
        }
        Ok(pythonized.clone().into_any())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        match &self.repr {
            NodeRepr::Owned { .. } => self.with_node_and_model(py, |g, k, model| {
                let node = &g.nodes[k];
                Ok(format!(
                    "AttackGraphNode(name: \"{}\", id: {}, type: {})",
                    g.full_name_of(k, model),
                    node.id,
                    node.step_type.as_str()
                ))
            }),
            NodeRepr::Detached(d) => Ok(format!("AttackGraphNode(name: \"{}\", id: {}, type: detached)", d.name, d.id)),
        }
    }

    /// `Owned`: owner-ptr+id composite hash, as before. `Detached`: plain
    /// Python object identity (pointer of this very `Py<Self>`) - matches
    /// the Python original's lack of custom `__eq__`/`__hash__` on
    /// `AttackGraphNode` (default identity-based hash/eq).
    fn __hash__(self_: &Bound<'_, Self>, py: Python<'_>) -> isize {
        let slf = self_.borrow();
        match &slf.repr {
            NodeRepr::Owned { .. } => composite_hash(slf.owner_ptr(py).unwrap_or(0), slf.id()),
            NodeRepr::Detached(_) => self_.as_ptr() as isize,
        }
    }

    /// See `__hash__`'s doc comment - same `Owned`/`Detached` split for
    /// `__richcmp__`'s `Eq`/`Ne`. A `Detached` node compared against an
    /// `Owned` one (or vice versa) is simply never equal (different
    /// Python objects), consistent with default identity semantics.
    fn __richcmp__(self_: &Bound<'_, Self>, other: &Bound<'_, PyAny>, op: CompareOp, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let eq = {
            let slf = self_.borrow();
            match &slf.repr {
                NodeRepr::Owned { .. } => match other.extract::<PyRef<'_, PyAttackGraphNode>>() {
                    Ok(other_ref) => slf.eq_with(&other_ref, py),
                    Err(_) => false,
                },
                NodeRepr::Detached(_) => self_.is(other),
            }
        };
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
    /// nodes). `Detached` nodes aren't picklable this way (no owner to
    /// delegate to) - out of scope per Phase 4 decision 8, so this errors
    /// clearly instead.
    #[allow(clippy::type_complexity)]
    fn __reduce__(&self, py: Python<'_>) -> PyResult<(Py<PyAny>, (Py<PyAttackGraph>, i64))> {
        let (owner_py, id) = self.owned()?;
        // Looked up by the real, eventual import path
        // (`maltoolbox._native`, already valid today too - see Phase
        // 0/1's `.so`-copy workaround) rather than hardcoding a
        // `Py<PyFunction>` reference, so this survives the Phase 5
        // packaging fix the same way the exception `__module__` strings
        // were already set up to.
        let func = py.import("maltoolbox._native")?.getattr("_rebuild_attack_graph_node")?.unbind();
        Ok((func, (owner_py.clone_ref(py), id)))
    }

    /// Deep-copying a single `Owned` node standalone (not via
    /// `AttackGraph.__deepcopy__`/`.nodes`'s `__deepcopy__`, both of which
    /// go through `PyAttackGraph::deepcopy_graph` directly) still needs to
    /// produce a correct result, and consult/populate the same `memo` -
    /// delegates to the owning graph's `deepcopy_graph` for the same
    /// whole-graph-clone rationale (consistent `children`/`parents` cross
    /// references), then returns just this node's copy. Checks `memo` first
    /// (keyed by `id(self)`, matching the pure-Python original) so a node
    /// already copied via an earlier `deepcopy_graph` call sharing this
    /// `memo` - e.g. `copy.deepcopy((attack_graph, a_node))` - returns the
    /// *same* copy rather than cloning the whole graph a second time.
    /// `Detached` nodes aren't owned by any graph to delegate to - out of
    /// scope per Phase 4 decision 8, so this errors clearly instead.
    fn __deepcopy__(self_: &Bound<'_, Self>, memo: &Bound<'_, PyDict>) -> PyResult<Py<PyAttackGraphNode>> {
        let py = self_.py();
        if let Some(existing) = memo.get_item(self_.as_ptr() as isize)? {
            return existing.extract().map_err(PyErr::from);
        }
        let slf = self_.borrow();
        let (owner_py, id) = slf.owned()?;
        let owner_py = owner_py.clone_ref(py);
        drop(slf);
        let owner_bound = owner_py.bind(py);
        let new_graph = PyAttackGraph::deepcopy_graph(owner_bound, memo)?;
        let new_graph_ref = new_graph.borrow(py);
        new_graph_ref.node_handle(&new_graph, py, id)
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
    fn __getitem__(&self, py: Python<'_>, id: i64) -> PyResult<Py<PyAttackGraphNode>> {
        let owner = self.owner_py.borrow(py);
        let present = owner.inner.borrow().id_to_node.contains_key(&id);
        if present {
            owner.node_handle(&self.owner_py, py, id)
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

    fn values(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAttackGraphNode>>> {
        let owner = self.owner_py.borrow(py);
        self.ids(py).into_iter().map(|id| owner.node_handle(&self.owner_py, py, id)).collect()
    }

    fn items(&self, py: Python<'_>) -> PyResult<Vec<(i64, Py<PyAttackGraphNode>)>> {
        let owner = self.owner_py.borrow(py);
        self.ids(py)
            .into_iter()
            .map(|id| Ok((id, owner.node_handle(&self.owner_py, py, id)?)))
            .collect()
    }

    #[pyo3(signature = (id, default=None))]
    fn get(&self, py: Python<'_>, id: i64, default: Option<Py<PyAny>>) -> PyResult<Option<Py<PyAny>>> {
        let owner = self.owner_py.borrow(py);
        let present = owner.inner.borrow().id_to_node.contains_key(&id);
        if present {
            Ok(Some(owner.node_handle(&self.owner_py, py, id)?.into_py_any(py)?))
        } else {
            Ok(default)
        }
    }

    /// The pure-Python original's `AttackGraph.nodes` is a plain, freely
    /// settable `dict[int, AttackGraphNode]` (Phase 4 decision 8), so
    /// `copy.deepcopy(attack_graph.nodes, memo)` is just a generic dict
    /// deepcopy that deep-copies each value via `AttackGraphNode.__deepcopy__`
    /// and rebuilds a plain `dict` - exercised directly by
    /// `test_deepcopy_memo_test`. This view isn't a real dict (Phase 3
    /// decision 2's lazy Mapping-protocol wrapper), so it needs its own
    /// `__deepcopy__` returning a real `dict` instead of falling through to
    /// pickle-based generic deepcopy (which can't pickle this Rust-defined
    /// class at all). Delegates to `PyAttackGraph::deepcopy_graph` (the same
    /// whole-graph clone `PyAttackGraph::__deepcopy__` uses) so the returned
    /// nodes' `children`/`parents` cross-references are mutually consistent,
    /// then returns `{id: copied_node}` built from the copied graph - not the
    /// copied graph itself, matching the original's plain-dict return type.
    fn __deepcopy__(&self, py: Python<'_>, memo: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        let owner_bound = self.owner_py.bind(py);
        let new_graph = PyAttackGraph::deepcopy_graph(owner_bound, memo)?;
        let new_graph_ref = new_graph.borrow(py);
        let ids = self.ids(py);
        let dict = PyDict::new(py);
        for id in ids {
            dict.set_item(id, new_graph_ref.node_handle(&new_graph, py, id)?)?;
        }
        Ok(dict.unbind())
    }
}

/// Rebuilds a node handle from a pickled `(owner, id)` pair - the
/// `__reduce__` target for `PyAttackGraphNode`. A plain function
/// (registered in `lib.rs`), not a method, since `__reduce__`'s callable
/// must be importable by name for pickle to locate it. Goes through the
/// owner's cache (Phase 4 decision 1): if the same owner is reachable
/// from multiple places in one combined `pickle.loads` (e.g. the graph
/// itself plus one of its nodes), this ensures the second occurrence
/// resolves to the same Python object as the first, same as live access.
#[pyfunction]
pub fn _rebuild_attack_graph_node(py: Python<'_>, owner: Py<PyAttackGraph>, id: i64) -> PyResult<Py<PyAttackGraphNode>> {
    let graph = owner.borrow(py);
    graph.node_handle(&owner, py, id)
}
