//! Mirrors `maltoolbox/model.py`'s `ModelAsset`. A handle (`owner` +
//! `i64` id), not a cache - same shape as Phase 1's
//! `PyLanguageGraphAsset`/`PyLanguageGraphAttackStep`. No `#[new]`:
//! the real Python `ModelAsset.__init__` takes no `Model` argument at
//! all (fully detached construction), which is incompatible with this
//! handle design the same way Phase 1's `LanguageGraphAsset`/
//! `LanguageGraphAttackStep` detached construction was - resolved there
//! by rewriting the one affected test (Phase 1 gap #1); the
//! `ModelAsset` analog (`test_model_remove_nonexisting_asset`) is
//! resolved the same way per Phase 2 decision 2. `ModelAsset` is only
//! ever handed out by `PyModel`.
//!
//! **Post-removal readability**: a handle whose `id` has been removed
//! from `owner.assets` (via `Model.remove_asset`) falls back to
//! `owner`'s `Tombstones` map (populated by `PyModel::remove_asset` from
//! `AssetSnapshot::final_state`) for every *read-only* getter, matching
//! the real Python `ModelAsset` object staying fully readable after
//! removal. Mutating methods (`add_associated_assets`/
//! `remove_associated_assets`/`validate_associated_assets`) do *not* get
//! this fallback - they delegate straight to the core `Model` methods,
//! which correctly reject an unknown/removed id on their own, and
//! nothing requires a removed asset to support further mutation. See
//! PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 2 status for the full
//! rationale (this resolves what was previously an open gap there).

use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use pyo3::basic::CompareOp;
use pyo3::exceptions::PyLookupError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PySet};
use pyo3::IntoPyObjectExt;

use maltoolbox_language::graph::LanguageGraph;
use maltoolbox_language_py::handle::composite_hash;
use maltoolbox_language_py::PyLanguageGraphAsset;
use maltoolbox_model::{Model, ModelAsset};

use crate::exceptions::model_error_to_py;

/// Read-only record of each removed asset's final state, shared between
/// a `PyModel` and every `PyModelAsset` handle it ever hands out - see
/// `PyModel::tombstones`'s doc comment.
pub type Tombstones = Rc<RefCell<HashMap<i64, ModelAsset>>>;

