//! Mirrors `maltoolbox/attackgraph/attackgraph.py`'s `AttackGraph`. The
//! one "container" type in this crate - see
//! PYTHON_BINDINGS_IMPLEMENTATION.md's "Container / handle pattern".
//!
//! Holds, in addition to the core `Rc<RefCell<AttackGraph>>`, the actual
//! `Py<PyLanguageGraph>`/`Option<Py<PyModel>>` objects passed in, so
//! `.lang_graph`/`.model` always return the same Python object. `.model`
//! exists here even though the Rust core's `AttackGraph` has no such
//! field (see `PORTING_NOTES.md` §2) because mal-simulator depends on
//! `attack_graph.model` directly.

use std::cell::RefCell;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySet};
use pyo3::IntoPyObjectExt;

use maltoolbox_attackgraph::ids::AttackGraphNodeId;
use maltoolbox_attackgraph::AttackGraph;
use maltoolbox_language::graph::{generate_graph as build_graph_from_langspec, LanguageGraph};
use maltoolbox_language_py::handle::{cached_handle, new_handle_cache, HandleCache};
use maltoolbox_language_py::PyLanguageGraph;
use maltoolbox_model::{AssetSnapshot, Model};
use maltoolbox_model_py::PyModel;

use crate::detector_support::{build_py_detector, detector_snapshots_for};
use crate::exceptions::{graph_error_to_lookup, graph_error_to_py};
use crate::node::{PyAttackGraphNode, PyAttackGraphNodesView};

#[pyclass(name = "AttackGraph", module = "maltoolbox._native", unsendable, weakref)]
pub struct PyAttackGraph {
    pub inner: Rc<RefCell<AttackGraph>>,
    pub lang_graph_py: Py<PyLanguageGraph>,
    pub model_py: Option<Py<PyModel>>,
    /// Lazily-seeded flat detectors list: `None` until first accessed via
    /// `.detectors`, then the sole source of truth from then on (never
    /// rebuilt from the core again).
    pub detectors_list: Rc<RefCell<Option<Py<PyList>>>>,
    /// Per-node detectors dict side table, lazily populated the same way -
    /// see `node.rs`'s `.detectors` getter.
    pub node_detectors: Rc<RefCell<HashMap<i64, Py<PyDict>>>>,
    /// Same pattern as `node_detectors`, for `AttackGraphNode.extras` -
    /// see `node.rs`'s `.extras` getter. Seeded once per node and never
    /// re-derived, so in-place mutation (`node.extras['x'] = y`) sticks
    /// across accesses.
    pub node_extras: Rc<RefCell<HashMap<i64, Py<PyDict>>>>,
    /// Per-owner `PyAttackGraphNode` handle cache, shared (same `Rc`) with
    /// every node handle this graph ever hands out, so repeated lookups
    /// for the same id return the identical Python object.
    pub node_cache: HandleCache<i64, PyAttackGraphNode>,
    /// Read-only record of each removed node's final state (post-unlink,
    /// pre-delete), keyed by id. Lets a `PyAttackGraphNode` handle whose
    /// entry is gone from `inner.id_to_node` keep resolving its simple
    /// fields (`node.rs`'s `with_node_value`), plus - via
    /// `PyNodeTombstone`'s pre-resolved fields, each computed once at
    /// removal time while the graph could still resolve them -
    /// `.children`/`.parents`, `.detectors`, and `.full_name`/`__repr__`.
    /// `to_dict()` is the one remaining gap: it would need a
    /// `children`/`parents` dict of full *names*, not just ids, which
    /// this struct doesn't carry (see `node.rs`'s doc comment).
    pub tombstones: Rc<RefCell<HashMap<i64, crate::node::PyNodeTombstone>>>,
    /// Per-node `(children, parents)` `PySet` pair, lazily built once per
    /// id and cached from then on, since malsim's hot loop reads
    /// `.parents` per traversability check and rebuilding a `PySet` from
    /// scratch each time is expensive. Cleared wholesale (not per-id) on
    /// any structural mutation (`add_node`/`remove_node`/
    /// `regenerate_graph`/`partially_regenerate_graph` - see
    /// `evict_edges_cache`), never on per-node state-only changes
    /// (`enabled_defenses`, `existence_status`, ...) that don't touch
    /// topology.
    pub node_edges_cache: Rc<RefCell<HashMap<i64, (Py<PySet>, Py<PySet>)>>>,
    /// When `Some`, `.nodes` returns this dict as-is instead of
    /// constructing a `PyAttackGraphNodesView`, letting
    /// `attack_graph.nodes = {...}` freely override the live view -
    /// matching the pure-Python original's plain, freely-settable `dict`
    /// attribute. Reset to `None` by `regenerate_graph`, which rebuilds
    /// live nodes from scratch and should surface those again.
    pub nodes_override: Rc<RefCell<Option<Py<PyDict>>>>,
}

impl PyAttackGraph {
    #[allow(clippy::type_complexity)]
    fn empty_state() -> (
        Rc<RefCell<Option<Py<PyList>>>>,
        Rc<RefCell<HashMap<i64, Py<PyDict>>>>,
        Rc<RefCell<HashMap<i64, Py<PyDict>>>>,
    ) {
        (
            Rc::new(RefCell::new(None)),
            Rc::new(RefCell::new(HashMap::new())),
            Rc::new(RefCell::new(HashMap::new())),
        )
    }

