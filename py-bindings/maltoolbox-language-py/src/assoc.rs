//! Mirrors `maltoolbox/language/language_graph_assoc.py`'s
//! `LanguageGraphAssociation`/`LanguageGraphAssociationField`.
//!
//! Unlike `LanguageGraphAsset`/`LanguageGraphAttackStep`, these wrap the
//! actual `Rc<LanguageGraphAssociation>`/cloned `LanguageGraphAssociationField`
//! value directly rather than an owner+id pair: the core crate already
//! gives `LanguageGraphAssociation` structural `PartialEq`/`Hash`
//! (excluding `info`, matching the Python dataclass's
//! `field(compare=False)`), and both sides of an association already
//! share the same `Rc`, matching Python's `left_asset.own_associations[...]
//! = assoc; right_asset.own_associations[...] = assoc` (the same object
//! on both sides).

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::basic::CompareOp;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::IntoPyObjectExt;

use maltoolbox_language::graph::assoc::{LanguageGraphAssociation, LanguageGraphAssociationField};
use maltoolbox_language::graph::LanguageGraph;

use crate::asset::PyLanguageGraphAsset;
use crate::exceptions::graph_error_to_py;
use crate::handle::{cached_handle, SharedLangGraphCaches};

fn struct_hash<T: std::hash::Hash>(value: &T) -> isize {
    use std::hash::Hasher;
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    value.hash(&mut hasher);
    hasher.finish() as isize
}

/// `caches` is threaded through so `.asset` resolves to the same
/// per-owner-cached `PyLanguageGraphAsset` handle used everywhere else.
/// `LanguageGraphAssociation`/`Field` themselves aren't cached handles
/// (they already have structural equality, per the module doc comment);
/// this just keeps the *asset* handles they hand out consistent with
/// every other path to the same asset.
#[pyclass(
    name = "LanguageGraphAssociationField",
    unsendable,
    skip_from_py_object
)]
#[derive(Clone)]
pub struct PyLanguageGraphAssociationField {
    pub owner: Rc<RefCell<LanguageGraph>>,
    pub field: LanguageGraphAssociationField,
    pub caches: SharedLangGraphCaches,
}

#[pymethods]
impl PyLanguageGraphAssociationField {
    #[getter]
    fn asset(&self, py: Python<'_>) -> PyResult<Py<PyLanguageGraphAsset>> {
        let owner = self.owner.clone();
        let id = self.field.asset;
        let caches = self.caches.clone();
        cached_handle(&self.caches.assets, py, id, move || {
            PyLanguageGraphAsset::new(owner, id, caches)
        })
    }

    #[getter]
    fn fieldname(&self) -> String {
        self.field.fieldname.clone()
    }

    #[getter]
    fn minimum(&self) -> i64 {
        self.field.minimum
    }

    #[getter]
    fn maximum(&self) -> Option<i64> {
        self.field.maximum
    }

    pub fn __repr__(&self) -> String {
        let asset_name = self.owner.borrow().asset(self.field.asset).name.clone();
        format!(
            "LanguageGraphAssociationField(asset: LanguageGraphAsset(name: \"{}\"), fieldname: \"{}\", minimum: {}, maximum: {:?})",
            asset_name,
            self.field.fieldname,
            self.field.minimum,
            self.field.maximum
        )
    }

    fn __hash__(&self) -> isize {
        struct_hash(&self.field)
    }

    fn __richcmp__(
        &self,
        other: &PyLanguageGraphAssociationField,
        op: CompareOp,
        py: Python<'_>,
    ) -> PyResult<Py<PyAny>> {
        let eq = self.field == other.field;
        match op {
            CompareOp::Eq => eq.into_py_any(py),
            CompareOp::Ne => (!eq).into_py_any(py),
            _ => Ok(py.NotImplemented()),
        }
    }
}

#[pyclass(name = "LanguageGraphAssociation", unsendable, skip_from_py_object)]
#[derive(Clone)]
pub struct PyLanguageGraphAssociation {
    pub owner: Rc<RefCell<LanguageGraph>>,
    pub assoc: Rc<LanguageGraphAssociation>,
    pub caches: SharedLangGraphCaches,
}

impl PyLanguageGraphAssociation {
    pub fn new(
        owner: Rc<RefCell<LanguageGraph>>,
        assoc: Rc<LanguageGraphAssociation>,
        caches: SharedLangGraphCaches,
    ) -> Self {
        PyLanguageGraphAssociation {
            owner,
            assoc,
            caches,
        }
    }

    fn wrap_field(&self, field: &LanguageGraphAssociationField) -> PyLanguageGraphAssociationField {
        PyLanguageGraphAssociationField {
            owner: self.owner.clone(),
            field: field.clone(),
            caches: self.caches.clone(),
        }
    }
}

#[pymethods]
impl PyLanguageGraphAssociation {
    #[getter]
    fn name(&self) -> String {
        self.assoc.name.clone()
    }

    #[getter]
    fn left_field(&self) -> PyLanguageGraphAssociationField {
        self.wrap_field(&self.assoc.left_field)
    }

    #[getter]
    fn right_field(&self) -> PyLanguageGraphAssociationField {
        self.wrap_field(&self.assoc.right_field)
    }

    #[getter]
    fn info<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.assoc.info {
            dict.set_item(k, v)?;
        }
        Ok(dict)
    }

    #[getter]
    fn full_name(&self) -> String {
        self.assoc.full_name()
    }

    fn get_field(&self, fieldname: &str) -> PyLanguageGraphAssociationField {
        self.wrap_field(self.assoc.get_field(fieldname))
    }

    fn contains_fieldname(&self, fieldname: &str) -> bool {
        self.assoc.contains_fieldname(fieldname)
    }

    fn contains_asset(&self, asset: &PyLanguageGraphAsset) -> bool {
        let graph = self.owner.borrow();
        self.assoc.contains_asset(&graph, asset.id)
    }

    fn get_opposite_fieldname(&self, fieldname: &str) -> PyResult<String> {
        self.assoc
            .get_opposite_fieldname(fieldname)
            .map_err(graph_error_to_py)
    }

    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let graph = self.owner.borrow();
        let dict = self.assoc.to_dict(&graph);
        pythonize::pythonize(py, &dict).map_err(|e| {
            graph_error_to_py(maltoolbox_language::graph::GraphError::Malformed(
                e.to_string(),
            ))
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "LanguageGraphAssociation(name: \"{}\", left_field: {}, right_field: {})",
            self.assoc.name,
            self.left_field().__repr__(),
            self.right_field().__repr__()
        )
    }

    fn __hash__(&self) -> isize {
        struct_hash(self.assoc.as_ref())
    }

    fn __richcmp__(
        &self,
        other: &PyLanguageGraphAssociation,
        op: CompareOp,
        py: Python<'_>,
    ) -> PyResult<Py<PyAny>> {
        let eq = self.assoc == other.assoc;
        match op {
            CompareOp::Eq => eq.into_py_any(py),
            CompareOp::Ne => (!eq).into_py_any(py),
            _ => Ok(py.NotImplemented()),
        }
    }
}
