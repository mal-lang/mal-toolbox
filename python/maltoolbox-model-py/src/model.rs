//! Mirrors `maltoolbox/model.py`'s `Model`. The one "container" type in
//! this crate - see PYTHON_BINDINGS_IMPLEMENTATION.md's "Container /
//! handle pattern".
//!
//! Holds both `inner` (the core `maltoolbox_model::Model`, which needs
//! a bare `Rc<LanguageGraph>` with no `RefCell`) and `lang_graph_py`
//! (the actual `Py<PyLanguageGraph>` object passed to the constructor,
//! stored so `.lang_graph` returns the same Python object every time,
//! per Phase 2 decision 4. Building `inner` requires cloning the
//! `LanguageGraph` data out of `lang_graph_py`'s `Rc<RefCell<_>>` once
//! at construction time, since the two Rc flavors can't otherwise
//! compose; see `crates/maltoolbox-language/src/graph/mod.rs`'s
//! `Clone` doc comment on `LanguageGraph` for the full rationale and
//! the narrow, confirmed-unused-in-practice divergence this introduces
//! around `regenerate_graph`.

use std::cell::RefCell;
use std::collections::HashMap;
use std::path::PathBuf;
use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::types::PyDict;

use maltoolbox_language_py::handle::{cached_handle, new_handle_cache, HandleCache};
use maltoolbox_language_py::PyLanguageGraph;
use maltoolbox_model::{file as model_file, Model, ModelAsset};

use crate::asset::{fix_associated_assets_int_keys, PyModelAsset, Tombstones};
use crate::exceptions::{from_dict_error_to_py, load_error_to_py, model_error_to_py};

#[pyclass(name = "Model", module = "maltoolbox._native", unsendable)]
pub struct PyModel {
    pub inner: Rc<RefCell<Model>>,
    pub lang_graph_py: Py<PyLanguageGraph>,
    /// Read-only record of each removed asset's final state (post
    /// `remove_asset` cleanup), keyed by id - lets a `PyModelAsset`
    /// handle whose entry is gone from `inner.assets` keep resolving
    /// its own attributes, matching Python's `ModelAsset` objects
    /// staying fully readable after removal. See
    /// `AssetSnapshot::final_state` (`maltoolbox-model`) and
    /// PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 2 status for the full
    /// rationale.
    pub tombstones: Tombstones,
    /// Per-owner `PyModelAsset` handle cache (Phase 4 decision 1) -
    /// shared (same `Rc`) with every `PyModelAsset` this model ever
    /// hands out, so repeated lookups for the same id return the
    /// identical Python object.
    pub handle_cache: HandleCache<i64, PyModelAsset>,
}

impl PyModel {
    fn lang_graph_rc(py: Python<'_>, lang_graph_py: &Py<PyLanguageGraph>) -> Rc<RefCell<maltoolbox_language::graph::LanguageGraph>> {
        lang_graph_py.borrow(py).inner.clone()
    }

    fn wrap(py: Python<'_>, inner: Model, lang_graph_py: Py<PyLanguageGraph>) -> PyResult<Self> {
        let _ = py;
        Ok(PyModel {
            inner: Rc::new(RefCell::new(inner)),
            lang_graph_py,
            tombstones: Rc::new(RefCell::new(HashMap::<i64, ModelAsset>::new())),
            handle_cache: new_handle_cache(),
        })
    }

    /// `pub` so cross-crate consumers (e.g. `maltoolbox-attackgraph-py`'s
    /// `PyAttackGraphNode::model_asset`) can build a cache-consistent
    /// `PyModelAsset` handle too, rather than constructing one directly
    /// and bypassing this model's cache (Phase 4 decision 1).
    pub fn asset_handle(&self, py: Python<'_>, id: i64) -> PyResult<Py<PyModelAsset>> {
        let owner = self.inner.clone();
        let lang_graph = Self::lang_graph_rc(py, &self.lang_graph_py);
        let lang_caches = self.lang_graph_py.borrow(py).caches.clone();
        let tombstones = self.tombstones.clone();
        let handle_cache = self.handle_cache.clone();
        cached_handle(&self.handle_cache, py, id, move || {
            PyModelAsset::new(owner, id, lang_graph, lang_caches, tombstones, handle_cache)
        })
    }

