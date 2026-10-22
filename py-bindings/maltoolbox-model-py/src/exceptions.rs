//! Exception hierarchy mirroring `maltoolbox/exceptions.py`'s
//! `ModelException` branch, built on the `MalToolboxException` type
//! from `maltoolbox-language-py`.
//!
//! `maltoolbox/model.py`'s own methods (`add_asset`/`remove_asset`/
//! `add_associated_assets`/etc.) almost never raise `ModelException`
//! itself - they raise plain built-in `ValueError`/`LookupError`/
//! `TypeError` directly. `ModelAssociationException` and
//! `DuplicateModelAssociationError` are dead exception classes in the
//! Python original (defined but never raised); they're kept here only
//! so the same importable names exist. `ModelException` itself is
//! raised only by `Model.load_from_file`'s broad exception wrapper. See
//! `model_error_to_py` (plain builtins, for direct method calls) vs
//! `load_error_to_py` (always `ModelException`, for `load_from_file`)
//! below.

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
/// condition. Two variants have no exact Python precedent, since the
/// Rust core validates a couple of things Python doesn't check
/// explicitly before a raw dict/set operation would fail:
/// `UnknownAssetId` is approximated as `LookupError` (consistent with
/// the other "not found" cases) and `NotAssociated` as `KeyError`
/// (matching the raw `KeyError` Python's
/// `_associated_assets[...].remove(...)` would raise).
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