    fn wrap(inner: AttackGraph, lang_graph_py: Py<PyLanguageGraph>, model_py: Option<Py<PyModel>>) -> Self {
        let (detectors_list, node_detectors, node_extras) = Self::empty_state();
        PyAttackGraph {
            inner: Rc::new(RefCell::new(inner)),
            lang_graph_py,
            model_py,
            detectors_list,
            node_detectors,
            node_extras,
            node_cache: new_handle_cache(),
            tombstones: Rc::new(RefCell::new(HashMap::new())),
            nodes_override: Rc::new(RefCell::new(None)),
            node_edges_cache: Rc::new(RefCell::new(HashMap::new())),
        }
    }

    /// Invalidates the whole `.children`/`.parents` cache. Whole-cache,
    /// not per-id: adding or removing one node can change the
    /// children/parents sets of arbitrary other existing nodes, so a
    /// precise per-id invalidation isn't meaningfully cheaper than
    /// letting the next access per node rebuild lazily.
    fn evict_edges_cache(&self) {
        self.node_edges_cache.borrow_mut().clear();
    }

    /// Resets the lazily-seeded detector containers. Used after a full
    /// `regenerate_graph`, which discards every old node and rebuilds
    /// from scratch, so previously-seeded detector containers would
    /// otherwise reference stale/gone nodes.
    fn reset_detector_state(&self) {
        *self.detectors_list.borrow_mut() = None;
        self.node_detectors.borrow_mut().clear();
        self.node_extras.borrow_mut().clear();
    }

    /// Cache-aware constructor for a node handle owned by this graph -
    /// see the `node_cache` field doc comment. `owner_py` must be the
    /// `Py<PyAttackGraph>` wrapping this very `PyAttackGraph` (a plain
    /// `&self` method can't produce a `Py<Self>` of itself, hence callers
    /// pass one in via the `self_: &Bound<'_, Self>` receiver pattern
    /// used throughout this file).
    pub fn node_handle(&self, owner_py: &Py<PyAttackGraph>, py: Python<'_>, id: i64) -> PyResult<Py<PyAttackGraphNode>> {
        let owner_py = owner_py.clone_ref(py);
        cached_handle(&self.node_cache, py, id, move || PyAttackGraphNode::new(owner_py, id))
    }

    /// Evicts `id`'s cache entry, if any. Needed because `add_node`'s
    /// caller-chosen `node_id` can legitimately collide with a
    /// previously-removed node's id, which must build a genuinely new
    /// handle rather than resurface the stale cached one. Not done on
    /// removal itself.
    fn evict_node_handle(&self, id: i64) {
        self.node_cache.borrow_mut().remove(&id);
    }

    /// Shared implementation for `PyAttackGraph::__deepcopy__` and
    /// `PyAttackGraphNodesView::__deepcopy__`/`PyAttackGraphNode::__deepcopy__`
    /// (`node.rs`) - port of `AttackGraph.__deepcopy__`
    /// (`maltoolbox/attackgraph/attackgraph.py`). `memo` is a real Python
    /// dict keyed by `id(python_object)`, exactly like the pure-Python
    /// original, so a whole-graph `copy.deepcopy` call (or one that also
    /// separately touches individual nodes reachable from this graph)
    /// produces exactly one copy of this graph and of each node, with
    /// every cross-reference pointing at the shared copies.
    ///
    /// Unlike the Python original (which builds an empty `AttackGraph`,
    /// then deep-copies each node and re-links `children`/`parents`
    /// individually), this clones the whole core `AttackGraph` in one
    /// shot (`AttackGraph` is `#[derive(Clone)]`): `AttackGraphNodeId`
    /// slotmap keys stay valid and mutually consistent across the clone,
    /// so no manual re-linking is needed. Does not clone `lang_graph` (an
    /// `Rc`, cheaply shared) or `model` (kept identical - the instance
    /// model should remain shared, not copied).
    ///
    /// Registers every node in `memo` (keyed by the original node
    /// handle's `id(...)`) so that deep-copying a node reachable from
    /// this graph elsewhere in the same `copy.deepcopy` call resolves to
    /// the same copied handle this call produces, not a separate
    /// duplicate - mirrors the Python original's `memo[id(node)] =
    /// copied_node` bookkeeping. Does not register the graph itself in
    /// `memo` first (unlike the Python original's `if id(self) in memo`
    /// early-out): nothing in this codebase deep-copies a structure that
    /// reaches the same `AttackGraph` via two different paths, so that
    /// re-entrancy case doesn't arise in practice.
    pub fn deepcopy_graph(self_: &Bound<'_, Self>, memo: &Bound<'_, PyDict>) -> PyResult<Py<PyAttackGraph>> {
        let py = self_.py();
        let self_py: Py<PyAttackGraph> = self_.clone().unbind();
        let slf = self_.borrow();

        let cloned_inner = slf.inner.borrow().clone();
        let ids: Vec<i64> = slf.inner.borrow().id_to_node.keys().copied().collect();
        let lang_graph_py = slf.lang_graph_py.clone_ref(py);
        let model_py = slf.model_py.as_ref().map(|m| m.clone_ref(py));

        let new_graph = Py::new(py, PyAttackGraph::wrap(cloned_inner, lang_graph_py, model_py))?;

        // Register each node in `memo`, keyed by the original handle's
        // `id(...)`, pointing at the corresponding handle on the new
        // graph - see this method's doc comment.
        let new_graph_ref = new_graph.borrow(py);
        for id in ids {
            let original_handle = slf.node_handle(&self_py, py, id)?;
            let copied_handle = new_graph_ref.node_handle(&new_graph, py, id)?;
            memo.set_item(original_handle.bind(py).as_ptr() as isize, copied_handle)?;
        }
        drop(slf);

        Ok(new_graph.clone_ref(py))
    }

