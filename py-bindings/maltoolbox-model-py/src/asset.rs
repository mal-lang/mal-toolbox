//! Mirrors `maltoolbox/model.py`'s `ModelAsset`. A handle (`owner` +
//! `i64` id), cached per-owner (`handle_cache`) so repeated lookups for
//! the same id return the identical Python object, same scheme as
//! `PyLanguageGraphAsset`/`PyLanguageGraphAttackStep`. No `#[new]`: the
//! real Python `ModelAsset.__init__` takes no `Model` argument at all
//! (fully detached construction), which is incompatible with this
//! handle design. `ModelAsset` is only ever handed out by `PyModel`.
//!
//! **Post-removal readability**: a handle whose `id` has been removed
//! from `owner.assets` (via `Model.remove_asset`) falls back to
//! `owner`'s `Tombstones` map (populated by `PyModel::remove_asset` from
//! `AssetSnapshot::final_state`) for every *read-only* getter, matching
//! the real Python `ModelAsset` object staying fully readable after
//! removal. Mutating methods (`add_associated_assets`/
//! `remove_associated_assets`/`validate_associated_assets`) do *not* get
//! this fallback - they delegate straight to the core `Model` methods,
//! which correctly reject an unknown/removed id on their own.

use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use pyo3::basic::CompareOp;
use pyo3::exceptions::PyLookupError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PySet};
use pyo3::IntoPyObjectExt;

use maltoolbox_language::graph::LanguageGraph;
use maltoolbox_language_py::handle::{
    cached_handle, composite_hash, HandleCache, SharedLangGraphCaches,
};
use maltoolbox_language_py::PyLanguageGraphAsset;

/// `{fieldname: {other_asset_id: other_asset_name}}`'s inner keys are
/// *integers* in the Python original, but the core's own `to_dict()`
/// can only produce `serde_json::Map` (string keys only, a JSON
/// limitation) - `pythonize` therefore hands back `{"0": "App1"}`
/// instead of `{0: "App1"}` unless corrected here, after pythonizing, by
/// rebuilding each inner dict with parsed-back-to-int keys. Shared by
/// `PyModelAsset::_to_dict` and `PyModel::to_dict`.
pub fn fix_associated_assets_int_keys(
    py: Python<'_>,
    asset_dict: &Bound<'_, PyDict>,
) -> PyResult<()> {
    let Some(associated) = asset_dict.get_item("associated_assets")? else {
        return Ok(());
    };
    let associated = associated.cast::<PyDict>()?;
    for (fieldname, sub_dict) in associated.iter() {
        let sub_dict = sub_dict.cast::<PyDict>()?;
        let fixed = PyDict::new(py);
        for (key, value) in sub_dict.iter() {
            let id: i64 = key.extract::<String>()?.parse().map_err(|_| {
                pyo3::exceptions::PyValueError::new_err("non-integer key in associated_assets")
            })?;
            fixed.set_item(id, value)?;
        }
        associated.set_item(fieldname, fixed)?;
    }
    Ok(())
}
use maltoolbox_model::{Model, ModelAsset};

use crate::exceptions::model_error_to_py;

/// Read-only record of each removed asset's final state, shared between
/// a `PyModel` and every `PyModelAsset` handle it ever hands out - see
/// `PyModel::tombstones`'s doc comment.
pub type Tombstones = Rc<RefCell<HashMap<i64, ModelAsset>>>;

/// Extracts `.id` from every `ModelAsset` in an arbitrary Python
/// iterable (`set`/`list`/etc.), since `Vec<PyRef<PyModelAsset>>` only
/// accepts `Sequence`s, not sets, and Python callers pass
/// `set[ModelAsset]` almost everywhere.
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
    /// The owning `PyModel`'s `PyLanguageGraph.caches`, needed so
    /// `.lg_asset` resolves to the same per-owner-cached
    /// `PyLanguageGraphAsset` handle as every other path to it.
    pub lang_caches: SharedLangGraphCaches,
    pub tombstones: Tombstones,
    /// This type's own per-owner handle cache, shared (same `Rc`) with
    /// `PyModel` and every sibling `PyModelAsset` handle, so e.g.
    /// `model.assets[id]` and `asset.associated_assets['field']`'s
    /// members return the identical Python object for the same id.
    pub handle_cache: HandleCache<i64, PyModelAsset>,
}

impl PyModelAsset {
    pub fn new(
        owner: Rc<RefCell<Model>>,
        id: i64,
        lang_graph: Rc<RefCell<LanguageGraph>>,
        lang_caches: SharedLangGraphCaches,
        tombstones: Tombstones,
        handle_cache: HandleCache<i64, PyModelAsset>,
    ) -> Self {
        PyModelAsset {
            owner,
            id,
            lang_graph,
            lang_caches,
            tombstones,
            handle_cache,
        }
    }