    /// Evicts `id`'s cache entry, if any - used only by `add_asset` when
    /// the newly-assigned id happens to collide with a *previously
    /// removed* asset's id (the core's `add_asset` allows this: an
    /// explicit `asset_id=` matching a removed id is not currently
    /// occupied, so it succeeds and creates a genuinely new, unrelated
    /// asset at that id). Without this, `asset_handle` would return the
    /// stale cached object for the *old* (now-removed, tombstoned) asset
    /// instead of building a fresh one for the new asset that now
    /// legitimately owns that id - Python has no such hazard (a plain
    /// `self.assets[asset_id] = ModelAsset(...)` always creates a new
    /// object), so this is a correctness fix, not an optimization.
    /// Deliberately *not* done on removal itself - see Phase 4 decision
    /// 1's "don't evict on removal" guidance; eviction only happens here,
    /// at the one point a genuinely new logical object is introduced at
    /// a given id.
    fn evict_handle(&self, id: i64) {
        self.handle_cache.borrow_mut().remove(&id);
    }

    /// Default `maltoolbox_version` should be the *live Python package's*
    /// `maltoolbox.__version__`, not the Rust crate's own internal
    /// `Cargo.toml` version (`maltoolbox_model::MALTOOLBOX_VERSION`,
    /// "0.1.0" today) - the two are unrelated numbers (one tracks this
    /// standalone Rust crate's own releases, the other the Python
    /// package's), and before this fix, every model constructed/loaded
    /// without an explicit version ended up stamped with the former,
    /// which is meaningless to anyone looking at `"MAL-Toolbox Version"`
    /// metadata. Confirmed to matter for real, not just cosmetic:
    /// `tests/translators/test_updater.py` compares an old model
    /// (converted with no recorded version, so it takes this default)
    /// against a freshly-loaded model with an explicit version in its
    /// file - this only matched in the pure-Python original because of
    /// the *separate*, already-documented `to_dict()` bug (ignores
    /// `self.maltoolbox_version`, always writes the live version
    /// instead) masking the comparison; this port's `to_dict()`
    /// correctly uses `self.maltoolbox_version` (PORTING_NOTES.md §3),
    /// which exposes the mismatch for the first time now.
    fn live_version(py: Python<'_>) -> PyResult<String> {
        py.import("maltoolbox")?.getattr("__version__")?.extract()
    }

    /// See `from_dict_py`'s doc comment: the Python original tolerates
    /// *any* key type anywhere in the input dict (plain Python dict
    /// iteration doesn't care), but `pythonize::depythonize` requires
    /// `serde_json::Value`-compatible input, which can only represent
    /// string-keyed maps. Rather than chase every individual place an
    /// int key might appear (confirmed via direct reproduction to be
    /// more than just `assets` - `attackers`/`attackers[*].entry_points`
    /// are int-keyed too, in the exact fixtures
    /// `tests/translators/test_updater.py` loads, and there is no
    /// principled reason to assume that list is exhaustive across every
    /// old model-version shape), this recursively rebuilds the *entire*
    /// structure with every dict key run through `.str()`, leaving
    /// values (and list contents) otherwise untouched. Always returns a
    /// new object - doesn't mutate `value` in place.
    fn stringify_all_keys<'py>(py: Python<'py>, value: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        if let Ok(dict) = value.cast::<PyDict>() {
            let fixed = PyDict::new(py);
            for (key, val) in dict.iter() {
                fixed.set_item(key.str()?, Self::stringify_all_keys(py, &val)?)?;
            }
            return Ok(fixed.into_any());
        }
        if let Ok(list) = value.cast::<pyo3::types::PyList>() {
            let fixed = pyo3::types::PyList::empty(py);
            for item in list.iter() {
                fixed.append(Self::stringify_all_keys(py, &item)?)?;
            }
            return Ok(fixed.into_any());
        }
        Ok(value.clone())
    }
}

#[pymethods]
impl PyModel {
    #[new]
    #[pyo3(signature = (name, lang_graph, mt_version=None))]
    fn new(py: Python<'_>, name: String, lang_graph: Py<PyLanguageGraph>, mt_version: Option<String>) -> PyResult<Self> {
        let lg_rc = Self::lang_graph_rc(py, &lang_graph);
        let cloned_graph = lg_rc.borrow().clone();
        let mut model = Model::new(name, Rc::new(cloned_graph));
        model.maltoolbox_version = match mt_version {
            Some(v) => v,
            None => Self::live_version(py)?,
        };
        Self::wrap(py, model, lang_graph)
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.borrow().name.clone()
    }

    #[setter]
    fn set_name(&self, name: String) {
        self.inner.borrow_mut().name = name;
    }

    #[getter]
    fn lang_graph(&self, py: Python<'_>) -> Py<PyLanguageGraph> {
        self.lang_graph_py.clone_ref(py)
    }

    #[getter]
    fn maltoolbox_version(&self) -> String {
        self.inner.borrow().maltoolbox_version.clone()
    }

    #[getter]
    fn next_id(&self) -> i64 {
        self.inner.borrow().next_id
    }

