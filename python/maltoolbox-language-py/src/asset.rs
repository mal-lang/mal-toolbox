//! Mirrors `maltoolbox/language/language_graph_asset.py`'s
//! `LanguageGraphAsset`. A handle (`owner` + `AssetId`), not a cache -
//! see `handle.rs` / PYTHON_BINDINGS_IMPLEMENTATION.md.

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::basic::CompareOp;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::IntoPyObjectExt;

use maltoolbox_language::graph::ids::AssetId;
use maltoolbox_language::graph::LanguageGraph;

use crate::attack_step::PyLanguageGraphAttackStep;
use crate::assoc::PyLanguageGraphAssociation;
use crate::exceptions::graph_error_to_py;
use crate::handle::composite_hash;

#[pyclass(name = "LanguageGraphAsset", unsendable, skip_from_py_object)]
#[derive(Clone)]
pub struct PyLanguageGraphAsset {
    pub owner: Rc<RefCell<LanguageGraph>>,
    pub id: AssetId,
}

impl PyLanguageGraphAsset {
    pub fn new(owner: Rc<RefCell<LanguageGraph>>, id: AssetId) -> Self {
        PyLanguageGraphAsset { owner, id }
    }

    fn owner_ptr(&self) -> usize {
        Rc::as_ptr(&self.owner) as usize
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
                PyLanguageGraphAssociation::new(self.owner.clone(), assoc.clone()),
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
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (name, step_id) in &graph.asset(self.id).attack_steps {
            dict.set_item(
                name,
                PyLanguageGraphAttackStep::new(self.owner.clone(), *step_id),
            )?;
        }
        Ok(dict)
    }

    #[getter]
    fn own_super_asset(&self) -> Option<PyLanguageGraphAsset> {
        let graph = self.owner.borrow();
        graph
            .asset(self.id)
            .own_super_asset
            .map(|id| PyLanguageGraphAsset::new(self.owner.clone(), id))
    }

    #[getter]
    fn own_sub_assets(&self) -> Vec<PyLanguageGraphAsset> {
        let graph = self.owner.borrow();
        graph
            .asset(self.id)
            .own_sub_assets
            .iter()
            .map(|&id| PyLanguageGraphAsset::new(self.owner.clone(), id))
            .collect()
    }

    /// This asset plus every asset that directly or indirectly extends
    /// it. Not cached (Python's is a `cached_property`) - see
    /// `LanguageGraph::fieldname_to_candidate_steps`'s doc comment for
    /// why that tradeoff is accepted throughout this layer.
    #[getter]
    fn sub_assets(&self) -> Vec<PyLanguageGraphAsset> {
        let graph = self.owner.borrow();
        graph
            .sub_assets(self.id)
            .into_iter()
            .map(|id| PyLanguageGraphAsset::new(self.owner.clone(), id))
            .collect()
    }

    /// This asset plus every asset it directly or indirectly extends,
    /// closest ancestor first.
    #[getter]
    fn super_assets(&self) -> Vec<PyLanguageGraphAsset> {
        let graph = self.owner.borrow();
        graph
            .super_assets(self.id)
            .into_iter()
            .map(|id| PyLanguageGraphAsset::new(self.owner.clone(), id))
            .collect()
    }

    /// Own + inherited associations, by fieldname.
    #[getter]
    fn associations<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (fieldname, assoc) in graph.associations(self.id) {
            dict.set_item(
                fieldname,
                PyLanguageGraphAssociation::new(self.owner.clone(), assoc),
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
                PyLanguageGraphAssociation::new(self.owner.clone(), assoc),
            )?;
        }
        Ok(dict)
    }

    /// Own + inherited variables: name -> (target asset, optional
    /// expression chain). The expression chain is exposed as its
    /// serialized `to_dict()` form, not a live object - see
    /// PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 1 status for why
    /// (`ExpressionsChain` doesn't have its own wrapper class yet).
    #[getter]
    fn variables<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let graph = self.owner.borrow();
        let dict = PyDict::new(py);
        for (name, (asset_id, expr)) in graph.variables(self.id) {
            let asset_handle = PyLanguageGraphAsset::new(self.owner.clone(), asset_id);
            let expr_value = match &expr {
                Some(e) => e.to_dict(&graph).map_err(graph_error_to_py)?,
                None => serde_json::Value::Null,
            };
            let expr_obj = pythonize::pythonize(py, &expr_value)
                .map_err(|e| crate::exceptions::graph_error_to_py(
                    maltoolbox_language::graph::GraphError::Malformed(e.to_string()),
                ))?;
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
}

