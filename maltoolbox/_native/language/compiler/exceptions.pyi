"""Type stub for ``maltoolbox._native.language.compiler.exceptions``.

A *separate* exception hierarchy from `maltoolbox._native.MalToolboxException`
- matches the pure-Python originals in `maltoolbox/language/compiler/exceptions.py`,
which subclass `Exception` directly rather than any MAL Toolbox-specific
base. Imported directly by `maltoolbox/language/compiler/exceptions.py`.
"""


class MalCompilerError(Exception):
    """Base exception for every MAL compiler error."""

class MalSyntaxError(MalCompilerError):
    """Raised for a syntax error while parsing a `.mal` file.

    Takes extra positional args beyond the message:
    `MalSyntaxError(message, line=None, column=None)`.
    """

    def __init__(
        self,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None: ...

class MalParseError(MalCompilerError):
    """Raised for a parse error. Not currently produced by the Rust
    compiler (which collapses this case into the base
    `MalCompilerError`), but kept importable for API compatibility."""

class MalTypeError(MalCompilerError):
    """Raised for a type error. Not currently produced by the Rust
    compiler (which collapses this case into the base
    `MalCompilerError`), but kept importable for API compatibility."""

class MalNameError(MalCompilerError):
    """Raised for a name-resolution error. Not currently produced by the
    Rust compiler (which collapses this case into the base
    `MalCompilerError`), but kept importable for API compatibility."""

class MalCompilationError(MalCompilerError):
    """Raised for a generic compilation failure. Not currently produced
    by the Rust compiler (which collapses this case into the base
    `MalCompilerError`), but kept importable for API compatibility."""
