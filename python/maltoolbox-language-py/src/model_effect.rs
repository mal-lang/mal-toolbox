//! Mirrors `maltoolbox/language/language_graph_model_effect.py`'s
//! `LanguageGraphModelEffect`/`AssocTraversal`/`GlobAssocTraversal`/
//! `AssocSet`/`DynTarget`/`ModelEffectType`, wrapping the Rust core's
//! `maltoolbox_language::graph::model_effect` types. Built for Phase 4
//! decision 3 (`AttackGraphNode.additive_model_effects`/
//! `subtractive_model_effects` were `NotImplementedError` stubs for the
//! non-empty case until this).
//!
//! Per the user's explicit scope relaxation for these types: no
//! identity caching, `__richcmp__`, or `__hash__` is implemented here -
//! only correct attribute access, which is all `test_create_dynamic_ag`
//! (the one test exercising this) actually reads. These are plain,
//! freely-constructible value snapshots, not owner+id handles.

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple};

use maltoolbox_language::graph::model_effect::{
    AssocSet, AssocTraversal, AssocTraversalChain, AssocTraversalElem, DynTarget, GlobAssocTraversal,
    LanguageGraphModelEffect, ModelEffectType, QuantityFilter,
};
use maltoolbox_language::graph::LanguageGraph;

use crate::asset::PyLanguageGraphAsset;
use crate::handle::SharedLangGraphCaches;

/// Everything needed to resolve an `asset_filter: AssetId` into a real
/// `PyLanguageGraphAsset` handle while converting a core model-effect
/// value into its Python wrapper - bundled since every conversion
/// function below needs both.
#[derive(Clone)]
struct Ctx {
    owner: Rc<RefCell<LanguageGraph>>,
    caches: SharedLangGraphCaches,
}

fn quantity_to_py(py: Python<'_>, q: Option<QuantityFilter>) -> PyResult<Py<PyAny>> {
    match q {
        None => Ok(py.None()),
        Some(QuantityFilter::Exact(n)) => Ok(n.into_pyobject(py)?.into_any().unbind()),
        Some(QuantityFilter::Range(lo, hi)) => Ok(PyTuple::new(py, [lo, hi])?.into_any().unbind()),
    }
}

#[pyclass(name = "AssocTraversal", module = "maltoolbox._native", unsendable)]
pub struct PyAssocTraversal {
    field_name: String,
    asset_filter: Option<maltoolbox_language::graph::ids::AssetId>,
    quantity_filter: Option<QuantityFilter>,
    ctx: Ctx,
}

#[pymethods]
impl PyAssocTraversal {
    #[getter]
    fn field_name(&self) -> String {
        self.field_name.clone()
    }

    #[getter]
    fn asset_filter(&self, py: Python<'_>) -> PyResult<Option<Py<PyLanguageGraphAsset>>> {
        self.asset_filter.map(|id| cached_asset(py, &self.ctx, id)).transpose()
    }

    #[getter]
    fn quantity_filter(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        quantity_to_py(py, self.quantity_filter)
    }

    fn __repr__(&self) -> String {
        format!(
            "AssocTraversal(field_name: {:?}, asset_filter: {:?}, quantity_filter: {:?})",
            self.field_name, self.asset_filter, self.quantity_filter
        )
    }
}

/// Resolves an `asset_filter: AssetId` to a `PyLanguageGraphAsset`
/// handle via the owning graph's real cache (Phase 4 decision 1 applies
/// here too, for consistency, even though `LanguageGraphModelEffect`
/// itself isn't one of the four cached handle types).
fn cached_asset(py: Python<'_>, ctx: &Ctx, id: maltoolbox_language::graph::ids::AssetId) -> PyResult<Py<PyLanguageGraphAsset>> {
    let owner = ctx.owner.clone();
    let caches = ctx.caches.clone();
    crate::handle::cached_handle(&ctx.caches.assets, py, id, move || PyLanguageGraphAsset::new(owner, id, caches))
}

#[pyclass(name = "GlobAssocTraversal", module = "maltoolbox._native", unsendable)]
pub struct PyGlobAssocTraversal {
    pattern: AssocTraversalChain,
    quantity_filter: Option<QuantityFilter>,
    ctx: Ctx,
}

#[pymethods]
impl PyGlobAssocTraversal {
    #[getter]
    fn pattern<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        chain_to_pylist(py, &self.ctx, &self.pattern)
    }

    #[getter]
    fn quantity_filter(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        quantity_to_py(py, self.quantity_filter)
    }

    fn __repr__(&self) -> String {
        format!("GlobAssocTraversal(pattern: [{} elem(s)])", self.pattern.len())
    }
}

#[pyclass(name = "AssocSet", module = "maltoolbox._native", unsendable)]
pub struct PyAssocSet {
    set_op: SetOperationPy,
    left: AssocTraversalChain,
    right: AssocTraversalChain,
    quantity_filter: Option<QuantityFilter>,
    ctx: Ctx,
}

#[derive(Clone, Copy)]
struct SetOperationPy(maltoolbox_language::graph::model_effect::SetOperation);

