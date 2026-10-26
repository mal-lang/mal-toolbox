"""MAL-Toolbox Model Module

`Model`/`ModelAsset` are implemented in Rust and exposed here via the
`maltoolbox._native` extension module - see
PYTHON_BINDINGS_IMPLEMENTATION.md at the repo root for the full
rationale and status.
"""

from __future__ import annotations

from maltoolbox._native import Model as Model
from maltoolbox._native import ModelAsset as ModelAsset
