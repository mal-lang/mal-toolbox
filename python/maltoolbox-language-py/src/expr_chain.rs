//! Mirrors `maltoolbox/language/expression_chain.py`'s `ExpressionsChain`.
//! The core represents this as an enum (one variant per shape - see
//! `maltoolbox_language::graph::expr_chain`'s module doc), but the Python
//! original is one flat dataclass with many `Option` fields; this wrapper
//! exposes that same flat shape
//! (`type`/`left_link`/`right_link`/`sub_link`/`fieldname`/`association`/
//! `subtype`/`multiplicity`), reading `None` for whichever fields don't
//! apply to the wrapped variant.
//!
//! No identity caching, `__richcmp__`, or `__hash__` - this is a plain,
//! freely-constructible value snapshot. `association`/`subtype` resolve
//! through the owning graph's real handles/caches for consistency with
//! every other path to the same asset/association.

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::prelude::*;

use maltoolbox_language::graph::expr_chain::ExpressionsChain;
use maltoolbox_language::graph::LanguageGraph;

use crate::asset::PyLanguageGraphAsset;
use crate::assoc::PyLanguageGraphAssociation;
use crate::handle::{cached_handle, SharedLangGraphCaches};

#[derive(Clone)]
struct Ctx {
    owner: Rc<RefCell<LanguageGraph>>,
    caches: SharedLangGraphCaches,
}

#[pyclass(name = "ExpressionsChain", module = "maltoolbox._native", unsendable)]
pub struct PyExpressionsChain {
    chain: ExpressionsChain,
    ctx: Ctx,
}

#[pymethods]
impl PyExpressionsChain {
    #[getter(r#type)]
    fn expr_type(&self) -> &'static str {
        self.chain.expr_type().as_str()
    }

    #[getter]
    fn left_link(&self, py: Python<'_>) -> PyResult<Option<Py<PyExpressionsChain>>> {
        match &self.chain {
            ExpressionsChain::Binary { left, .. } => left
                .as_deref()
                .map(|c| chain_to_py(py, self.ctx.clone(), c.clone()))
                .transpose(),
            _ => Ok(None),
        }
    }

    #[getter]
    fn right_link(&self, py: Python<'_>) -> PyResult<Option<Py<PyExpressionsChain>>> {
        match &self.chain {
            ExpressionsChain::Binary { right, .. } => right
                .as_deref()
                .map(|c| chain_to_py(py, self.ctx.clone(), c.clone()))
                .transpose(),
            _ => Ok(None),
        }
    }

    #[getter]
    fn sub_link(&self, py: Python<'_>) -> PyResult<Option<Py<PyExpressionsChain>>> {
        match &self.chain {
            ExpressionsChain::Transitive { sub }
            | ExpressionsChain::SubType { sub, .. }
            | ExpressionsChain::AssocOp { sub }
            | ExpressionsChain::Multiplicity { sub, .. } => {
                Ok(Some(chain_to_py(py, self.ctx.clone(), (**sub).clone())?))
            }
            _ => Ok(None),
        }
    }

    #[getter]
    fn fieldname(&self) -> Option<String> {
        match &self.chain {
            ExpressionsChain::Field { fieldname, .. } => Some(fieldname.clone()),
            _ => None,
        }
    }

    #[getter]
    fn association(&self, py: Python<'_>) -> PyResult<Option<Py<PyLanguageGraphAssociation>>> {
        match &self.chain {
            ExpressionsChain::Field { association, .. } => Ok(Some(Py::new(
                py,
                PyLanguageGraphAssociation::new(
                    self.ctx.owner.clone(),
                    association.clone(),
                    self.ctx.caches.clone(),
                ),
            )?)),
            _ => Ok(None),
        }
    }

    #[getter]
    fn subtype(&self, py: Python<'_>) -> PyResult<Option<Py<PyLanguageGraphAsset>>> {
        match &self.chain {
            ExpressionsChain::SubType { subtype, .. } => {
                let owner = self.ctx.owner.clone();
                let caches = self.ctx.caches.clone();
                Ok(Some(cached_handle(
                    &self.ctx.caches.assets,
                    py,
                    *subtype,
                    move || PyLanguageGraphAsset::new(owner, *subtype, caches),
                )?))
            }
            _ => Ok(None),
        }
    }

    #[getter]
    fn multiplicity<'py>(&self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyAny>>> {
        match &self.chain {
            ExpressionsChain::Multiplicity { multiplicity, .. } => Ok(Some(
                pythonize::pythonize(py, multiplicity)
                    .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?,
            )),
            _ => Ok(None),
        }
    }

    fn __repr__(&self) -> String {
        format!("ExpressionsChain(type: \"{}\")", self.expr_type())
    }
}

fn chain_to_py(
    py: Python<'_>,
    ctx: Ctx,
    chain: ExpressionsChain,
) -> PyResult<Py<PyExpressionsChain>> {
    Py::new(py, PyExpressionsChain { chain, ctx })
}

/// Converts a core `ExpressionsChain` into its Python wrapper. `owner`/
/// `caches` identify the `LanguageGraph` that `association`/`subtype`
/// resolve their handles against.
pub fn expr_chain_to_py(
    py: Python<'_>,
    owner: Rc<RefCell<LanguageGraph>>,
    caches: SharedLangGraphCaches,
    chain: &ExpressionsChain,
) -> PyResult<Py<PyExpressionsChain>> {
    chain_to_py(py, Ctx { owner, caches }, chain.clone())
}
