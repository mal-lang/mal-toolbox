//! Mirrors `maltoolbox/language/language_graph_asset.py`'s
//! `LanguageGraphAsset`. A handle (`owner` + `AssetId`) - per Phase 4
//! decision 1, cached per-owner (`caches.assets`) so repeated lookups
//! for the same id return the identical Python object; see `handle.rs`
//! / PYTHON_BINDINGS_IMPLEMENTATION.md.

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::basic::CompareOp;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::IntoPyObjectExt;
use slotmap::Key;

use maltoolbox_language::graph::ids::AssetId;
use maltoolbox_language::graph::LanguageGraph;

use crate::attack_step::PyLanguageGraphAttackStep;
use crate::assoc::PyLanguageGraphAssociation;
use crate::exceptions::graph_error_to_py;
use crate::expr_chain::expr_chain_to_py;
use crate::handle::{cached_handle, composite_hash, SharedLangGraphCaches};

#[pyclass(name = "LanguageGraphAsset", unsendable, skip_from_py_object)]
#[derive(Clone)]
pub struct PyLanguageGraphAsset {
    pub owner: Rc<RefCell<LanguageGraph>>,
    pub id: AssetId,
    pub caches: SharedLangGraphCaches,
}

impl PyLanguageGraphAsset {
    pub fn new(owner: Rc<RefCell<LanguageGraph>>, id: AssetId, caches: SharedLangGraphCaches) -> Self {
        PyLanguageGraphAsset { owner, id, caches }
    }

    fn owner_ptr(&self) -> usize {
        Rc::as_ptr(&self.owner) as usize
    }

    /// Cache-aware constructor for a sibling asset handle owned by the
    /// same `LanguageGraph` - see `handle.rs`'s Phase 4 decision 1 note.
    fn asset_handle(&self, py: Python<'_>, id: AssetId) -> PyResult<Py<PyLanguageGraphAsset>> {
        let owner = self.owner.clone();
        let caches = self.caches.clone();
        cached_handle(&self.caches.assets, py, id, move || PyLanguageGraphAsset::new(owner, id, caches))
    }

    /// Cache-aware constructor for an attack-step handle owned by the
    /// same `LanguageGraph`.
    fn step_handle(&self, py: Python<'_>, id: maltoolbox_language::graph::ids::AttackStepId) -> PyResult<Py<PyLanguageGraphAttackStep>> {
        let owner = self.owner.clone();
        let caches = self.caches.clone();
        cached_handle(&self.caches.steps, py, id, move || PyLanguageGraphAttackStep::new(owner, id, caches))
    }
}

#[pymethods]
impl PyLanguageGraphAsset {
    #[getter]
    fn name(&self) -> String {
        self.owner.borrow().asset(self.id).name.clone()
    }

    #[getter]
    fn is_abstract(&self) -> bool {
        self.owner.borrow().asset(self.id).is_abstract
    }