    /// Borrows `self.model_py` (if any) down to a `&Model` in one scope,
    /// for the core API's `Option<&Model>` parameters.
    pub fn with_model<R>(&self, py: Python<'_>, f: impl FnOnce(Option<&Model>) -> R) -> R {
        match &self.model_py {
            Some(m) => {
                let model_ref = m.borrow(py);
                let core_model = model_ref.inner.borrow();
                f(Some(&core_model))
            }
            None => f(None),
        }
    }

    /// Builds the core's `to_dict()` `Value`, then overlays each node's
    /// live `node_extras` side-table entry (if seeded) onto its
    /// `"extras"` field, since the core's own `node_to_dict` only knows
    /// about `extras` as captured at generation time and can't see
    /// Python-side mutation of the lazily-seeded dict
    /// (`node.extras['x'] = y`). Operates on the `serde_json::Value`
    /// directly (before `fix_children_parents_int_keys` gives
    /// `children`/`parents` integer keys, which aren't valid JSON) so
    /// `to_dict`/`save_to_file` can share this one pass.
    fn to_dict_value(&self, py: Python<'_>) -> serde_json::Value {
        let mut dict = self.with_model(py, |model| self.inner.borrow().to_dict(model));
        if let Some(steps) = dict.get_mut("attack_steps").and_then(|v| v.as_object_mut()) {
            let node_extras = self.node_extras.borrow();
            for node_value in steps.values_mut() {
                let Some(id) = node_value.get("id").and_then(|v| v.as_i64()) else {
                    continue;
                };
                let Some(extras) = node_extras.get(&id) else { continue };
                let extras = extras.bind(py);
                if extras.is_empty() {
                    if let Some(obj) = node_value.as_object_mut() {
                        obj.remove("extras");
                    }
                    continue;
                }
                if let Ok(value) = pythonize::depythonize::<serde_json::Value>(extras) {
                    node_value["extras"] = value;
                }
            }
        }
        dict
    }

    fn bare_lang_graph(py: Python<'_>, lang_graph_py: &Py<PyLanguageGraph>, model_py: Option<&Py<PyModel>>) -> Rc<LanguageGraph> {
        if let Some(m) = model_py {
            // Reuse the model's own bare `Rc<LanguageGraph>` - an `Rc`
            // clone, no data copy.
            return m.borrow(py).inner.borrow().lang_graph.clone();
        }
        // No model to borrow from - clone the data out of
        // `lang_graph_py`'s `Rc<RefCell<_>>` once (same technique as
        // `PyModel::new`).
        Rc::new(lang_graph_py.borrow(py).inner.borrow().clone())
    }

