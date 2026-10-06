"""MAL-Toolbox exception hierarchy.

Implemented in Rust, exposed here via `maltoolbox._native` - see
PYTHON_BINDINGS_IMPLEMENTATION.md at the repo root (`### Error ->
exception mapping`) for the full hierarchy and rationale.
"""

from maltoolbox._native import AttackGraphException as AttackGraphException
from maltoolbox._native import (
    AttackGraphStepExpressionError as AttackGraphStepExpressionError,
)
from maltoolbox._native import (
    DuplicateModelAssociationError as DuplicateModelAssociationError,
)
from maltoolbox._native import (
    LanguageGraphAssociationError as LanguageGraphAssociationError,
)
from maltoolbox._native import LanguageGraphException as LanguageGraphException
from maltoolbox._native import (
    LanguageGraphStepExpressionError as LanguageGraphStepExpressionError,
)
from maltoolbox._native import (
    LanguageGraphSuperAssetNotFoundError as LanguageGraphSuperAssetNotFoundError,
)
from maltoolbox._native import MalToolboxException as MalToolboxException
from maltoolbox._native import ModelAssociationException as ModelAssociationException
from maltoolbox._native import ModelException as ModelException
