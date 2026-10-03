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
use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::types::PyDict;

use maltoolbox_language_py::PyLanguageGraph;
use maltoolbox_model::{file as model_file, Model, ModelAsset};

use crate::asset::{PyModelAsset, Tombstones};
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
        })
    }

    fn asset_handle(&self, py: Python<'_>, id: i64) -> PyModelAsset {
        PyModelAsset::new(
            self.inner.clone(),
            id,
            Self::lang_graph_rc(py, &self.lang_graph_py),
            self.tombstones.clone(),
        )
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
        if let Some(v) = mt_version {
            model.maltoolbox_version = v;
        }
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
        let model = self.inner.borrow();
        let dict = PyDict::new(py);
        for &id in &model.asset_order {
            dict.set_item(id, self.asset_handle(py, id))?;
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
    ) -> PyResult<PyModelAsset> {
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
        Ok(self.asset_handle(py, id))
    }

    fn remove_asset(&self, asset: &PyModelAsset) -> PyResult<()> {
        let snapshot = {
            let mut model = self.inner.borrow_mut();
            model.remove_asset(asset.id).map_err(model_error_to_py)?
        };
        self.tombstones.borrow_mut().insert(asset.id, snapshot.final_state);
        Ok(())
    }

    fn get_asset_by_id(&self, py: Python<'_>, asset_id: i64) -> Option<PyModelAsset> {
        let model = self.inner.borrow();
        model.get_asset_by_id(asset_id).map(|_| self.asset_handle(py, asset_id))
    }

    fn get_asset_by_name(&self, py: Python<'_>, asset_name: &str) -> Option<PyModelAsset> {
        let model = self.inner.borrow();
        model.get_asset_by_name(asset_name).map(|a| self.asset_handle(py, a.id))
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let model = self.inner.borrow();
        let dict = model.to_dict();
        pythonize::pythonize(py, &dict).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    fn _to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.to_dict(py)
    }

    fn save_to_file(&self, filename: &str) -> PyResult<()> {
        let model = self.inner.borrow();
        model_file::save_to_file(&model, filename)
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))
    }

    #[staticmethod]
    pub fn load_from_file(py: Python<'_>, filename: &str, lang_graph: Py<PyLanguageGraph>) -> PyResult<Self> {
        let lg_rc = Self::lang_graph_rc(py, &lang_graph);
        let cloned_graph = lg_rc.borrow().clone();
        let model = model_file::load_from_file(filename, Rc::new(cloned_graph)).map_err(load_error_to_py)?;
        Self::wrap(py, model, lang_graph)
    }

    /// Classmethod in the Python original (`cls._from_dict`); no
    /// try/except there (unlike `load_from_file`) - raw errors
    /// propagate, see `exceptions::from_dict_error_to_py`.
    #[staticmethod]
    #[pyo3(name = "_from_dict")]
    fn from_dict_py<'py>(py: Python<'py>, serialized: &Bound<'py, PyAny>, lang_graph: Py<PyLanguageGraph>) -> PyResult<Self> {
        let value: serde_json::Value = pythonize::depythonize(serialized)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let lg_rc = Self::lang_graph_rc(py, &lang_graph);
        let cloned_graph = lg_rc.borrow().clone();
        let model = model_file::from_dict(&value, Rc::new(cloned_graph)).map_err(from_dict_error_to_py)?;
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