    #[getter]
    fn info<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (k, v) in &graph.asset(self.id).info {
            dict.set_item(k, v)?;
        }
        Ok(dict)
    }

    /// Own-only associations, by fieldname (not own+inherited - see
    /// `.associations` for that).
    #[getter]
    fn own_associations<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (fieldname, assoc) in &graph.asset(self.id).own_associations {
            dict.set_item(
                fieldname,
                PyLanguageGraphAssociation::new(self.owner.clone(), assoc.clone(), self.caches.clone()),
            )?;
        }
        Ok(dict)
    }

    /// Own + inherited attack steps, by name - matches Python's
    /// `attack_steps` dict (which `_inherit_attack_steps` also
    /// populates with synthesized inherited entries at build time, so
    /// "own" vs "inherited" isn't a distinction left to make here).
    #[getter]
    fn attack_steps<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let steps: Vec<(String, maltoolbox_language::graph::ids::AttackStepId)> =
            self.owner.borrow().asset(self.id).attack_steps.iter().map(|(n, &id)| (n.clone(), id)).collect();
        let dict = PyDict::new(py);
        for (name, step_id) in steps {
            dict.set_item(name, self.step_handle(py, step_id)?)?;
        }
        Ok(dict)
    }

    #[getter]
    fn own_super_asset(&self, py: Python<'_>) -> PyResult<Option<Py<PyLanguageGraphAsset>>> {
        let super_id = self.owner.borrow().asset(self.id).own_super_asset;
        super_id.map(|id| self.asset_handle(py, id)).transpose()
    }

    #[getter]
    fn own_sub_assets(&self, py: Python<'_>) -> PyResult<Vec<Py<PyLanguageGraphAsset>>> {
        let ids: Vec<AssetId> = self.owner.borrow().asset(self.id).own_sub_assets.clone();
        ids.into_iter().map(|id| self.asset_handle(py, id)).collect()
    }

    /// This asset plus every asset that directly or indirectly extends
    /// it. Not cached (Python's is a `cached_property`) - see
    /// `LanguageGraph::fieldname_to_candidate_steps`'s doc comment for
    /// why that tradeoff is accepted throughout this layer. (The
    /// returned *handles* are cached per Phase 4 decision 1 - this just
    /// means the *list* itself is recomputed each access, not that the
    /// objects inside it are fresh each time.)
    #[getter]
    fn sub_assets(&self, py: Python<'_>) -> PyResult<Vec<Py<PyLanguageGraphAsset>>> {
        let ids = self.owner.borrow().sub_assets(self.id);
        ids.into_iter().map(|id| self.asset_handle(py, id)).collect()
    }

    /// This asset plus every asset it directly or indirectly extends,
    /// closest ancestor first.
    #[getter]
    fn super_assets(&self, py: Python<'_>) -> PyResult<Vec<Py<PyLanguageGraphAsset>>> {
        let ids = self.owner.borrow().super_assets(self.id);
        ids.into_iter().map(|id| self.asset_handle(py, id)).collect()
    }

    /// Own + inherited associations, by fieldname.
    #[getter]
    fn associations<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (fieldname, assoc) in graph.associations(self.id) {
            dict.set_item(
                fieldname,
                PyLanguageGraphAssociation::new(self.owner.clone(), assoc, self.caches.clone()),
            )?;
        }
        Ok(dict)
    }

    fn associations_to<'py>(
        &self,
        py: Python<'py>,
        asset_type: &PyLanguageGraphAsset,
    ) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (fieldname, assoc) in graph.associations_to(self.id, asset_type.id) {
            dict.set_item(
                fieldname,
                PyLanguageGraphAssociation::new(self.owner.clone(), assoc, self.caches.clone()),
            )?;
        }
        Ok(dict)
    }

    /// Own + inherited variables: name -> (target asset, optional
    /// expression chain) - the expression chain is a real
    /// `ExpressionsChain` wrapper (closes Phase 1 gap #2; confirmed
    /// necessary for real by `tests/language/test_languagegraph.py::
    /// test_interleaved_vars`, which reads `.right_link.fieldname`
    /// directly on it).
    #[getter]
    fn variables<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (name, (asset_id, expr)) in graph.variables(self.id) {
            let asset_handle = self.asset_handle(py, asset_id)?;
            let expr_obj = match &expr {
                Some(e) => expr_chain_to_py(py, self.owner.clone(), self.caches.clone(), e)?.into_any(),
                None => py.None(),
            };
            dict.set_item(name, (asset_handle, expr_obj))?;
        }
        Ok(dict)
    }

    fn is_subasset_of(&self, target_asset: &PyLanguageGraphAsset) -> bool {
        self.owner.borrow().is_subasset_of(self.id, target_asset.id)
    }

    fn get_all_common_superassets(&self, other: &PyLanguageGraphAsset) -> std::collections::HashSet<String> {
        self.owner
            .borrow()
            .get_all_common_superassets(self.id, other.id)
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.owner.borrow();
        let dict = graph
            .asset(self.id)
            .to_dict(&graph)
            .map_err(graph_error_to_py)?;
        pythonize::pythonize(py, &dict)
            .map_err(|e| crate::exceptions::graph_error_to_py(
                maltoolbox_language::graph::GraphError::Malformed(e.to_string()),
            ))
    }

    pub fn __repr__(&self) -> String {
        format!("LanguageGraphAsset(name: \"{}\")", self.name())
    }

    fn __hash__(&self) -> isize {
        composite_hash(self.owner_ptr(), self.id)
    }

    fn __richcmp__(&self, other: &PyLanguageGraphAsset, op: CompareOp, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let eq = self.owner_ptr() == other.owner_ptr() && self.id == other.id;
        match op {
            CompareOp::Eq => eq.into_py_any(py),
            CompareOp::Ne => (!eq).into_py_any(py),
            _ => Ok(py.NotImplemented()),
        }
    }

    /// Phase 4 decision 9: delegate to a fresh, temporary
    /// `PyLanguageGraph` wrapping the same underlying `Rc<RefCell<_>>` +
    /// `id` (round-tripped through slotmap's stable `KeyData` ffi repr,
    /// since `AssetId` itself isn't picklable) - pickle recursively
    /// pickles that temporary owner via `PyLanguageGraph`'s own
    /// `__reduce__`, so this doesn't need its own graph-serialization
    /// logic. No object-identity requirement here (unlike
    /// `PyAttackGraphNode`) - `test_pickle_languagegraph_asset` only
    /// checks `to_dict()` equality - so a temporary owner handle is
    /// sufficient; see PYTHON_BINDINGS_IMPLEMENTATION.md's "New Phase 4
    /// decision 9".
    #[allow(clippy::type_complexity)]
    fn __reduce__(&self, py: Python<'_>) -> PyResult<(Py<PyAny>, (Py<crate::language_graph::PyLanguageGraph>, u64))> {
        let temp_owner = Py::new(
            py,
            crate::language_graph::PyLanguageGraph {
                inner: self.owner.clone(),
                caches: self.caches.clone(),
            },
        )?;
        let func = py.import("maltoolbox._native")?.getattr("_rebuild_language_graph_asset")?.unbind();
        Ok((func, (temp_owner, self.id.data().as_ffi())))
    }
}

/// Rebuilds a `PyLanguageGraphAsset` handle from a pickled
/// `(owner, ffi_id)` pair - the `__reduce__` target. A plain function
/// (registered in `lib.rs`), not a method, since `__reduce__`'s callable
/// must be importable by name. Goes through the owner's cache (Phase 4
/// decision 1) exactly like live access would.
#[pyfunction]
pub fn _rebuild_language_graph_asset(
    py: Python<'_>,
    owner: Py<crate::language_graph::PyLanguageGraph>,
    ffi_id: u64,
) -> PyResult<Py<PyLanguageGraphAsset>> {
    let id = AssetId::from(slotmap::KeyData::from_ffi(ffi_id));
    let graph = owner.borrow(py);
    graph.asset_handle(py, id)
}

