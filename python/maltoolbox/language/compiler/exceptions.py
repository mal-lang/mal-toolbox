"""MalCompiler exception hierarchy.

Implemented in Rust, exposed here via `maltoolbox._native` - see
PYTHON_BINDINGS_IMPLEMENTATION.md at the repo root (Phase 4 decision 6)
for why these specific classes are shimmed even though `MalCompiler`
itself stays pure Python (Phase 4 decision 5): `LanguageGraph
.from_mal_spec` is native-backed and raises these same classes
internally, so the exception *class objects* must be shared for
`pytest.raises(MalCompilerError)`-style catching to work regardless of
which compiler (pure-Python `MalCompiler`, or the Rust one driving
`LanguageGraph.from_mal_spec`) raised it.
"""

from maltoolbox._native.language.compiler.exceptions import (
    MalCompilationError as MalCompilationError,
)
from maltoolbox._native.language.compiler.exceptions import (
    MalCompilerError as MalCompilerError,
)
from maltoolbox._native.language.compiler.exceptions import MalNameError as MalNameError
from maltoolbox._native.language.compiler.exceptions import (
    MalParseError as MalParseError,
)
from maltoolbox._native.language.compiler.exceptions import (
    MalSyntaxError as MalSyntaxError,
)
from maltoolbox._native.language.compiler.exceptions import MalTypeError as MalTypeError