#[pymethods]
impl PyAssocSet {
    #[getter]
    fn set_op(&self) -> &'static str {
        use maltoolbox_language::graph::model_effect::SetOperation::*;
        match self.set_op.0 {
            Union => "UNION",
            Difference => "DIFFERENCE",
            Intersection => "INTERSECTION",
        }
    }

    #[getter]
    fn left<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        chain_to_pylist(py, &self.ctx, &self.left)
    }

    #[getter]
    fn right<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        chain_to_pylist(py, &self.ctx, &self.right)
    }

    #[getter]
    fn quantity_filter(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        quantity_to_py(py, self.quantity_filter)
    }

    fn __repr__(&self) -> String {
        format!("AssocSet(set_op: {})", self.set_op())
    }
}

#[pyclass(name = "DynTarget", module = "maltoolbox._native", unsendable)]
pub struct PyDynTarget {
    assoc_op: bool,
    assoc_traversal: AssocTraversalChain,
    ctx: Ctx,
}

#[pymethods]
impl PyDynTarget {
    #[getter]
    fn assoc_op(&self) -> bool {
        self.assoc_op
    }

    #[getter]
    fn assoc_traversal<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        chain_to_pylist(py, &self.ctx, &self.assoc_traversal)
    }

    fn __repr__(&self) -> String {
        format!("DynTarget(assoc_op: {}, assoc_traversal: [{} elem(s)])", self.assoc_op, self.assoc_traversal.len())
    }
}

#[pyclass(name = "LanguageGraphModelEffect", module = "maltoolbox._native", unsendable)]
pub struct PyLanguageGraphModelEffect {
    model_effect_type: ModelEffectType,
    base: AssocTraversalChain,
    targets: Vec<DynTarget>,
    ctx: Ctx,
}

#[pymethods]
impl PyLanguageGraphModelEffect {
    #[getter(model_effect_type)]
    fn model_effect_type_py(&self) -> &'static str {
        match self.model_effect_type {
            ModelEffectType::Additive => "ADDITIVE",
            ModelEffectType::Subtractive => "SUBTRACTIVE",
        }
    }

    #[getter]
    fn base<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        chain_to_pylist(py, &self.ctx, &self.base)
    }

    #[getter]
    fn targets(&self, py: Python<'_>) -> PyResult<Vec<Py<PyDynTarget>>> {
        self.targets
            .iter()
            .map(|t| {
                Py::new(
                    py,
                    PyDynTarget {
                        assoc_op: t.assoc_op,
                        assoc_traversal: t.assoc_traversal.clone(),
                        ctx: self.ctx.clone(),
                    },
                )
            })
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "LanguageGraphModelEffect(model_effect_type: {}, base: [{} elem(s)], targets: [{} elem(s)])",
            self.model_effect_type_py(),
            self.base.len(),
            self.targets.len()
        )
    }
}

fn elem_to_py(py: Python<'_>, ctx: &Ctx, elem: &AssocTraversalElem) -> PyResult<Py<PyAny>> {
    match elem {
        AssocTraversalElem::Traversal(AssocTraversal {
            field_name,
            asset_filter,
            quantity_filter,
        }) => Ok(Py::new(
            py,
            PyAssocTraversal {
                field_name: field_name.clone(),
                asset_filter: *asset_filter,
                quantity_filter: *quantity_filter,
                ctx: ctx.clone(),
            },
        )?
        .into_any()),
        AssocTraversalElem::Glob(GlobAssocTraversal { pattern, quantity_filter }) => Ok(Py::new(
            py,
            PyGlobAssocTraversal {
                pattern: pattern.clone(),
                quantity_filter: *quantity_filter,
                ctx: ctx.clone(),
            },
        )?
        .into_any()),
        AssocTraversalElem::Set(AssocSet {
            set_op,
            left,
            right,
            quantity_filter,
        }) => Ok(Py::new(
            py,
            PyAssocSet {
                set_op: SetOperationPy(*set_op),
                left: left.clone(),
                right: right.clone(),
                quantity_filter: *quantity_filter,
                ctx: ctx.clone(),
            },
        )?
        .into_any()),
    }
}

fn chain_to_pylist<'py>(py: Python<'py>, ctx: &Ctx, chain: &AssocTraversalChain) -> PyResult<Bound<'py, PyList>> {
    let items: PyResult<Vec<Py<PyAny>>> = chain.iter().map(|e| elem_to_py(py, ctx, e)).collect();
    PyList::new(py, items?)
}

/// Converts a core `LanguageGraphModelEffect` into its Python wrapper.
/// `owner`/`caches` identify the `LanguageGraph` any `asset_filter`
/// should resolve its `PyLanguageGraphAsset` handles against (Phase 4
/// decision 1's cache applies here too, for consistency, even though
/// `LanguageGraphModelEffect` itself isn't a cached handle type).
pub fn model_effect_to_py(
    py: Python<'_>,
    owner: Rc<RefCell<LanguageGraph>>,
    caches: SharedLangGraphCaches,
    effect: &LanguageGraphModelEffect,
) -> PyResult<Py<PyLanguageGraphModelEffect>> {
    let ctx = Ctx { owner, caches };
    Py::new(
        py,
        PyLanguageGraphModelEffect {
            model_effect_type: effect.model_effect_type,
            base: effect.base.clone(),
            targets: effect.targets.clone(),
            ctx,
        },
    )
}