    /// Extracts `.id` from every `ModelAsset` in an arbitrary Python
    /// iterable - same reasoning as `maltoolbox-model-py`'s `ids_of`
    /// (`Vec<PyRef<T>>` extraction only accepts `Sequence`s, not sets).
    fn asset_ids_of(obj: &Bound<'_, PyAny>) -> PyResult<HashSet<i64>> {
        obj.try_iter()?
            .map(|item| Ok(item?.extract::<PyRef<'_, maltoolbox_model_py::PyModelAsset>>()?.id))
            .collect()
    }

    /// Extracts `(left_id, fieldname, right_id)` from a Python
    /// `set[tuple[ModelAsset, str, ModelAsset]]`.
    fn assoc_ids_of(obj: &Bound<'_, PyAny>) -> PyResult<HashSet<(i64, String, i64)>> {
        obj.try_iter()?
            .map(|item| {
                let tuple = item?;
                let left: PyRef<'_, maltoolbox_model_py::PyModelAsset> = tuple.get_item(0)?.extract()?;
                let fieldname: String = tuple.get_item(1)?.extract()?;
                let right: PyRef<'_, maltoolbox_model_py::PyModelAsset> = tuple.get_item(2)?.extract()?;
                Ok((left.id, fieldname, right.id))
            })
            .collect()
    }

    /// Resolves a removed asset's id to an `AssetSnapshot`, trying the
    /// live `model.assets` entry first and falling back to the model's
    /// tombstone record (same live-then-tombstone logic as
    /// `PyModelAsset::with_asset`, duplicated here since that helper is
    /// private to `maltoolbox-model-py`).
    fn asset_snapshot_for(model_py: &Py<PyModel>, py: Python<'_>, id: i64) -> PyResult<AssetSnapshot> {
        let model = model_py.borrow(py);
        {
            let core_model = model.inner.borrow();
            if let Some(live) = core_model.assets.get(&id) {
                return Ok(AssetSnapshot {
                    name: live.name.clone(),
                    lg_asset: live.lg_asset,
                    final_state: live.clone(),
                });
            }
        }
        let tombstones = model.tombstones.borrow();
        if let Some(final_state) = tombstones.get(&id) {
            return Ok(AssetSnapshot {
                name: final_state.name.clone(),
                lg_asset: final_state.lg_asset,
                final_state: final_state.clone(),
            });
        }
        Err(pyo3::exceptions::PyLookupError::new_err(format!(
            "Asset with id {id} not found in model (never added, or removed with no tombstone recorded)."
        )))
    }
}

#[pymethods]
impl PyAttackGraph {
    /// `lang_graph=None` is accepted purely so `AttackGraph(None)`
    /// succeeds, matching the pure-Python original. A minimal placeholder
    /// `PyLanguageGraph` (built from an empty langspec `{}`) is
    /// constructed internally rather than threading `Option` through
    /// every other field/method that assumes a real one.
    #[new]
    #[pyo3(signature = (lang_graph, model=None))]
    pub fn new(py: Python<'_>, lang_graph: Option<Py<PyLanguageGraph>>, model: Option<Py<PyModel>>) -> PyResult<Self> {
        let lang_graph = match lang_graph {
            Some(lg) => lg,
            None => Py::new(
                py,
                PyLanguageGraph::wrap(
                    build_graph_from_langspec(serde_json::json!({}))
                        .map_err(maltoolbox_language_py::exceptions::graph_error_to_py)?,
                ),
            )?,
        };
        let inner = match &model {
            Some(m) => {
                let model_ref = m.borrow(py);
                let core_model = model_ref.inner.borrow();
                AttackGraph::from_model(&core_model).map_err(graph_error_to_py)?
            }
            None => AttackGraph::empty(Self::bare_lang_graph(py, &lang_graph, None)),
        };
        Ok(Self::wrap(inner, lang_graph, model))
    }

    /// Makes the reference cycle `PyAttackGraph.node_cache ->
    /// Py<PyAttackGraphNode> -> NodeRepr::Owned.owner_py -> back to this
    /// `PyAttackGraph`` visible to CPython's cyclic GC. Without this (and
    /// `PyAttackGraphNode::__traverse__`/`__clear__` on the other side,
    /// `node.rs`), both `Py<T>` legs live inside Rust-side
    /// `Rc<RefCell<...>>` containers invisible to `tp_traverse`, so
    /// `gc.collect()` could never find and break the cycle, leaking every
    /// `AttackGraph` that ever handed out a node handle. Visits every
    /// `Py<T>` field that can reach back into a cycle; `inner`/
    /// `tombstones` are plain Rust data, so nothing to visit there.
    fn __traverse__(&self, visit: pyo3::PyVisit<'_>) -> Result<(), pyo3::PyTraverseError> {
        visit.call(&self.lang_graph_py)?;
        if let Some(model_py) = &self.model_py {
            visit.call(model_py)?;
        }
        if let Some(list) = self.detectors_list.borrow().as_ref() {
            visit.call(list)?;
        }
        for v in self.node_detectors.borrow().values() {
            visit.call(v)?;
        }
        for v in self.node_extras.borrow().values() {
            visit.call(v)?;
        }
        for v in self.node_cache.borrow().values() {
            visit.call(v)?;
        }
        for (children, parents) in self.node_edges_cache.borrow().values() {
            visit.call(children)?;
            visit.call(parents)?;
        }
        if let Some(dict) = self.nodes_override.borrow().as_ref() {
            visit.call(dict)?;
        }
        Ok(())
    }

    /// Breaks the cycle described in `__traverse__`'s doc comment by
    /// dropping every `Py<PyAttackGraphNode>` this graph holds (plus the
    /// other lazily-cached `Py<T>` containers), so the cycle collector
    /// can finish reclaiming both sides. Matches the `CycleWithClear`
    /// pattern in pyo3's own `test_gc.rs`: it's fine to leave the object
    /// method-unusable afterward since `__clear__` only runs during
    /// cycle collection, when nothing reachable from Python still uses it.
    fn __clear__(&self) {
        self.node_cache.borrow_mut().clear();
        self.node_edges_cache.borrow_mut().clear();
        self.node_detectors.borrow_mut().clear();
        self.node_extras.borrow_mut().clear();
        *self.detectors_list.borrow_mut() = None;
        *self.nodes_override.borrow_mut() = None;
    }

    #[getter]
    fn lang_graph(&self, py: Python<'_>) -> Py<PyLanguageGraph> {
        self.lang_graph_py.clone_ref(py)
    }

    #[getter]
    fn model(&self, py: Python<'_>) -> Option<Py<PyModel>> {
        self.model_py.as_ref().map(|m| m.clone_ref(py))
    }

    #[setter]
    fn set_model(&mut self, model: Option<Py<PyModel>>) {
        self.model_py = model;
    }

    #[getter]
    fn next_node_id(&self) -> i64 {
        self.inner.borrow().next_node_id
    }

    /// A lazy read-only Mapping view, not a real `dict` - see `node.rs`'s
    /// `PyAttackGraphNodesView`. Needs `Py<Self>` to hand out, hence the
    /// `&Bound<'_, Self>` receiver instead of `&self`. When
    /// `nodes_override` has been set (via the `#[setter]` below), that
    /// real `dict` is returned as-is instead, matching the pure-Python
    /// original's freely settable `dict` attribute
    /// (`attack_graph.nodes = {...}`), which the patternfinder tests rely
    /// on to hand-build small graphs of detached nodes.
    #[getter]
    fn nodes(self_: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let py = self_.py();
        let slf = self_.borrow();
        if let Some(dict) = &*slf.nodes_override.borrow() {
            return Ok(dict.clone_ref(py).into_any());
        }
        drop(slf);
        let view = PyAttackGraphNodesView {
            owner_py: self_.clone().unbind(),
        };
        view.into_py_any(py)
    }

    /// See the `.nodes` getter's doc comment. Cleared back to `None` by
    /// `regenerate_graph`, so a full rebuild surfaces the
    /// freshly-generated live nodes again instead of a stale override.
    #[setter]
    fn set_nodes(&self, value: &Bound<'_, PyDict>) {
        *self.nodes_override.borrow_mut() = Some(value.clone().unbind());
    }

    /// `dict[str, AttackGraphNode]`, rebuilt fresh per access - not a
    /// hot path like `.nodes`, so no caching is needed here.
    #[getter]
    fn full_name_to_node<'py>(self_: &Bound<'py, Self>) -> PyResult<Bound<'py, PyDict>> {
        let py = self_.py();
        let owner_py: Py<PyAttackGraph> = self_.clone().unbind();
        let slf = self_.borrow();
        let ids: Vec<(String, i64)> = {
            let graph = slf.inner.borrow();
            graph.full_name_to_node.iter().map(|(full_name, &key)| (full_name.clone(), graph.nodes[key].id)).collect()
        };
        let dict = PyDict::new(py);
        for (full_name, id) in ids {
            dict.set_item(full_name, slf.node_handle(&owner_py, py, id)?)?;
        }
        Ok(dict)
    }