    fn owner_ptr(&self) -> usize {
        Rc::as_ptr(&self.owner) as usize
    }

    /// Cache-aware constructor for a sibling `ModelAsset` handle owned by
    /// the same `Model`.
    fn asset_handle(&self, py: Python<'_>, id: i64) -> PyResult<Py<PyModelAsset>> {
        let owner = self.owner.clone();
        let lang_graph = self.lang_graph.clone();
        let lang_caches = self.lang_caches.clone();
        let tombstones = self.tombstones.clone();
        let handle_cache = self.handle_cache.clone();
        cached_handle(&self.handle_cache, py, id, move || {
            PyModelAsset::new(owner, id, lang_graph, lang_caches, tombstones, handle_cache)
        })
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
    fn lg_asset(&self, py: Python<'_>) -> PyResult<Py<PyLanguageGraphAsset>> {
        let lg_id = self.with_asset(|asset| Ok(asset.lg_asset))?;
        let owner = self.lang_graph.clone();
        let caches = self.lang_caches.clone();
        cached_handle(&self.lang_caches.assets, py, lg_id, move || {
            PyLanguageGraphAsset::new(owner, lg_id, caches)
        })
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

    /// Plain mutable attribute in the Python original
    /// (`self.extras: dict = {}`, freely reassignable). Live-only, no
    /// tombstone fallback - same as every other mutating method on this
    /// type.
    #[setter]
    fn set_extras(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let parsed: serde_json::Value = pythonize::depythonize(value)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let extras = parsed.as_object().cloned().unwrap_or_default();
        let mut model = self.owner.borrow_mut();
        let asset = model
            .assets
            .get_mut(&self.id)
            .ok_or_else(|| self.not_found())?;
        asset.extras = extras;
        Ok(())
    }

    /// `dict[str, set[ModelAsset]]`, matching the Python `@property
    /// associated_assets`. Rebuilt fresh per access, not cached. For a
    /// tombstoned (removed) asset, `final_state.associated_assets` was
    /// captured *after* `remove_asset`'s own cleanup already emptied it,
    /// so this correctly yields `{}` rather than the pre-removal
    /// associations.
    #[getter]
    fn associated_assets<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        self.with_asset(|asset| {
            let dict = PyDict::new(py);
            for (fieldname, ids) in &asset.associated_assets {
                let set = PySet::empty(py)?;
                for &other_id in ids {
                    set.add(self.asset_handle(py, other_id)?)?;
                }
                dict.set_item(fieldname, set)?;
            }
            Ok(dict)
        })
    }

    fn associations_with(
        &self,
        py: Python<'_>,
        other: &PyModelAsset,
    ) -> PyResult<Vec<Py<maltoolbox_language_py::PyLanguageGraphAssociation>>> {
        let model = self.owner.borrow();
        let assocs = model.associations_with(self.id, other.id);
        assocs
            .into_iter()
            .map(|a| {
                Py::new(
                    py,
                    maltoolbox_language_py::PyLanguageGraphAssociation::new(
                        self.lang_graph.clone(),
                        a,
                        self.lang_caches.clone(),
                    ),
                )
            })
            .collect()
    }

    fn has_association_with(&self, other: &PyModelAsset, assoc_name: &str) -> bool {
        let model = self.owner.borrow();
        model.has_association_with(self.id, other.id, assoc_name)
    }

    fn validate_associated_assets(
        &self,
        fieldname: &str,
        assets_to_add: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
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

    /// Matches the Python original's `ModelAsset._to_dict()` exactly:
    /// returns `{self.id: {name, type, ...}}`, a single-key dict keyed
    /// by this asset's own id, *not* just the inner field dict. The
    /// core's own `ModelAsset::to_dict()` deliberately returns the
    /// unwrapped inner dict (`Model::to_dict` wraps it per-asset
    /// itself), so this id-wrapping step belongs here, not in the core.
    fn _to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        // `associated_assets` needs id->name resolution against the
        // live model; only meaningful in the live-asset branch, since a
        // tombstoned asset's `associated_assets` is already empty.
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
        // Built as a real `PyDict` with an *integer* key, not via
        // `pythonize` on a `serde_json::Map`: JSON objects only support
        // string keys, which would silently turn `self.id` into `"0"`.
        let inner = pythonize::pythonize(py, &dict)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let inner = inner.cast::<PyDict>()?;
        fix_associated_assets_int_keys(py, inner)?;
        let wrapped = PyDict::new(py);
        wrapped.set_item(self.id, inner)?;
        Ok(wrapped.into_any())
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

    fn __richcmp__(
        &self,
        other: &PyModelAsset,
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
