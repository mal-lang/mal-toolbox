"""Type stub for ``maltoolbox._native.language.compiler.mal_analyzer``.

A *separate* exception hierarchy, not under
`maltoolbox._native.MalToolboxException` nor
`maltoolbox._native.language.compiler.exceptions.MalCompilerError` -
matches the pure-Python original, which subclasses `Exception` directly.
The unconventional lowercase-`m` class name is intentional and exact:
`assoc_traversal_processor.py` (and other call sites) import and raise it
by this exact name. Imported directly by
`maltoolbox/language/compiler/mal_analyzer.py`.
"""


class malAnalyzerException(Exception):
    """Raised by the MAL semantic analyzer for a semantic/analysis error."""
