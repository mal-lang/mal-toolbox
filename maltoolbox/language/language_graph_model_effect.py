"""LanguageGraphModelEffect functionality
- Represents a dynamic sentence's effect on the model instance (addition
  or removal of assets/associations), triggered by compromising an
  attack step.

`AssocTraversal`/`GlobAssocTraversal`/`AssocSet`/`DynTarget`/
`LanguageGraphModelEffect` are implemented in Rust and exposed here via
the `maltoolbox._native` extension module - see
PYTHON_BINDINGS_IMPLEMENTATION.md at the repo root (Phase 4a, "model
effects wrapper") for the full rationale and status.

`ModelEffectType`/`SetOperation` are not native pyclasses: the Rust side
returns `LanguageGraphModelEffect.model_effect_type` and `AssocSet.set_op`
as plain `str`s (`"ADDITIVE"`/`"SUBTRACTIVE"`, `"UNION"`/`"DIFFERENCE"`/
`"INTERSECTION"`), so this shim re-creates both as `str`-backed `Enum`s to
preserve the old pure-Python call sites that compare them against the
enum members (e.g. `model_effect.model_effect_type ==
ModelEffectType.ADDITIVE`, `assoc_set.set_op == SetOperation.UNION`). A
plain (non-`str`) `Enum` would make those comparisons always `False`.
"""

from __future__ import annotations

from enum import Enum

from maltoolbox._native import AssocSet as AssocSet
from maltoolbox._native import AssocTraversal as AssocTraversal
from maltoolbox._native import DynTarget as DynTarget
from maltoolbox._native import GlobAssocTraversal as GlobAssocTraversal
from maltoolbox._native import LanguageGraphModelEffect as LanguageGraphModelEffect


class ModelEffectType(str, Enum):
    """The type of effect on the model instance, i.e. addition or subtraction.

    Backed by `str` so it compares equal to the plain strings
    (`"ADDITIVE"`/`"SUBTRACTIVE"`) returned by the native
    `LanguageGraphModelEffect.model_effect_type` getter.
    """

    ADDITIVE = "ADDITIVE"
    SUBTRACTIVE = "SUBTRACTIVE"


class SetOperation(str, Enum):
    """A set operation between the results of two AssocTraversalChains.

    Backed by `str` so it compares equal to the plain strings
    (`"UNION"`/`"DIFFERENCE"`/`"INTERSECTION"`) returned by the native
    `AssocSet.set_op` getter.
    """

    UNION = "UNION"
    DIFFERENCE = "DIFFERENCE"
    INTERSECTION = "INTERSECTION"


# Mirrors the old pure-Python `AssocTraversalChain: TypeAlias = list[...]` -
# kept as a plain type alias for type hints; the native side builds these
# as ordinary Python lists of the element pyclasses above.
AssocTraversalChain = list[AssocTraversal | GlobAssocTraversal | AssocSet]
