//! Mirrors `maltoolbox/language/languagegraph.py`'s `LanguageGraph`.
//! The one "container" type in this crate - see
//! PYTHON_BINDINGS_IMPLEMENTATION.md's "Container / handle pattern".

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PySet, PyTuple};

use maltoolbox_language::graph::file as lang_file;
use maltoolbox_language::graph::file::language_graph_from_dict;
use maltoolbox_language::graph::{language_graph_to_dict, LanguageGraph};

use crate::asset::PyLanguageGraphAsset;
use crate::assoc::PyLanguageGraphAssociation;
use crate::attack_step::PyLanguageGraphAttackStep;
use crate::exceptions::{graph_error_to_py, load_error_to_py};

/// Mirrors `maltoolbox.language.languagegraph.LanguageGraph`.
///
/// `unsendable`: holds `Rc<RefCell<_>>`, not `Arc<Mutex<_>>` - the GIL
/// already serializes access from Python; see
/// PYTHON_BINDINGS_IMPLEMENTATION.md's "Rc<RefCell<_>> vs Arc<Mutex<_>>"
/// note.
#[pyclass(name = "LanguageGraph", module = "maltoolbox._native", unsendable)]
pub struct PyLanguageGraph {
    pub inner: Rc<RefCell<LanguageGraph>>,
}

impl PyLanguageGraph {
    pub fn wrap(graph: LanguageGraph) -> Self {
        PyLanguageGraph {
            inner: Rc::new(RefCell::new(graph)),
        }
    }
}

#[pymethods]
impl PyLanguageGraph {
    #[staticmethod]
    fn load_from_file(path: &str) -> PyResult<Self> {
        let graph = lang_file::load_from_file(path).map_err(load_error_to_py)?;
        Ok(Self::wrap(graph))
    }

    #[staticmethod]
    fn from_mal_spec(path: &str) -> PyResult<Self> {
        let graph = lang_file::from_mal_spec(path).map_err(load_error_to_py)?;
        Ok(Self::wrap(graph))
    }

    #[staticmethod]
    fn from_mar_archive(path: &str) -> PyResult<Self> {
        let graph = lang_file::from_mar_archive(path).map_err(load_error_to_py)?;
        Ok(Self::wrap(graph))
    }

    fn save_to_file(&self, path: &str) -> PyResult<()> {
        let graph = self.inner.borrow();
        lang_file::save_to_file(&graph, path).map_err(load_error_to_py)
    }

    fn to_mar_archive(&self, path: &str) -> PyResult<()> {
        let graph = self.inner.borrow();
        lang_file::to_mar_archive(&graph, path).map_err(load_error_to_py)
    }

