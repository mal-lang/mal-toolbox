//! Exception hierarchy mirroring `maltoolbox/exceptions.py` (the
//! `LanguageGraphException` branch) plus the two *separate* compiler
//! hierarchies that are NOT under `MalToolboxException`:
//! `maltoolbox.language.compiler.exceptions.MalCompilerError` and
//! `maltoolbox.language.compiler.mal_analyzer.malAnalyzerException`.
//! See PYTHON_BINDINGS_IMPLEMENTATION.md's "Phase 1 decisions" section
//! for the exact Rust-error -> Python-exception mapping and the
//! evidence for why both hierarchies are required (not just the
//! `MalToolboxException` one).

use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyOSError};
use pyo3::prelude::*;

use maltoolbox_language::compiler::CompileError;
use maltoolbox_language::graph::file::LoadError;
use maltoolbox_language::graph::GraphError;

// As with the compiler hierarchy below, the module string given here
// becomes `__module__` (what `pickle`/`repr` use), set to where these
// live in `maltoolbox/exceptions.py` today, not this crate's own
// `_native` module.
create_exception!(maltoolbox.exceptions, MalToolboxException, PyException);
create_exception!(maltoolbox.exceptions, LanguageGraphException, MalToolboxException);
create_exception!(
    maltoolbox.exceptions,
    LanguageGraphSuperAssetNotFoundError,
    LanguageGraphException
);
create_exception!(maltoolbox.exceptions, LanguageGraphAssociationError, LanguageGraphException);
create_exception!(maltoolbox.exceptions, LanguageGraphStepExpressionError, LanguageGraphException);

// `maltoolbox.language.compiler.exceptions` - a *separate* hierarchy,
// not under `MalToolboxException` (matches the Python originals in
// `maltoolbox/language/compiler/exceptions.py`, which subclass `Exception`
// directly).
// The module string given here becomes `__module__` on the resulting
// exception type, which is what `pickle`/`repr` use to locate it - set
// to the path these will live at after Phase 4's cutover
// (`maltoolbox.language.compiler.exceptions`), not this crate's own
// `_native.language.compiler.exceptions` nesting, so a pickled instance
// survives the eventual shim swap.
create_exception!(maltoolbox.language.compiler.exceptions, MalCompilerError, PyException);
create_exception!(maltoolbox.language.compiler.exceptions, MalSyntaxError, MalCompilerError);
create_exception!(maltoolbox.language.compiler.exceptions, MalParseError, MalCompilerError);
create_exception!(maltoolbox.language.compiler.exceptions, MalTypeError, MalCompilerError);
create_exception!(maltoolbox.language.compiler.exceptions, MalNameError, MalCompilerError);
create_exception!(maltoolbox.language.compiler.exceptions, MalCompilationError, MalCompilerError);

// `maltoolbox.language.compiler.mal_analyzer.malAnalyzerException` - yet
// another separate hierarchy. Exact (unconventional, lowercase-`m`)
// name preserved: `assoc_traversal_processor.py` imports and raises it
// by this exact name.
#[allow(non_camel_case_types)]
mod mal_analyzer_exception {
    use super::{create_exception, PyException};
    create_exception!(
        maltoolbox.language.compiler.mal_analyzer,
        malAnalyzerException,
        PyException
    );
}
pub use mal_analyzer_exception::malAnalyzerException;

pub fn graph_error_to_py(err: GraphError) -> PyErr {
    let msg = err.to_string();
    match err {
        GraphError::SuperAssetNotFound { .. } => LanguageGraphSuperAssetNotFoundError::new_err(msg),
        GraphError::AssociationAssetNotFound { .. } => LanguageGraphAssociationError::new_err(msg),
        GraphError::StepExpression(_) => LanguageGraphStepExpressionError::new_err(msg),
        GraphError::Malformed(_) | GraphError::Lookup(_) => LanguageGraphException::new_err(msg),
    }
}

/// `CompileError` -> Python exception, per PYTHON_BINDINGS_IMPLEMENTATION.md
/// Phase 1 decision 3. Note this is a many-to-fewer mapping: the Rust
/// compiler doesn't distinguish parse/type/name sub-cases as finely as
/// Python's `MalCompilerError` hierarchy does, so `Malformed` collapses
/// to the base `MalCompilerError` rather than picking one of
/// `MalParseError`/`MalTypeError`/`MalNameError` arbitrarily.
pub fn compile_error_to_py(err: CompileError) -> PyErr {
    let msg = err.to_string();
    match err {
        CompileError::Io { .. } => PyOSError::new_err(msg),
        CompileError::Syntax { line, column, .. } => {
            // MalSyntaxError's Python `__init__(self, message, line=None,
            // column=None)` takes extra positional args beyond the
            // message - pass them through the same way.
            MalSyntaxError::new_err((msg, line, column))
        }
        CompileError::Malformed(_) => MalCompilerError::new_err(msg),
        CompileError::Semantic(_) => malAnalyzerException::new_err(msg),
    }
}

/// `LoadError` wraps a `CompileError`, a `GraphError`, or file-I/O
/// failures that occur during `LanguageGraph::load_from_file` and
/// friends (not just plain compilation).
pub fn load_error_to_py(err: LoadError) -> PyErr {
    match err {
        LoadError::Compile(e) => compile_error_to_py(e),
        LoadError::Graph(e) => graph_error_to_py(e),
        LoadError::FileUtil(e) => PyOSError::new_err(e.to_string()),
        LoadError::Archive(path, reason) => {
            PyOSError::new_err(format!("failed to read mar archive '{path}': {reason}"))
        }
        LoadError::UnknownExtension => {
            pyo3::exceptions::PyTypeError::new_err(
                "Unknown file extension, expected json/mal/mar/yml/yaml",
            )
        }
    }
}

/// Registers the `_native` module's top-level exceptions
/// (`MalToolboxException` + the `LanguageGraphException` branch) and
/// returns the two compiler-error submodules
/// (`language.compiler.exceptions`, `language.compiler.mal_analyzer`)
/// for the caller to nest and register in `sys.modules` - see
/// `lib.rs::register`.
pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("MalToolboxException", py.get_type::<MalToolboxException>())?;
    m.add("LanguageGraphException", py.get_type::<LanguageGraphException>())?;
    m.add(
        "LanguageGraphSuperAssetNotFoundError",
        py.get_type::<LanguageGraphSuperAssetNotFoundError>(),
    )?;
    m.add(
        "LanguageGraphAssociationError",
        py.get_type::<LanguageGraphAssociationError>(),
    )?;
    m.add(
        "LanguageGraphStepExpressionError",
        py.get_type::<LanguageGraphStepExpressionError>(),
    )?;
    Ok(())
}

pub fn register_compiler_exceptions(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("MalCompilerError", py.get_type::<MalCompilerError>())?;
    m.add("MalSyntaxError", py.get_type::<MalSyntaxError>())?;
    m.add("MalParseError", py.get_type::<MalParseError>())?;
    m.add("MalTypeError", py.get_type::<MalTypeError>())?;
    m.add("MalNameError", py.get_type::<MalNameError>())?;
    m.add("MalCompilationError", py.get_type::<MalCompilationError>())?;
    Ok(())
}

pub fn register_analyzer_exceptions(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("malAnalyzerException", py.get_type::<malAnalyzerException>())?;
    Ok(())
}
