//! Exception hierarchy mirroring `maltoolbox/exceptions.py`'s
//! `AttackGraphException` branch, built on the `MalToolboxException` type
//! from `maltoolbox-language-py`.
//!
//! The core's `maltoolbox_attackgraph::GraphError` is overloaded: its
//! `Malformed(String)` variant covers several Python conditions that map
//! to *different* exception types there (plain lookup failures raise
//! `LookupError` directly in `node_getters.py`/`attack_graph_from_dict`,
//! not a custom exception). `graph_error_to_py` below is the context-free
//! default; call sites that know they're wrapping one of Python's
//! `LookupError`-raising paths (`get_node_by_full_name`, `from_dict`'s
//! "failed to find ..." messages) map directly to `PyLookupError` instead
//! - see `graph.rs`.

use pyo3::create_exception;
use pyo3::exceptions::{PyLookupError, PyOSError, PyValueError};
use pyo3::prelude::*;

use maltoolbox_attackgraph::GraphError;
use maltoolbox_language_py::exceptions::MalToolboxException;

create_exception!(_native, AttackGraphException, MalToolboxException);
create_exception!(_native, AttackGraphStepExpressionError, AttackGraphException);

/// Context-free default mapping for a [`GraphError`]:
/// - `DuplicateNodeId` -> `PyValueError`, matching `AttackGraph.add_node`'s
///   plain `ValueError` in Python.
/// - `StepExpression` -> `AttackGraphStepExpressionError`, matching
///   `generate.py`'s step-expression resolution failures.
/// - `Malformed` falls back to the base `AttackGraphException` (a
///   catch-all for conditions that are plain `LookupError`s at specific
///   call sites instead - see the module doc comment above).
/// - `Language`/`Model` delegate to the respective layer's own mapper.
pub fn graph_error_to_py(err: GraphError) -> PyErr {
    let msg = err.to_string();
    match err {
        GraphError::DuplicateNodeId(_) => PyValueError::new_err(msg),
        GraphError::StepExpression(_) => AttackGraphStepExpressionError::new_err(msg),
        GraphError::Malformed(_) => AttackGraphException::new_err(msg),
        GraphError::Language(e) => maltoolbox_language_py::exceptions::graph_error_to_py(e),
        GraphError::Model(e) => maltoolbox_model_py::exceptions::model_error_to_py(e),
        GraphError::FileUtil(e) => PyOSError::new_err(e.to_string()),
    }
}

/// For call sites that know any failure here corresponds to a
/// `LookupError` in Python (`get_node_by_full_name`,
/// `attack_graph_from_dict`'s "Failed to find ..." messages); bypasses
/// `graph_error_to_py`'s generic `Malformed` -> `AttackGraphException`
/// default.
pub fn graph_error_to_lookup(err: GraphError) -> PyErr {
    match err {
        GraphError::Language(e) => maltoolbox_language_py::exceptions::graph_error_to_py(e),
        GraphError::Model(e) => maltoolbox_model_py::exceptions::model_error_to_py(e),
        _ => PyLookupError::new_err(err.to_string()),
    }
}

pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("AttackGraphException", py.get_type::<AttackGraphException>())?;
    m.add(
        "AttackGraphStepExpressionError",
        py.get_type::<AttackGraphStepExpressionError>(),
    )?;
    Ok(())
}