    #[setter]
    fn set_next_id(&self, value: i64) {
        self.inner.borrow_mut().next_id = value;
    }

    /// `dict[int, ModelAsset]`, matching Python's `.assets` exactly
    /// (keyed by id, not name - `._name_to_asset` is the name-keyed
    /// optimization, exposed here via `get_asset_by_name`). Rebuilt
    /// fresh per access, not cached - same convention as every other
    /// mapping-shaped attribute in this layer.
    #[getter]
    fn assets<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let ids: Vec<i64> = self.inner.borrow().asset_order.clone();
        let dict = PyDict::new(py);
        for id in ids {
            dict.set_item(id, self.asset_handle(py, id)?)?;
        }
        Ok(dict)
    }

    #[pyo3(signature = (asset_type, name=None, asset_id=None, defenses=None, extras=None, allow_duplicate_names=true))]
    #[allow(clippy::too_many_arguments)]
    fn add_asset(
        &self,
        py: Python<'_>,
        asset_type: &str,
        name: Option<String>,
        asset_id: Option<i64>,
        defenses: Option<std::collections::HashMap<String, f64>>,
        extras: Option<&Bound<'_, PyAny>>,
        allow_duplicate_names: bool,
    ) -> PyResult<Py<PyModelAsset>> {
        let extras_map = extras
            .map(|e| -> PyResult<serde_json::Map<String, serde_json::Value>> {
                let value: serde_json::Value =
                    pythonize::depythonize(e).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
                Ok(value.as_object().cloned().unwrap_or_default())
            })
            .transpose()?;
        let id = {
            let mut model = self.inner.borrow_mut();
            model
                .add_asset(asset_type, name, asset_id, defenses, extras_map, allow_duplicate_names)
                .map_err(model_error_to_py)?
        };
        // See `evict_handle`'s doc comment: a caller-chosen `asset_id`
        // can legitimately collide with a previously-removed asset's id.
        self.evict_handle(id);
        self.asset_handle(py, id)
    }

    fn remove_asset(&self, asset: &PyModelAsset) -> PyResult<()> {
        let snapshot = {
            let mut model = self.inner.borrow_mut();
            model.remove_asset(asset.id).map_err(model_error_to_py)?
        };
        self.tombstones.borrow_mut().insert(asset.id, snapshot.final_state);
        Ok(())
    }

    fn get_asset_by_id(&self, py: Python<'_>, asset_id: i64) -> PyResult<Option<Py<PyModelAsset>>> {
        let present = self.inner.borrow().get_asset_by_id(asset_id).is_some();
        if present {
            Ok(Some(self.asset_handle(py, asset_id)?))
        } else {
            Ok(None)
        }
    }

    fn get_asset_by_name(&self, py: Python<'_>, asset_name: &str) -> PyResult<Option<Py<PyModelAsset>>> {
        let id = self.inner.borrow().get_asset_by_name(asset_name).map(|a| a.id);
        match id {
            Some(id) => Ok(Some(self.asset_handle(py, id)?)),
            None => Ok(None),
        }
    }

    /// `contents['assets']` is keyed by *integer* asset id in the Python
    /// original (`contents['assets'].update(asset._to_dict())`, and each
    /// asset's own `_to_dict()` returns `{self.id: ...}` with an int
    /// key) - the core's `to_dict()` can only produce `serde_json::Map`
    /// (string keys only), so both the outer `assets` dict's keys and
    /// each asset's nested `associated_assets` keys need fixing up after
    /// pythonizing. See `fix_associated_assets_int_keys`'s doc comment
    /// for why Phase 2's own oracle diff never caught this.
    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let model = self.inner.borrow();
        let dict = model.to_dict();
        let pythonized = pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let pythonized = pythonized.cast::<PyDict>()?;
        if let Some(assets) = pythonized.get_item("assets")? {
            let assets = assets.cast::<PyDict>()?;
            let fixed_assets = PyDict::new(py);
            for (str_id, asset_dict) in assets.iter() {
                let id: i64 = str_id.extract::<String>()?.parse().map_err(|_| {
                    pyo3::exceptions::PyValueError::new_err("non-integer asset id key")
                })?;
                let asset_dict = asset_dict.cast::<PyDict>()?;
                fix_associated_assets_int_keys(py, asset_dict)?;
                fixed_assets.set_item(id, asset_dict)?;
            }
            pythonized.set_item("assets", fixed_assets)?;
        }
        Ok(pythonized.clone().into_any())
    }

    fn _to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.to_dict(py)
    }

    /// `PathBuf`, not `&str` - pyo3 extracts it from both a plain `str`
    /// and any `os.PathLike` (e.g. `pathlib.Path`), matching the Python
    /// original's file APIs (see `maltoolbox-language-py`'s identical
    /// fix for the same reason).
    fn save_to_file(&self, filename: PathBuf) -> PyResult<()> {
        let model = self.inner.borrow();
        model_file::save_to_file(&model, filename)
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))
    }

    #[staticmethod]
    pub fn load_from_file(py: Python<'_>, filename: PathBuf, lang_graph: Py<PyLanguageGraph>) -> PyResult<Self> {
        let lg_rc = Self::lang_graph_rc(py, &lang_graph);
        let cloned_graph = lg_rc.borrow().clone();
        let mut model = model_file::load_from_file(filename, Rc::new(cloned_graph)).map_err(load_error_to_py)?;
        if model.maltoolbox_version == maltoolbox_model::MALTOOLBOX_VERSION {
            model.maltoolbox_version = Self::live_version(py)?;
        }
        Self::wrap(py, model, lang_graph)
    }

    /// Classmethod in the Python original (`cls._from_dict`); no
    /// try/except there (unlike `load_from_file`) - raw errors
    /// propagate, see `exceptions::from_dict_error_to_py`.
    ///
    /// The Python original's `assets.items()`-based loop tolerates
    /// *either* a `str` or an `int` key for each asset (it always does
    /// `int(asset_id)` itself) - confirmed load-bearing by
    /// `tests/translators/test_updater.py`: the old-version model YAML
    /// fixtures it loads use bare (unquoted) integer keys, which
    /// `yaml.safe_load` parses as real Python `int`s, not `str`s (unlike
    /// JSON, which has no unquoted-key syntax). `pythonize::depythonize`
    /// requires `serde_json::Value`-compatible input, which can only
    /// represent string-keyed maps - stringify `serialized['assets']`'s
    /// keys first (on a shallow copy, not mutating the caller's dict) so
    /// an int-keyed `assets` dict depythonizes successfully either way.
    #[staticmethod]
    #[pyo3(name = "_from_dict")]
    fn from_dict_py<'py>(py: Python<'py>, serialized: &Bound<'py, PyAny>, lang_graph: Py<PyLanguageGraph>) -> PyResult<Self> {
        let serialized = Self::stringify_all_keys(py, serialized)?;
        let value: serde_json::Value = pythonize::depythonize(&serialized)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let lg_rc = Self::lang_graph_rc(py, &lang_graph);
        let cloned_graph = lg_rc.borrow().clone();
        let mut model = model_file::from_dict(&value, Rc::new(cloned_graph)).map_err(from_dict_error_to_py)?;
        if model.maltoolbox_version == maltoolbox_model::MALTOOLBOX_VERSION {
            model.maltoolbox_version = Self::live_version(py)?;
        }
        Self::wrap(py, model, lang_graph)
    }

    /// Pickling (Phase 3 decision 4, deferred from Phase 2): reconstructs
    /// the nested `lang_graph` from its own pickled dict state first (via
    /// `LanguageGraph._from_pickle_state`), then rebuilds `self` from
    /// `_from_dict` the normal way - so a pickled `Model` never needs the
    /// original `LanguageGraph` Python object to still be around.
    #[staticmethod]
    fn _from_pickle_state(py: Python<'_>, state: &Bound<'_, PyAny>, lang_graph_state: &Bound<'_, PyAny>) -> PyResult<Self> {
        let lg_cls = py.import("maltoolbox._native")?.getattr("LanguageGraph")?;
        let lang_graph_obj = lg_cls.call_method1("_from_pickle_state", (lang_graph_state,))?;
        let lang_graph_py: Py<PyLanguageGraph> = lang_graph_obj.extract()?;
        Self::from_dict_py(py, state, lang_graph_py)
    }

    #[allow(clippy::type_complexity)]
    fn __reduce__<'py>(&self, py: Python<'py>) -> PyResult<(Bound<'py, PyAny>, (Bound<'py, PyAny>, Bound<'py, PyAny>))> {
        let cls = py.get_type::<PyModel>();
        let func = cls.getattr("_from_pickle_state")?;
        let lang_graph_state = self.lang_graph_py.bind(py).call_method0("_to_dict")?;
        let model_state = self._to_dict(py)?;
        Ok((func, (model_state, lang_graph_state)))
    }

    fn __repr__(&self, py: Python<'_>) -> String {
        let lg = self.lang_graph_py.borrow(py);
        let graph = lg.inner.borrow();
        format!(
            "Model(name: \"{}\", language: LanguageGraph(id: \"{}\", version: \"{}\"))",
            self.name(),
            graph.metadata.id,
            graph.metadata.version
        )
    }
}
