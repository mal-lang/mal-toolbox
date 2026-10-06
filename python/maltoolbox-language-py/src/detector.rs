//! Mirrors `maltoolbox/language/language_graph_detector.py`'s
//! `LanguageGraphDetector`/`LanguageGraphContextItem`, wrapping the Rust
//! core's `maltoolbox_language::graph::detector` types exposed on
//! `LanguageGraphAttackStep.detectors`.
//!
//! Like `model_effect.rs`/`expr_chain.rs`, these are plain,
//! freely-constructible value snapshots rather than owner+id handles:
//! no identity caching, `__richcmp__`, or `__hash__`.

use std::cell::RefCell;
use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::types::PyDict;

use maltoolbox_language::graph::detector::{LanguageGraphContextItem, LanguageGraphDetector};
use maltoolbox_language::graph::LanguageGraph;

use crate::asset::PyLanguageGraphAsset;
use crate::expr_chain::{expr_chain_to_py, PyExpressionsChain};
use crate::handle::{cached_handle, SharedLangGraphCaches};

#[derive(Clone)]
struct Ctx {
    owner: Rc<RefCell<LanguageGraph>>,
    caches: SharedLangGraphCaches,
}

#[pyclass(
    name = "LanguageGraphContextItem",
    module = "maltoolbox._native",
    unsendable
)]
pub struct PyLanguageGraphContextItem {
    label: String,
    asset_type: maltoolbox_language::graph::ids::AssetId,
    attack_step_name: Option<String>,
    expr: Option<maltoolbox_language::graph::expr_chain::ExpressionsChain>,
    ctx: Ctx,
}

#[pymethods]
impl PyLanguageGraphContextItem {
    #[getter]
    fn label(&self) -> String {
        self.label.clone()
    }

    /// The real `LanguageGraphAsset` object (not just its name), per the
    /// pure-Python original's dataclass shape.
    #[getter]
    fn asset_type(&self, py: Python<'_>) -> PyResult<Py<PyLanguageGraphAsset>> {
        let owner = self.ctx.owner.clone();
        let caches = self.ctx.caches.clone();
        let id = self.asset_type;
        cached_handle(&self.ctx.caches.assets, py, id, move || {
            PyLanguageGraphAsset::new(owner, id, caches)
        })
    }

    #[getter]
    fn attack_step_name(&self) -> Option<String> {
        self.attack_step_name.clone()
    }

    #[getter]
    fn expr(&self, py: Python<'_>) -> PyResult<Option<Py<PyExpressionsChain>>> {
        self.expr
            .as_ref()
            .map(|e| expr_chain_to_py(py, self.ctx.owner.clone(), self.ctx.caches.clone(), e))
            .transpose()
    }

    fn __repr__(&self) -> String {
        format!(
            "LanguageGraphContextItem(label: {:?}, attack_step_name: {:?})",
            self.label, self.attack_step_name
        )
    }
}

#[pyclass(
    name = "LanguageGraphDetector",
    module = "maltoolbox._native",
    unsendable
)]
pub struct PyLanguageGraphDetector {
    name: Option<String>,
    context: Vec<(String, LanguageGraphContextItem)>,
    detector_type: Option<String>,
    tprate: Option<f64>,
    fprate: Option<f64>,
    ctx: Ctx,
}

#[pymethods]
impl PyLanguageGraphDetector {
    #[getter]
    fn name(&self) -> Option<String> {
        self.name.clone()
    }

    #[getter]
    fn context<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        for (label, item) in &self.context {
            dict.set_item(
                label,
                Py::new(
                    py,
                    PyLanguageGraphContextItem {
                        label: item.label.clone(),
                        asset_type: item.asset_type,
                        attack_step_name: item.attack_step_name.clone(),
                        expr: item.expr.clone(),
                        ctx: self.ctx.clone(),
                    },
                )?,
            )?;
        }
        Ok(dict)
    }

    /// Python attribute name is `type` (matches the original dataclass
    /// field) - `#[getter(r#type)]` avoids colliding with the Rust
    /// keyword, same idiom as `AttackGraphNode.type`/
    /// `LanguageGraphAttackStep.type` elsewhere in this layer.
    #[getter(r#type)]
    fn detector_type(&self) -> Option<String> {
        self.detector_type.clone()
    }

    #[getter]
    fn tprate(&self) -> Option<f64> {
        self.tprate
    }

    #[getter]
    fn fprate(&self) -> Option<f64> {
        self.fprate
    }

    fn __repr__(&self) -> String {
        format!(
            "LanguageGraphDetector(name: {:?}, type: {:?}, tprate: {:?}, fprate: {:?})",
            self.name, self.detector_type, self.tprate, self.fprate
        )
    }
}

/// Converts a core `LanguageGraphDetector` into its Python wrapper.
/// `owner`/`caches` identify the `LanguageGraph` any `asset_type`/`expr`
/// should resolve its handles against.
pub fn detector_to_py(
    py: Python<'_>,
    owner: Rc<RefCell<LanguageGraph>>,
    caches: SharedLangGraphCaches,
    detector: &LanguageGraphDetector,
) -> PyResult<Py<PyLanguageGraphDetector>> {
    let ctx = Ctx { owner, caches };
    Py::new(
        py,
        PyLanguageGraphDetector {
            name: detector.name.clone(),
            context: detector
                .context
                .iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect(),
            detector_type: detector.detector_type.clone(),
            tprate: detector.tprate,
            fprate: detector.fprate,
            ctx,
        },
    )
}