    #[getter]
    fn attack_steps(self_: &Bound<'_, Self>) -> PyResult<Vec<Py<PyAttackGraphNode>>> {
        let py = self_.py();
        let owner_py: Py<PyAttackGraph> = self_.clone().unbind();
        let slf = self_.borrow();
        let ids: Vec<i64> = {
            let graph = slf.inner.borrow();
            graph.attack_steps.iter().map(|&key| graph.nodes[key].id).collect()
        };
        ids.into_iter().map(|id| slf.node_handle(&owner_py, py, id)).collect()
    }

    #[getter]
    fn defense_steps(self_: &Bound<'_, Self>) -> PyResult<Vec<Py<PyAttackGraphNode>>> {
        let py = self_.py();
        let owner_py: Py<PyAttackGraph> = self_.clone().unbind();
        let slf = self_.borrow();
        let ids: Vec<i64> = {
            let graph = slf.inner.borrow();
            graph.defense_steps.iter().map(|&key| graph.nodes[key].id).collect()
        };
        ids.into_iter().map(|id| slf.node_handle(&owner_py, py, id)).collect()
    }

    /// Live, mutable flat list: lazily seeded from every node's current
    /// core-side detector data on first access, then the same
    /// `Py<PyList>` object on every subsequent access, so external
    /// `.append()`/`.remove()` mutation is visible to later reads. Never
    /// kept in sync with the per-node `.detectors` dicts after seeding,
    /// matching the pure-Python original.
    #[getter]
    fn detectors(self_: &Bound<'_, Self>) -> PyResult<Py<PyList>> {
        let py = self_.py();
        {
            let slf = self_.borrow();
            let cell = slf.detectors_list.borrow();
            if let Some(list) = &*cell {
                return Ok(list.clone_ref(py));
            }
        }
        let owner_py: Py<PyAttackGraph> = self_.clone().unbind();
        let snapshot = {
            let slf = self_.borrow();
            let graph = slf.inner.borrow();
            let keys: Vec<AttackGraphNodeId> = graph.nodes.keys().collect();
            detector_snapshots_for(&graph, &keys)
        };
        let list = PyList::empty(py);
        for snap in &snapshot {
            list.append(build_py_detector(py, &owner_py, snap)?)?;
        }
        let slf = self_.borrow();
        *slf.detectors_list.borrow_mut() = Some(list.clone().unbind());
        Ok(list.unbind())
    }

    fn get_node_by_full_name(self_: &Bound<'_, Self>, full_name: &str) -> PyResult<Py<PyAttackGraphNode>> {
        let py = self_.py();
        let owner_py: Py<PyAttackGraph> = self_.clone().unbind();
        let slf = self_.borrow();
        let id = {
            let graph = slf.inner.borrow();
            let key = graph.get_node_by_full_name(full_name).map_err(graph_error_to_lookup)?;
            graph.nodes[key].id
        };
        slf.node_handle(&owner_py, py, id)
    }

    /// Matches Python's `regenerate_graph`: a full rebuild from
    /// `self.model`, discarding every existing node, so any already-held
    /// `PyAttackGraphNode` handle for an old id correctly fails to
    /// resolve afterward. Also clears `node_cache` entirely, since fresh
    /// generation may reuse the same `i64` ids for logically different
    /// nodes.
    fn regenerate_graph(&self, py: Python<'_>) -> PyResult<()> {
        let model_py = self
            .model_py
            .as_ref()
            .ok_or_else(|| pyo3::exceptions::PyAssertionError::new_err("Model required to generate graph"))?;
        let model_ref = model_py.borrow(py);
        let core_model = model_ref.inner.borrow();
        self.inner.borrow_mut().regenerate_graph(&core_model).map_err(graph_error_to_py)?;
        self.reset_detector_state();
        self.node_cache.borrow_mut().clear();
        self.evict_edges_cache();
        // A full rebuild should surface the freshly-generated live
        // nodes, not a stale `.nodes = {...}` override from before the
        // rebuild - see the `.nodes` getter/setter's doc comment.
        *self.nodes_override.borrow_mut() = None;
        Ok(())
    }