    /// Always writes JSON regardless of `filename`'s extension, matching
    /// the Python original (`json.dump(self.lang_spec, file, indent=4)`
    /// unconditionally).
    fn save_language_specification_to_json(&self, filename: &str) -> PyResult<()> {
        let graph = self.inner.borrow();
        let json = serde_json::to_string_pretty(&graph.lang_spec)
            .map_err(|e| graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(e.to_string())))?;
        std::fs::write(filename, json)
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))
    }

    /// Rebuild `.assets` from the `lang_spec` given at construction time
    /// (or loaded from a `.mal`/`.mar` file - *not* available on a graph
    /// rebuilt via `from_dict`/a plain JSON/YAML load, same gap as the
    /// Python original: `self.assets = generate_graph(self.lang_spec)`
    /// fails there too if `lang_spec` is `None`).
    fn regenerate_graph(&self) -> PyResult<()> {
        let lang_spec = self.inner.borrow().lang_spec.clone();
        let regenerated = maltoolbox_language::generate_graph(lang_spec).map_err(graph_error_to_py)?;
        *self.inner.borrow_mut() = regenerated;
        Ok(())
    }

    #[getter]
    fn metadata<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.inner.borrow();
        let dict = PyDict::new(py);
        dict.set_item("version", &graph.metadata.version)?;
        dict.set_item("id", &graph.metadata.id)?;
        Ok(dict)
    }

    #[getter]
    fn lang_spec<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.inner.borrow();
        pythonize::pythonize(py, &graph.lang_spec).map_err(|e| {
            graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(e.to_string()))
        })
    }

    #[getter]
    fn assets<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.inner.borrow();
        let dict = PyDict::new(py);
        for &id in &graph.asset_order {
            let name = graph.asset(id).name.clone();
            dict.set_item(name, PyLanguageGraphAsset::new(self.inner.clone(), id))?;
        }
        Ok(dict)
    }

    /// All associations in the language graph (a Python `set`, matching
    /// the original's `@property associations`).
    #[getter]
    fn associations<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PySet>> {
        let graph = self.inner.borrow();
        let set = PySet::empty(py)?;
        for &asset_id in &graph.asset_order {
            for assoc in graph.asset(asset_id).own_associations.values() {
                set.add(PyLanguageGraphAssociation::new(self.inner.clone(), assoc.clone()))?;
            }
        }
        Ok(set)
    }

    /// All attack steps in the language graph (a Python `set`, matching
    /// the original's `@property attack_steps`).
    #[getter]
    fn attack_steps<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PySet>> {
        let graph = self.inner.borrow();
        let set = PySet::empty(py)?;
        for &asset_id in &graph.asset_order {
            for &step_id in graph.asset(asset_id).attack_steps.values() {
                set.add(PyLanguageGraphAttackStep::new(self.inner.clone(), step_id))?;
            }
        }
        Ok(set)
    }

    /// Maps each association fieldname to the `(asset_type,
    /// attack_step_name)` pairs whose children expression chains can
    /// traverse that field. Computed fresh each call, not cached - see
    /// `LanguageGraph::fieldname_to_candidate_steps`'s doc comment in
    /// the core crate for why that tradeoff is accepted (same reasoning
    /// as the `.assets`/`.associations`/`.attack_steps` dict/set
    /// rebuild-per-access decision for this layer).
    #[getter]
    fn fieldname_to_candidate_steps<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.inner.borrow();
        let dict = PyDict::new(py);
        for (fieldname, pairs) in graph.fieldname_to_candidate_steps() {
            let set = PySet::empty(py)?;
            for (asset_type, step_name) in pairs {
                set.add(PyTuple::new(py, [asset_type, step_name])?)?;
            }
            dict.set_item(fieldname, set)?;
        }
        Ok(dict)
    }

    fn _to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.inner.borrow();
        let dict = language_graph_to_dict(&graph).map_err(graph_error_to_py)?;
        pythonize::pythonize(py, &dict).map_err(|e| {
            graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(e.to_string()))
        })
    }

    fn __repr__(&self) -> String {
        let graph = self.inner.borrow();
        format!(
            "LanguageGraph(id: \"{}\", version: \"{}\")",
            graph.metadata.id, graph.metadata.version
        )
    }

    /// Pickling target for `__reduce__` - a plain function (not the class
    /// itself), since `PyLanguageGraph` has no `#[new]` (matches the real
    /// Python original's `_from_dict`-based reconstruction path, not a
    /// bare constructor call) - see PYTHON_BINDINGS_IMPLEMENTATION.md's
    /// Phase 3 decision 4.
    #[staticmethod]
    fn _from_pickle_state(py: Python<'_>, state: &Bound<'_, PyAny>) -> PyResult<Self> {
        let value: serde_json::Value = pythonize::depythonize(state)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let _ = py;
        let graph = language_graph_from_dict(&value).map_err(graph_error_to_py)?;
        Ok(Self::wrap(graph))
    }

    fn __reduce__<'py>(&self, py: Python<'py>) -> PyResult<(Bound<'py, PyAny>, (Bound<'py, PyAny>,))> {
        let cls = py.get_type::<PyLanguageGraph>();
        let func = cls.getattr("_from_pickle_state")?;
        let state = self._to_dict(py)?;
        Ok((func, (state,)))
    }
}
