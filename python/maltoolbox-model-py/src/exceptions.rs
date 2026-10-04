//! Exception hierarchy mirroring `maltoolbox/exceptions.py`'s
//! `ModelException` branch, built on top of the `MalToolboxException`
//! type `maltoolbox-language-py` already created in Phase 1 - see
//! PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 2 decision 1 for why this
//! crate depends on that one instead of redefining a second,
//! incompatible `MalToolboxException` type.
//!
//! Important, confirmed-by-reading-the-source subtlety: unlike
//! `maltoolbox/language/compiler`'s errors, `maltoolbox/model.py`'s own
//! methods (`add_asset`/`remove_asset`/`add_associated_assets`/etc.)
//! almost never raise `ModelException` itself - they raise plain
//! built-in `ValueError`/`LookupError`/`TypeError` directly. The
//! `ModelException` subclasses in `exceptions.py`
//! (`ModelAssociationException`, `DuplicateModelAssociationError`) are
//! defined but never actually raised anywhere in the current codebase
//! (confirmed by grep) - dead exception classes, kept here only so the
//! same importable names exist, not because anything produces them.
//! `ModelException` itself is raised exactly once in the real source:
//! `Model.load_from_file`'s broad `except Exception as e: raise
//! ModelException(...) from e` wrapper. See `model_error_to_py` (plain
//! builtins, for direct method calls) vs `load_error_to_py` (always
//! `ModelException`, for the `load_from_file` entry point) below.

use pyo3::create_exception;
use pyo3::exceptions::{PyKeyError, PyLookupError, PyTypeError, PyValueError};
use pyo3::prelude::*;

use maltoolbox_language_py::exceptions::MalToolboxException;
use maltoolbox_model::file::LoadError;
use maltoolbox_model::ModelError;

create_exception!(_native, ModelException, MalToolboxException);
create_exception!(_native, ModelAssociationException, ModelException);
create_exception!(_native, DuplicateModelAssociationError, ModelException);

/// Maps a `ModelError` to the same plain built-in exception type
/// `maltoolbox/model.py`'s own code raises for the equivalent
/// condition - confirmed line-by-line against the real source, not
/// assumed. Two variants have no exact Python precedent (the Rust core
/// validates a couple of things Python doesn't check explicitly before
/// a raw dict/set operation would fail): `UnknownAssetId` (approximated
/// as `LookupError`, consistent with the other "not found" cases) and
/// `NotAssociated` (approximated as `KeyError`, matching the raw
/// `KeyError` Python's `_associated_assets[...].remove(...)` would
/// raise in the equivalent situation). Logged as a known approximation
/// in PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 2 status, not silently
/// picked.
pub fn model_error_to_py(err: ModelError) -> PyErr {
    let msg = err.to_string();
    match err {
        ModelError::DuplicateAssetId(_) => PyValueError::new_err(msg),
        ModelError::UnknownAssetType { .. } => PyValueError::new_err(msg),
        ModelError::DuplicateAssetName(_) => PyValueError::new_err(msg),
        ModelError::AssetNotFound { .. } => PyLookupError::new_err(msg),
        ModelError::UnknownFieldname { .. } => PyLookupError::new_err(msg),
        ModelError::WrongAssociatedAssetType { .. } => PyTypeError::new_err(msg),
        ModelError::TooManyAssetsInField(..) => PyValueError::new_err(msg),
        ModelError::UnknownAssociation { .. } => PyValueError::new_err(msg),
        ModelError::UnknownAssetId(_) => PyLookupError::new_err(msg),
        ModelError::NotAssociated { .. } => PyKeyError::new_err(msg),
        ModelError::Language(e) => maltoolbox_language_py::exceptions::graph_error_to_py(e),
        ModelError::Malformed(_) => PyValueError::new_err(msg),
    }
}

/// `_from_dict` (the classmethod, not `load_from_file`) has no
/// try/except in the Python original - raw errors propagate. Used only
/// if/when `Model._from_dict` is bound directly (see `model.rs`).
pub fn from_dict_error_to_py(err: LoadError) -> PyErr {
    match err {
        LoadError::FileUtil(e) => pyo3::exceptions::PyOSError::new_err(e.to_string()),
        LoadError::Model(e) => model_error_to_py(e),
        LoadError::Malformed(msg) => PyValueError::new_err(msg),
    }
}

/// `load_from_file` always wraps *any* failure into `ModelException`
/// with this exact message, matching `maltoolbox/model.py`'s broad
/// `except Exception as e: raise ModelException(...) from e`.
pub fn load_error_to_py(_err: LoadError) -> PyErr {
    ModelException::new_err(
        "Could not load model. It might be of an older version. \
         Try to upgrade it with 'maltoolbox upgrade-model'"
            .to_string(),
    )
}

pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("ModelException", py.get_type::<ModelException>())?;
    m.add(
        "ModelAssociationException",
        py.get_type::<ModelAssociationException>(),
    )?;
    m.add(
        "DuplicateModelAssociationError",
        py.get_type::<DuplicateModelAssociationError>(),
    )?;
    Ok(())
}