/// Extracts `.id` from every `ModelAsset` in an arbitrary Python
/// iterable (`set`/`list`/etc.) - `Vec<PyRef<PyModelAsset>>` only
/// accepts `Sequence`s, not sets, and Python's real
/// `add_associated_assets`/`remove_associated_assets`/
/// `validate_associated_assets` are called with `set[ModelAsset]`
/// almost everywhere.
fn ids_of(obj: &Bound<'_, PyAny>) -> PyResult<std::collections::HashSet<i64>> {
    obj.try_iter()?
        .map(|item| Ok(item?.extract::<PyRef<'_, PyModelAsset>>()?.id))
        .collect()
}

#[pyclass(name = "ModelAsset", unsendable, skip_from_py_object)]
#[derive(Clone)]
pub struct PyModelAsset {
    pub owner: Rc<RefCell<Model>>,
    pub id: i64,
    /// The owning `PyModel`'s language graph, shared (same `Rc`) so
    /// `.lg_asset` handles compare equal via the usual owner-pointer
    /// scheme - see `model.rs` for why this can't just be derived from
    /// `owner.borrow().lang_graph` (that's a bare `Rc<LanguageGraph>`,
    /// not `Rc<RefCell<LanguageGraph>>`).
    pub lang_graph: Rc<RefCell<LanguageGraph>>,
    pub tombstones: Tombstones,
}

impl PyModelAsset {
    pub fn new(owner: Rc<RefCell<Model>>, id: i64, lang_graph: Rc<RefCell<LanguageGraph>>, tombstones: Tombstones) -> Self {
        PyModelAsset {
            owner,
            id,
            lang_graph,
            tombstones,
        }
    }

    fn owner_ptr(&self) -> usize {
        Rc::as_ptr(&self.owner) as usize
    }

    fn not_found(&self) -> PyErr {
        PyLookupError::new_err(format!(
            "Asset with id {} not found in model (never added, or removed and no \
             tombstone recorded? this shouldn't happen for an id reached via a \
             real PyModelAsset handle).",
            self.id
        ))
    }

    /// Resolves `self` to its backing data - the live entry in
    /// `owner.assets` if still present, else the `Tombstones` fallback
    /// recorded at removal time - and runs `f` against it. This is the
    /// one place "where does this handle's data live right now" is
    /// decided; every read-only getter below goes through it so the
    /// post-removal-readability fallback applies uniformly.
    fn with_asset<R>(&self, f: impl FnOnce(&ModelAsset) -> PyResult<R>) -> PyResult<R> {
        let model = self.owner.borrow();
        if let Some(asset) = model.assets.get(&self.id) {
            return f(asset);
        }
        drop(model);
        let tombstones = self.tombstones.borrow();
        if let Some(asset) = tombstones.get(&self.id) {
            return f(asset);
        }
        Err(self.not_found())
    }
}

#[pymethods]
impl PyModelAsset {
    #[getter]
    fn name(&self) -> PyResult<String> {
        self.with_asset(|asset| Ok(asset.name.clone()))
    }

    #[getter]
    fn id(&self) -> i64 {
        self.id
    }

    #[getter(r#type)]
    fn asset_type(&self) -> PyResult<String> {
        self.with_asset(|asset| Ok(asset.asset_type.clone()))
    }

    #[getter]
    fn lg_asset(&self) -> PyResult<PyLanguageGraphAsset> {
        self.with_asset(|asset| Ok(PyLanguageGraphAsset::new(self.lang_graph.clone(), asset.lg_asset)))
    }

    #[getter]
    fn defenses<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        self.with_asset(|asset| {
            let dict = PyDict::new(py);
            for (k, v) in &asset.defenses {
                dict.set_item(k, v)?;
            }
            Ok(dict)
        })
    }

    #[getter]
    fn extras<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.with_asset(|asset| {
            pythonize::pythonize(py, &serde_json::Value::Object(asset.extras.clone()))
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
        })
    }

    /// `dict[str, set[ModelAsset]]`, matching the Python `@property
    /// associated_assets`. Rebuilt fresh per access, not cached - same
    /// convention as every other mapping-shaped attribute in this
    /// layer. For a tombstoned (removed) asset, `final_state
    /// .associated_assets` was captured *after* `remove_asset`'s own
    /// cleanup already emptied it, so this correctly yields `{}` rather
    /// than the pre-removal associations.
    #[getter]
    fn associated_assets<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        self.with_asset(|asset| {
            let dict = PyDict::new(py);
            for (fieldname, ids) in &asset.associated_assets {
                let set = PySet::empty(py)?;
                for &other_id in ids {
                    set.add(PyModelAsset::new(
                        self.owner.clone(),
                        other_id,
                        self.lang_graph.clone(),
                        self.tombstones.clone(),
                    ))?;
                }
                dict.set_item(fieldname, set)?;
            }
            Ok(dict)
        })
    }

    fn associations_with(&self, other: &PyModelAsset) -> PyResult<Vec<maltoolbox_language_py::PyLanguageGraphAssociation>> {
        let model = self.owner.borrow();
        let assocs = model.associations_with(self.id, other.id);
        Ok(assocs
            .into_iter()
            .map(|a| maltoolbox_language_py::PyLanguageGraphAssociation::new(self.lang_graph.clone(), a))
            .collect())
    }

    fn has_association_with(&self, other: &PyModelAsset, assoc_name: &str) -> bool {
        let model = self.owner.borrow();
        model.has_association_with(self.id, other.id, assoc_name)
    }

    fn validate_associated_assets(&self, fieldname: &str, assets_to_add: &Bound<'_, PyAny>) -> PyResult<()> {
        let model = self.owner.borrow();
        let ids = ids_of(assets_to_add)?;
        model
            .validate_associated_assets(self.id, fieldname, &ids)
            .map_err(model_error_to_py)
    }

    fn add_associated_assets(&self, fieldname: &str, assets: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut model = self.owner.borrow_mut();
        let ids = ids_of(assets)?;
        model
            .add_associated_assets(self.id, fieldname, ids)
            .map_err(model_error_to_py)
    }

    fn remove_associated_assets(&self, fieldname: &str, assets: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut model = self.owner.borrow_mut();
        let ids = ids_of(assets)?;
        model
            .remove_associated_assets(self.id, fieldname, &ids)
            .map_err(model_error_to_py)
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self._to_dict(py)
    }

    fn _to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        // `associated_assets` needs id->name resolution against the
        // live model, same as the core crate's own `Model::to_dict` -
        // only meaningful in the live-asset branch, since a tombstoned
        // asset's `associated_assets` is already empty (captured after
        // `remove_asset`'s own cleanup ran).
        let model = self.owner.borrow();
        let dict = if let Some(asset) = model.assets.get(&self.id) {
            let mut dict = asset.to_dict();
            let mut associated = serde_json::Map::new();
            for (fieldname, ids) in &asset.associated_assets {
                let mut named = serde_json::Map::new();
                for other_id in ids {
                    if let Some(other) = model.assets.get(other_id) {
                        named.insert(other_id.to_string(), serde_json::json!(other.name));
                    }
                }
                associated.insert(fieldname.clone(), serde_json::Value::Object(named));
            }
            dict["associated_assets"] = serde_json::Value::Object(associated);
            dict
        } else {
            let tombstones = self.tombstones.borrow();
            let asset = tombstones.get(&self.id).ok_or_else(|| self.not_found())?;
            asset.to_dict()
        };
        pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self) -> PyResult<String> {
        self.with_asset(|asset| {
            Ok(format!(
                "ModelAsset(name: \"{}\", id: {}, type: {})",
                asset.name, asset.id, asset.asset_type
            ))
        })
    }

    fn __hash__(&self) -> isize {
        composite_hash(self.owner_ptr(), self.id)
    }

    fn __richcmp__(&self, other: &PyModelAsset, op: CompareOp, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let eq = self.owner_ptr() == other.owner_ptr() && self.id == other.id;
        match op {
            CompareOp::Eq => eq.into_py_any(py),
            CompareOp::Ne => (!eq).into_py_any(py),
            _ => Ok(py.NotImplemented()),
        }
    }
}

impl PartialEq for PyModelAsset {
    fn eq(&self, other: &Self) -> bool {
        self.owner_ptr() == other.owner_ptr() && self.id == other.id
    }
}
impl Eq for PyModelAsset {}
impl std::hash::Hash for PyModelAsset {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.owner_ptr().hash(state);
        self.id.hash(state);
    }
}