    #[pyo3(signature = (new_assets=None, new_associations=None, removed_assets=None, removed_associations=None))]
    fn partially_regenerate_graph(
        self_: &Bound<'_, Self>,
        new_assets: Option<&Bound<'_, PyAny>>,
        new_associations: Option<&Bound<'_, PyAny>>,
        removed_assets: Option<&Bound<'_, PyAny>>,
        removed_associations: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Vec<Py<PyAttackGraphNode>>> {
        let py = self_.py();
        let owner_py: Py<PyAttackGraph> = self_.clone().unbind();
        let slf = self_.borrow();
        let model_py = slf
            .model_py
            .as_ref()
            .map(|m| m.clone_ref(py))
            .ok_or_else(|| pyo3::exceptions::PyAssertionError::new_err("Model required to generate graph"))?;

        let new_assets = new_assets.map(Self::asset_ids_of).transpose()?.unwrap_or_default();
        let new_associations = new_associations.map(Self::assoc_ids_of).transpose()?.unwrap_or_default();
        let removed_asset_ids = removed_assets.map(Self::asset_ids_of).transpose()?.unwrap_or_default();
        let removed_associations = removed_associations.map(Self::assoc_ids_of).transpose()?.unwrap_or_default();

        let mut removed_snapshots: HashMap<i64, AssetSnapshot> = HashMap::new();
        for id in &removed_asset_ids {
            removed_snapshots.insert(*id, Self::asset_snapshot_for(&model_py, py, *id)?);
        }

        // Snapshot every node's full state before the call, so any node
        // removed as a side effect (the core's own internal
        // `removal_candidates`, not surfaced back to this binding) can
        // still have its stale `node_detectors` entry purged and its
        // final state recorded in `tombstones` below. Cloning every node
        // (not just ids) is more than the detector-purge path alone
        // needs, but this method isn't a simulation hot path, so the
        // cost is acceptable for the tombstone coverage it buys.
        // `key_to_id_before` is captured in the same borrow as
        // `nodes_before`, so a removed node's `children`/`parents` keys
        // are resolved against slotmap state as it stood immediately
        // before this call's mutations - resolving against the
        // *post*-call state instead would risk a key already recycled
        // for an unrelated new node (see `PyNodeTombstone`'s doc
        // comment). `detector_snapshots_before`/`full_names_before` do
        // the same for `.detectors`/`.full_name`.
        let (nodes_before, key_to_id_before, detector_snapshots_before, full_names_before): (
            HashMap<i64, maltoolbox_attackgraph::AttackGraphNode>,
            HashMap<AttackGraphNodeId, i64>,
            HashMap<i64, Vec<crate::detector_support::DetectorSnapshot>>,
            HashMap<i64, String>,
        ) = {
            let graph = slf.inner.borrow();
            let model_ref = model_py.borrow(py);
            let core_model = model_ref.inner.borrow();
            let nodes_before: HashMap<i64, maltoolbox_attackgraph::AttackGraphNode> =
                graph.nodes.values().map(|n| (n.id, n.clone())).collect();
            let key_to_id_before: HashMap<AttackGraphNodeId, i64> = graph.nodes.iter().map(|(k, n)| (k, n.id)).collect();
            let all_keys: Vec<AttackGraphNodeId> = key_to_id_before.keys().copied().collect();
            let mut detector_snapshots_before: HashMap<i64, Vec<crate::detector_support::DetectorSnapshot>> = HashMap::new();
            for snap in detector_snapshots_for(&graph, &all_keys) {
                detector_snapshots_before.entry(snap.node_id).or_default().push(snap);
            }
            let full_names_before: HashMap<i64, String> = key_to_id_before
                .iter()
                .map(|(&k, &id)| (id, graph.full_name_of(k, Some(&core_model))))
                .collect();
            (nodes_before, key_to_id_before, detector_snapshots_before, full_names_before)
        };
        let node_ids_before: HashSet<i64> = nodes_before.keys().copied().collect();

        let created_ids: Vec<i64> = {
            let model_ref = model_py.borrow(py);
            let core_model = model_ref.inner.borrow();
            let created = slf
                .inner
                .borrow_mut()
                .partially_regenerate_graph(
                    &core_model,
                    &new_assets,
                    &new_associations,
                    &removed_snapshots,
                    &removed_associations,
                )
                .map_err(graph_error_to_py)?;
            let graph = slf.inner.borrow();
            created.into_iter().map(|key| graph.nodes[key].id).collect()
        };

        slf.evict_edges_cache();

        // Purge stale per-node detector entries, and record a tombstone,
        // for any node removed as a side effect of this call (see
        // `nodes_before`/`node_ids_before` above).
        {
            let node_ids_after: HashSet<i64> = slf.inner.borrow().id_to_node.keys().copied().collect();
            let mut table = slf.node_detectors.borrow_mut();
            let mut extras_table = slf.node_extras.borrow_mut();
            let mut tombstones = slf.tombstones.borrow_mut();
            for removed_id in node_ids_before.difference(&node_ids_after) {
                table.remove(removed_id);
                extras_table.remove(removed_id);
                if let Some(final_state) = nodes_before.get(removed_id) {
                    let children_ids: Vec<i64> = final_state
                        .children
                        .iter()
                        .filter_map(|k| key_to_id_before.get(k).copied())
                        .collect();
                    let parents_ids: Vec<i64> = final_state
                        .parents
                        .iter()
                        .filter_map(|k| key_to_id_before.get(k).copied())
                        .collect();
                    tombstones.insert(
                        *removed_id,
                        crate::node::PyNodeTombstone {
                            state: final_state.clone(),
                            children_ids,
                            parents_ids,
                            detector_snapshots: detector_snapshots_before.get(removed_id).cloned().unwrap_or_default(),
                            full_name: full_names_before.get(removed_id).cloned().unwrap_or_else(|| final_state.fallback_full_name()),
                        },
                    );
                }
            }
        }

        // Seed detector containers for newly-created nodes only; existing
        // nodes' already-seeded state is left untouched, matching
        // Python's `partially_regenerate_graph` only ever calling
        // `_create_detectors` for the newly-created nodes.
        let snapshot = {
            let graph = slf.inner.borrow();
            let keys: Vec<AttackGraphNodeId> = created_ids.iter().filter_map(|&id| graph.id_to_node.get(&id).copied()).collect();
            detector_snapshots_for(&graph, &keys)
        };
        let mut by_node: HashMap<i64, Vec<&crate::detector_support::DetectorSnapshot>> = HashMap::new();
        for snap in &snapshot {
            by_node.entry(snap.node_id).or_default().push(snap);
        }
        for (&node_id, snaps) in &by_node {
            let dict = PyDict::new(py);
            for snap in snaps {
                dict.set_item(&snap.label, build_py_detector(py, &owner_py, snap)?)?;
            }
            slf.node_detectors.borrow_mut().insert(node_id, dict.unbind());
        }
        if let Some(list) = &*slf.detectors_list.borrow() {
            let list = list.bind(py);
            for snap in &snapshot {
                list.append(build_py_detector(py, &owner_py, snap)?)?;
            }
        }

        created_ids.into_iter().map(|id| slf.node_handle(&owner_py, py, id)).collect()
    }

    #[pyo3(signature = (lg_attack_step, node_id=None, model_asset=None, ttc_dist=None, existence_status=None, full_name=None))]
    #[allow(clippy::too_many_arguments)]
    fn add_node(
        self_: &Bound<'_, Self>,
        lg_attack_step: PyRef<'_, maltoolbox_language_py::PyLanguageGraphAttackStep>,
        node_id: Option<i64>,
        model_asset: Option<PyRef<'_, maltoolbox_model_py::PyModelAsset>>,
        ttc_dist: Option<&Bound<'_, PyAny>>,
        existence_status: Option<bool>,
        full_name: Option<String>,
    ) -> PyResult<Py<PyAttackGraphNode>> {
        let py = self_.py();
        let owner_py: Py<PyAttackGraph> = self_.clone().unbind();
        let slf = self_.borrow();

        let ttc_value = ttc_dist
            .map(|v| -> PyResult<serde_json::Value> {
                pythonize::depythonize(v).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
            })
            .transpose()?;

        let key = {
            let mut graph = slf.inner.borrow_mut();
            slf.with_model(py, |model| {
                graph.add_node(
                    lg_attack_step.id,
                    model,
                    node_id,
                    model_asset.as_ref().map(|a| a.id),
                    ttc_value,
                    existence_status,
                    full_name,
                )
            })
            .map_err(graph_error_to_py)?
        };
        let id = slf.inner.borrow().nodes[key].id;
        // See `evict_node_handle`'s doc comment.
        slf.evict_node_handle(id);
        // Deliberately not `evict_edges_cache()` here: the core's
        // `add_node` always creates the new node with empty
        // `children`/`parents`, never linked into any existing node's
        // edges as a side effect, so no other node's cached `(children,
        // parents)` pair can have gone stale. Wiping the whole cache
        // here would also silently discard any direct Python-side
        // mutation of an already-fetched edges set
        // (`some_node.parents.add(new_node)`) made before this call: the
        // mutated `PySet` is correct in-memory, but an evicted cache
        // would rebuild from the (unmodified) core and lose it.
        slf.node_handle(&owner_py, py, id)
    }

    fn remove_node(&self, node: &PyAttackGraphNode, py: Python<'_>) -> PyResult<()> {
        let node_id = node.id();
        let mut graph = self.inner.borrow_mut();
        let key = graph
            .id_to_node
            .get(&node_id)
            .copied()
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err(node_id))?;
        // Capture detector snapshots and full_name before removal, while
        // `key` still resolves to a live node - both need the node
        // present at `key`, unlike the children/parents translation
        // below (which only needs other nodes' keys, untouched by
        // removing this one).
        let detector_snapshots = detector_snapshots_for(&graph, &[key]);
        let full_name = match &self.model_py {
            Some(m) => {
                let model_ref = m.borrow(py);
                let core_model = model_ref.inner.borrow();
                graph.full_name_of(key, Some(&core_model))
            }
            None => graph.full_name_of(key, None),
        };
        let final_state = graph.remove_node(key).map_err(graph_error_to_py)?;
        // Resolve children/parents to stable i64 ids while `graph` is
        // still borrowed, right after removal - a single non-batch
        // removal doesn't touch any other node's slotmap key, so this is
        // the simplest point at which the translation is guaranteed
        // valid.
        let children_ids: Vec<i64> = final_state.children.iter().filter_map(|k| graph.nodes.get(*k).map(|n| n.id)).collect();
        let parents_ids: Vec<i64> = final_state.parents.iter().filter_map(|k| graph.nodes.get(*k).map(|n| n.id)).collect();
        drop(graph);
        self.node_detectors.borrow_mut().remove(&node_id);
        self.node_extras.borrow_mut().remove(&node_id);
        self.tombstones.borrow_mut().insert(
            node_id,
            crate::node::PyNodeTombstone {
                state: final_state,
                children_ids,
                parents_ids,
                detector_snapshots,
                full_name,
            },
        );
        self.evict_edges_cache();
        Ok(())
    }

    /// Each node's `children`/`parents` need the same int-key fixup
    /// `PyAttackGraphNode::to_dict` applies standalone - see
    /// `fix_children_parents_int_keys`.
    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let dict = self.to_dict_value(py);
        let pythonized = pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let pythonized = pythonized.cast::<PyDict>()?;
        if let Some(steps) = pythonized.get_item("attack_steps")? {
            let steps = steps.cast::<PyDict>()?;
            for (_, node_dict) in steps.iter() {
                let node_dict = node_dict.cast::<PyDict>()?;
                crate::node::fix_children_parents_int_keys(py, node_dict)?;
            }
        }
        Ok(pythonized.clone().into_any())
    }

    fn _to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.to_dict(py)
    }

    /// `PathBuf`, not `&str` - pyo3 extracts it from both a plain `str`
    /// and any `os.PathLike` (e.g. `pathlib.Path`), matching the Python
    /// original's file APIs.
    ///
    /// Routed through `self.to_dict_value()` (not the core's own
    /// `AttackGraph::save_to_file`, which only sees the generation-time
    /// snapshot) so the `node_extras` overlay is reflected on disk too -
    /// matching the Python original's `save_to_file`, which always
    /// delegated to `self._to_dict()`.
    fn save_to_file(&self, py: Python<'_>, filename: PathBuf) -> PyResult<()> {
        let value = self.to_dict_value(py);
        maltoolbox_fileutil::save_dict_to_file(filename, &value).map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))
    }

    #[staticmethod]
    #[pyo3(signature = (filename, lang_graph, model=None))]
    fn load_from_file(py: Python<'_>, filename: PathBuf, lang_graph: Py<PyLanguageGraph>, model: Option<Py<PyModel>>) -> PyResult<Self> {
        let bare_lang_graph = Self::bare_lang_graph(py, &lang_graph, model.as_ref());
        let inner = match &model {
            Some(m) => {
                let model_ref = m.borrow(py);
                let core_model = model_ref.inner.borrow();
                AttackGraph::load_from_file(filename, bare_lang_graph, Some(&core_model))
            }
            None => AttackGraph::load_from_file(filename, bare_lang_graph, None),
        }
        .map_err(graph_error_to_py)?;
        Ok(Self::wrap(inner, lang_graph, model))
    }

    fn __repr__(&self, py: Python<'_>) -> String {
        let graph = self.inner.borrow();
        let model_repr = match &self.model_py {
            Some(m) => m.bind(py).repr().map(|r| r.to_string()).unwrap_or_else(|_| "None".to_string()),
            None => "None".to_string(),
        };
        format!(
            "AttackGraph(Number of nodes: {}, model: {}, language: {}",
            graph.nodes.len(),
            model_repr,
            self.lang_graph_py.bind(py).repr().map(|r| r.to_string()).unwrap_or_else(|_| "None".to_string()),
        )
    }

    /// Bundles this graph's own `_to_dict()` plus its `lang_graph`'s
    /// serialized state (always present) and its `model`'s (when there
    /// is one), so unpickling can rebuild the whole chain bottom-up with
    /// no original Python object or on-disk file needed, including a
    /// model-less graph. `lang_graph_state` is always included
    /// independently of `model_state` so that case round-trips too.
    #[staticmethod]
    fn _from_pickle_state(
        py: Python<'_>,
        state: &Bound<'_, PyAny>,
        lang_graph_state: &Bound<'_, PyAny>,
        model_state: Option<Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let native = py.import("maltoolbox._native")?;

        let (lang_graph_py, model_py): (Py<PyLanguageGraph>, Option<Py<PyModel>>) = match model_state {
            Some(model_dict) => {
                // Let `Model._from_pickle_state` reconstruct the nested
                // `LanguageGraph` itself, then pull the resulting object
                // back off `model.lang_graph` rather than building a
                // second, separate `LanguageGraph` here.
                let model_cls = native.getattr("Model")?;
                let model_obj = model_cls.call_method1("_from_pickle_state", (model_dict, lang_graph_state))?;
                let lang_graph_obj = model_obj.getattr("lang_graph")?;
                (lang_graph_obj.extract()?, Some(model_obj.extract()?))
            }
            None => {
                let lg_cls = native.getattr("LanguageGraph")?;
                let lang_graph_obj = lg_cls.call_method1("_from_pickle_state", (lang_graph_state,))?;
                (lang_graph_obj.extract()?, None)
            }
        };

        let value: serde_json::Value = pythonize::depythonize(state).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let bare_lang_graph = Self::bare_lang_graph(py, &lang_graph_py, model_py.as_ref());
        let model_ref = model_py.as_ref().map(|m| m.borrow(py));
        let core_model = model_ref.as_ref().map(|m| m.inner.borrow());
        let inner = AttackGraph::from_dict(&value, bare_lang_graph, core_model.as_deref()).map_err(graph_error_to_py)?;
        drop(core_model);
        drop(model_ref);
        Ok(Self::wrap(inner, lang_graph_py, model_py))
    }

    /// Uses `to_dict_value` (string-keyed `children`/`parents`), not
    /// `self.to_dict()`/`._to_dict()` (which runs
    /// `fix_children_parents_int_keys` to give Python callers integer
    /// keys). `_from_pickle_state` feeds `state` back through
    /// `pythonize::depythonize` into a `serde_json::Value`, and
    /// `serde_json::Value::Object` only accepts string keys, so the
    /// int-keyed form would fail to unpickle any graph with a linked
    /// node. The core's own `AttackGraph::from_dict` parses
    /// `children`/`parents` ids back out of string keys too, so this
    /// round-trips correctly.
    #[allow(clippy::type_complexity)]
    fn __reduce__<'py>(
        &self,
        py: Python<'py>,
    ) -> PyResult<(Bound<'py, PyAny>, (Bound<'py, PyAny>, Bound<'py, PyAny>, Option<Bound<'py, PyAny>>))> {
        let cls = py.get_type::<PyAttackGraph>();
        let func = cls.getattr("_from_pickle_state")?;
        let state = pythonize::pythonize(py, &self.to_dict_value(py)).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let lang_graph_state = self.lang_graph_py.bind(py).call_method0("_to_dict")?;
        let model_state = match &self.model_py {
            Some(m) => Some(m.bind(py).call_method0("_to_dict")?),
            None => None,
        };
        Ok((func, (state, lang_graph_state, model_state)))
    }

    /// See `deepcopy_graph`'s doc comment for the full rationale.
    fn __deepcopy__(self_: &Bound<'_, Self>, memo: &Bound<'_, PyDict>) -> PyResult<Py<PyAttackGraph>> {
        Self::deepcopy_graph(self_, memo)
    }
}
