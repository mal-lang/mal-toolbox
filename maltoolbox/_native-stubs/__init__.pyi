"""Type stubs for the compiled PyO3 extension module ``maltoolbox._native``.

This is a PEP 561 stub-only package: there is no real ``maltoolbox/_native/``
package on disk at runtime (the real thing is the compiled
``maltoolbox/_native.*.so`` extension module, built via maturin from
``python/maltoolbox-pyo3``). These ``.pyi`` files exist purely to give
type checkers (mypy) and editors (Pylance) full type/autocomplete
information for that compiled module's API.

The native module is assembled from three PyO3 "compat layer" crates:
``maltoolbox-language-py``, ``maltoolbox-model-py``, and
``maltoolbox-attackgraph-py``. Each crate's ``register()`` function (see
each crate's ``src/lib.rs``) adds its classes/exceptions/functions to this
module; ``maltoolbox-language-py``'s ``register()`` additionally nests
submodules at ``maltoolbox._native.language``,
``maltoolbox._native.language.compiler``,
``maltoolbox._native.language.compiler.exceptions``, and
``maltoolbox._native.language.compiler.mal_analyzer`` (see the sibling
``.pyi`` files under ``language/``).
"""


from collections.abc import Mapping
from typing import Any

# ---------------------------------------------------------------------------
# Exceptions (maltoolbox-language-py/src/exceptions.rs, Phase 1 hierarchy;
# maltoolbox-model-py/src/exceptions.rs, Phase 2 hierarchy;
# maltoolbox-attackgraph-py/src/exceptions.rs, Phase 3 hierarchy)
# ---------------------------------------------------------------------------

class MalToolboxException(Exception):
    """Base exception for every MAL Toolbox-specific error."""

class LanguageGraphException(MalToolboxException):
    """Base exception for LanguageGraph-related errors."""

class LanguageGraphSuperAssetNotFoundError(LanguageGraphException):
    """Raised when an asset's declared super asset cannot be found."""

class LanguageGraphAssociationError(LanguageGraphException):
    """Raised for invalid/malformed association lookups."""

class LanguageGraphStepExpressionError(LanguageGraphException):
    """Raised when a step expression fails to resolve."""

class ModelException(MalToolboxException):
    """Base exception for Model-related errors."""

class ModelAssociationException(ModelException):
    """Defined for API compatibility; not currently raised by any Rust or
    Python code path (see ``maltoolbox-model-py/src/exceptions.rs``)."""

class DuplicateModelAssociationError(ModelException):
    """Defined for API compatibility; not currently raised by any Rust or
    Python code path (see ``maltoolbox-model-py/src/exceptions.rs``)."""

class AttackGraphException(MalToolboxException):
    """Base exception for AttackGraph-related errors."""

class AttackGraphStepExpressionError(AttackGraphException):
    """Raised when a step expression fails to resolve while generating or
    regenerating an attack graph."""

# ---------------------------------------------------------------------------
# Language layer (maltoolbox-language-py)
# ---------------------------------------------------------------------------

class LanguageGraphAssociationField:
    """One side (left or right) of a `LanguageGraphAssociation`."""

    @property
    def asset(self) -> LanguageGraphAsset: ...
    @property
    def fieldname(self) -> str: ...
    @property
    def minimum(self) -> int: ...
    @property
    def maximum(self) -> int | None: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

class LanguageGraphAssociation:
    """An association (type) defined in a MAL language, linking two asset
    types via a left and a right field."""

    @property
    def name(self) -> str: ...
    @property
    def left_field(self) -> LanguageGraphAssociationField: ...
    @property
    def right_field(self) -> LanguageGraphAssociationField: ...
    @property
    def info(self) -> dict[str, Any]: ...
    @property
    def full_name(self) -> str: ...
    def get_field(self, fieldname: str) -> LanguageGraphAssociationField: ...
    def contains_fieldname(self, fieldname: str) -> bool: ...
    def contains_asset(self, asset: LanguageGraphAsset) -> bool: ...
    def get_opposite_fieldname(self, fieldname: str) -> str: ...
    def to_dict(self) -> dict[str, Any]: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

class ExpressionsChain:
    """A node in a tree of operations describing how to traverse
    associations in a language graph (union/intersection/difference/
    collect/field/transitive/subType/assoc_op/multiplicity). Field values
    that don't apply to this node's `type` read as `None`."""

    @property
    def type(self) -> str: ...
    @property
    def left_link(self) -> ExpressionsChain | None: ...
    @property
    def right_link(self) -> ExpressionsChain | None: ...
    @property
    def sub_link(self) -> ExpressionsChain | None: ...
    @property
    def fieldname(self) -> str | None: ...
    @property
    def association(self) -> LanguageGraphAssociation | None: ...
    @property
    def subtype(self) -> LanguageGraphAsset | None: ...
    @property
    def multiplicity(self) -> Any | None: ...

class LanguageGraphAttackStep:
    """An attack step (type) defined on an asset type in a MAL language."""

    @property
    def name(self) -> str: ...
    @property
    def type(self) -> str: ...
    @property
    def asset(self) -> LanguageGraphAsset: ...
    @property
    def causal_mode(self) -> str | None: ...
    @property
    def ttc(self) -> Any | None: ...
    @property
    def overrides(self) -> bool: ...
    @property
    def info(self) -> dict[str, Any]: ...
    @property
    def tags(self) -> list[str]: ...
    @property
    def inherits(self) -> LanguageGraphAttackStep | None: ...
    @property
    def own_children(self) -> dict[LanguageGraphAttackStep, list[ExpressionsChain | None]]: ...
    @property
    def own_parents(self) -> dict[LanguageGraphAttackStep, list[ExpressionsChain | None]]: ...
    @property
    def children(self) -> dict[LanguageGraphAttackStep, list[ExpressionsChain | None]]: ...
    @property
    def parents(self) -> None:
        """Always raises `NotImplementedError` - never implemented, on
        either the Rust or the original pure-Python side."""
    @property
    def own_requires(self) -> list[ExpressionsChain | None]: ...
    @property
    def requires(self) -> list[ExpressionsChain | None]: ...
    @property
    def own_additive_model_effects(self) -> list[LanguageGraphModelEffect]: ...
    @property
    def own_subtractive_model_effects(self) -> list[LanguageGraphModelEffect]: ...
    @property
    def additive_model_effects(self) -> list[LanguageGraphModelEffect]: ...
    @property
    def subtractive_model_effects(self) -> list[LanguageGraphModelEffect]: ...
    @property
    def full_name(self) -> str: ...
    @property
    def detectors(self) -> dict[str, LanguageGraphDetector]: ...
    def to_dict(self) -> dict[str, Any]: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

class LanguageGraphAsset:
    """An asset (type) defined in a MAL language."""

    @property
    def name(self) -> str: ...
    @property
    def is_abstract(self) -> bool: ...
    @property
    def info(self) -> dict[str, Any]: ...
    @property
    def own_associations(self) -> dict[str, LanguageGraphAssociation]: ...
    @property
    def attack_steps(self) -> dict[str, LanguageGraphAttackStep]: ...
    @property
    def own_super_asset(self) -> LanguageGraphAsset | None: ...
    @property
    def own_sub_assets(self) -> list[LanguageGraphAsset]: ...
    @property
    def sub_assets(self) -> list[LanguageGraphAsset]: ...
    @property
    def super_assets(self) -> list[LanguageGraphAsset]: ...
    @property
    def associations(self) -> dict[str, LanguageGraphAssociation]: ...
    def associations_to(self, asset_type: LanguageGraphAsset) -> dict[str, LanguageGraphAssociation]: ...
    @property
    def variables(self) -> dict[str, tuple[LanguageGraphAsset, ExpressionsChain | None]]: ...
    def is_subasset_of(self, target_asset: LanguageGraphAsset) -> bool: ...
    def get_all_common_superassets(self, other: LanguageGraphAsset) -> set[str]: ...
    def to_dict(self) -> dict[str, Any]: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

class LanguageGraphContextItem:
    """One entry in a `LanguageGraphDetector.context` mapping."""

    @property
    def label(self) -> str: ...
    @property
    def asset_type(self) -> LanguageGraphAsset: ...
    @property
    def attack_step_name(self) -> str | None: ...
    @property
    def expr(self) -> ExpressionsChain | None: ...

class LanguageGraphDetector:
    """A detector declared on an attack step in a MAL language."""

    @property
    def name(self) -> str | None: ...
    @property
    def context(self) -> dict[str, LanguageGraphContextItem]: ...
    @property
    def type(self) -> str | None: ...
    @property
    def tprate(self) -> float | None: ...
    @property
    def fprate(self) -> float | None: ...

class AssocTraversal:
    """A single association-field traversal step within a model effect's
    `base`/`targets` traversal chains."""

    @property
    def field_name(self) -> str: ...
    @property
    def asset_filter(self) -> LanguageGraphAsset | None: ...
    @property
    def quantity_filter(self) -> int | tuple[int, int] | None: ...

class GlobAssocTraversal:
    """A glob (`*`) traversal step matching any association field."""

    @property
    def pattern(self) -> list[AssocTraversal | GlobAssocTraversal | AssocSet]: ...
    @property
    def quantity_filter(self) -> int | tuple[int, int] | None: ...

class AssocSet:
    """A set-operation (union/difference/intersection) node within a
    model effect's traversal chain."""

    @property
    def set_op(self) -> str:
        """One of `"UNION"`, `"DIFFERENCE"`, `"INTERSECTION"`."""
    @property
    def left(self) -> list[AssocTraversal | GlobAssocTraversal | AssocSet]: ...
    @property
    def right(self) -> list[AssocTraversal | GlobAssocTraversal | AssocSet]: ...
    @property
    def quantity_filter(self) -> int | tuple[int, int] | None: ...

class DynTarget:
    """A single target (association to add/remove) of a dynamic sentence's
    model effect."""

    @property
    def assoc_op(self) -> bool: ...
    @property
    def assoc_traversal(self) -> list[AssocTraversal | GlobAssocTraversal | AssocSet]: ...

class LanguageGraphModelEffect:
    """A dynamic sentence's effect on the model instance (addition or
    removal of assets/associations), triggered by compromising an attack
    step."""

    @property
    def model_effect_type(self) -> str:
        """One of `"ADDITIVE"`, `"SUBTRACTIVE"`."""
    @property
    def base(self) -> list[AssocTraversal | GlobAssocTraversal | AssocSet]: ...
    @property
    def targets(self) -> list[DynTarget]: ...

class LanguageGraph:
    """Graph representation of a MAL language."""

    def __init__(self, lang_spec: dict[str, Any]) -> None:
        """Build a graph directly from an already-compiled langspec dict
        (the shape `MalCompiler().compile(...)` produces, same as what's
        inside a `.mar` archive's `langspec.json`)."""
    @staticmethod
    def load_from_file(path: str) -> LanguageGraph:
        """Create a LanguageGraph from mal, mar, yaml, or json."""
    @staticmethod
    def from_mal_spec(path: str) -> LanguageGraph:
        """Create a LanguageGraph from a `.mal` file (a MAL spec)."""
    @staticmethod
    def from_mar_archive(path: str) -> LanguageGraph:
        """Create a LanguageGraph from a `.mar` archive provided by malc."""
    def save_to_file(self, path: str) -> None:
        """Save to json/yml/mar depending on extension."""
    def to_mar_archive(self, path: str) -> None:
        """Save the LanguageGraph's `lang_spec` to a `.mar` archive that
        can be loaded with `from_mar_archive`."""
    def save_language_specification_to_json(self, filename: str) -> None:
        """Save the MAL language specification dictionary to a JSON file."""
    def regenerate_graph(self) -> None:
        """Rebuild `.assets` from the `lang_spec` given at construction
        time (or loaded from a `.mal`/`.mar` file) - not available on a
        graph rebuilt via a plain JSON/YAML load with no `lang_spec`."""
    @property
    def metadata(self) -> dict[str, str]: ...
    @property
    def lang_spec(self) -> dict[str, Any]: ...
    @property
    def assets(self) -> dict[str, LanguageGraphAsset]: ...
    @property
    def associations(self) -> set[LanguageGraphAssociation]: ...
    @property
    def attack_steps(self) -> set[LanguageGraphAttackStep]: ...
    @property
    def fieldname_to_candidate_steps(self) -> dict[str, set[tuple[str, str]]]: ...
    def _to_dict(self) -> dict[str, Any]: ...
    def __reduce__(self) -> tuple[Any, ...]: ...

# ---------------------------------------------------------------------------
# Model layer (maltoolbox-model-py)
# ---------------------------------------------------------------------------

class ModelAsset:
    """An instance of an asset (type) in a `Model`. Only ever handed out
    by a `Model` - no public constructor."""

    @property
    def name(self) -> str: ...
    @property
    def id(self) -> int: ...
    @property
    def type(self) -> str: ...
    @property
    def lg_asset(self) -> LanguageGraphAsset: ...
    @property
    def defenses(self) -> dict[str, float]: ...
    @property
    def extras(self) -> dict[str, Any]: ...
    @extras.setter
    def extras(self, value: dict[str, Any]) -> None: ...
    @property
    def associated_assets(self) -> dict[str, set[ModelAsset]]: ...
    def associations_with(self, other: ModelAsset) -> list[LanguageGraphAssociation]: ...
    def has_association_with(self, other: ModelAsset, assoc_name: str) -> bool: ...
    def validate_associated_assets(
        self, fieldname: str, assets_to_add: set[ModelAsset]
    ) -> None: ...
    def add_associated_assets(self, fieldname: str, assets: set[ModelAsset]) -> None: ...
    def remove_associated_assets(self, fieldname: str, assets: set[ModelAsset]) -> None: ...
    def to_dict(self) -> dict[int, dict[str, Any]]: ...
    def _to_dict(self) -> dict[int, dict[str, Any]]: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

class Model:
    """An implementation of a MAL language model containing assets."""

    def __init__(
        self,
        name: str,
        lang_graph: LanguageGraph,
        mt_version: str | None = None,
    ) -> None: ...
    @property
    def name(self) -> str: ...
    @name.setter
    def name(self, value: str) -> None: ...
    @property
    def lang_graph(self) -> LanguageGraph: ...
    @property
    def maltoolbox_version(self) -> str: ...
    @property
    def next_id(self) -> int: ...
    @next_id.setter
    def next_id(self, value: int) -> None: ...
    @property
    def assets(self) -> dict[int, ModelAsset]: ...
    def add_asset(
        self,
        asset_type: str,
        name: str | None = None,
        asset_id: int | None = None,
        defenses: dict[str, float] | None = None,
        extras: dict[str, Any] | None = None,
        allow_duplicate_names: bool = True,
    ) -> ModelAsset:
        """Create an asset based on the provided parameters and add it to
        the model."""
    def remove_asset(self, asset: ModelAsset) -> None:
        """Remove an asset from the model."""
    def get_asset_by_id(self, asset_id: int) -> ModelAsset | None: ...
    def get_asset_by_name(self, asset_name: str) -> ModelAsset | None: ...
    def to_dict(self) -> dict[str, Any]: ...
    def _to_dict(self) -> dict[str, Any]: ...
    def save_to_file(self, filename: str) -> None:
        """Save to json/yml depending on extension."""
    @staticmethod
    def load_from_file(filename: str, lang_graph: LanguageGraph) -> Model:
        """Create from json or yaml file depending on file extension."""
    @staticmethod
    def _from_dict(serialized: dict[str, Any], lang_graph: LanguageGraph) -> Model:
        """Deserialize a previously-`_to_dict`'d model dict. Used by
        `maltoolbox.translators.updater` to rebuild older-schema models."""
    def __reduce__(self) -> tuple[Any, ...]: ...

# ---------------------------------------------------------------------------
# Attack graph layer (maltoolbox-attackgraph-py)
# ---------------------------------------------------------------------------

class Detector:
    """A detector attached to an `AttackGraphNode`."""

    def __init__(
        self,
        name: str | None,
        node: AttackGraphNode,
        potential_context: dict[str, set[AttackGraphNode]],
        tprate: float | None = None,
        fprate: float | None = None,
    ) -> None: ...
    @property
    def name(self) -> str | None: ...
    @property
    def node(self) -> AttackGraphNode: ...
    @property
    def potential_context(self) -> dict[str, set[AttackGraphNode]]: ...
    @property
    def tprate(self) -> float | None: ...
    @property
    def fprate(self) -> float | None: ...
    def to_dict(self) -> dict[str, Any]: ...
    def __hash__(self) -> int:
        """Always raises `TypeError` ('unhashable type: Detector') -
        mirrors the real runtime effect of the original frozen
        dataclass's auto-generated `__hash__` (its `potential_context`
        dict field is itself unhashable)."""
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def __reduce__(self) -> tuple[Any, ...]: ...

class AttackGraphNode:
    """A single node (attack step or defense step instance) in an
    `AttackGraph`.

    Nodes handed out by an owning `AttackGraph` (via `.nodes`,
    `.attack_steps`, `.defense_steps`, `.add_node`, traversal, ...) support
    the full API below. A node constructed directly
    (`AttackGraphNode(node_id, lg_attack_step, ...)`) is "detached" - it
    has no owning graph, and only supports `.id`/`.name`/`.children`/
    `.parents` (get and set) plus `__repr__`/default identity hash+eq;
    every other attribute/method raises `NotImplementedError` on a
    detached node.
    """

    def __init__(
        self,
        node_id: int,
        lg_attack_step: LanguageGraphAttackStep,
        model_asset: ModelAsset | None = None,
        ttc_dist: dict[str, Any] | None = None,
        existence_status: bool | None = None,
        full_name: str | None = None,
    ) -> None: ...
    @property
    def id(self) -> int: ...
    @property
    def name(self) -> str: ...
    @property
    def type(self) -> str: ...
    @property
    def lg_attack_step(self) -> LanguageGraphAttackStep: ...
    @property
    def causal_mode(self) -> str | None: ...
    @property
    def ttc(self) -> Any | None: ...
    @property
    def tags(self) -> list[str]: ...
    @property
    def additive_model_effects(self) -> list[LanguageGraphModelEffect] | None: ...
    @property
    def subtractive_model_effects(self) -> list[LanguageGraphModelEffect] | None: ...
    @property
    def model_asset(self) -> ModelAsset | None: ...
    @property
    def existence_status(self) -> bool | None: ...
    @existence_status.setter
    def existence_status(self, value: bool | None) -> None: ...
    @property
    def children(self) -> set[AttackGraphNode]: ...
    @children.setter
    def children(self, value: set[AttackGraphNode] | Any) -> None: ...
    @property
    def parents(self) -> set[AttackGraphNode]: ...
    @parents.setter
    def parents(self, value: set[AttackGraphNode] | Any) -> None: ...
    @property
    def extras(self) -> dict[str, Any]: ...
    @property
    def detectors(self) -> dict[str, Detector]: ...
    @property
    def full_name(self) -> str: ...
    @property
    def info(self) -> dict[str, Any]: ...
    def to_dict(self) -> dict[str, Any]: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def __reduce__(self) -> tuple[Any, ...]: ...
    def __deepcopy__(self, memo: dict[int, Any]) -> AttackGraphNode: ...

class AttackGraph:
    """A graph of `AttackGraphNode`s generated from a `Model` + a
    `LanguageGraph`."""

    def __init__(
        self,
        lang_graph: LanguageGraph | None,
        model: Model | None = None,
    ) -> None: ...
    @property
    def lang_graph(self) -> LanguageGraph: ...
    @property
    def model(self) -> Model | None: ...
    @model.setter
    def model(self, value: Model | None) -> None: ...
    @property
    def next_node_id(self) -> int: ...
    @property
    def nodes(self) -> Mapping[int, AttackGraphNode]:
        """A lazy read-only `Mapping[int, AttackGraphNode]` view by
        default; freely settable to any `dict[int, AttackGraphNode]`
        (e.g. to hand-build a small graph of detached nodes), in which
        case that dict is returned as-is until `regenerate_graph()` is
        called."""
    @nodes.setter
    def nodes(self, value: dict[int, AttackGraphNode]) -> None: ...
    @property
    def full_name_to_node(self) -> dict[str, AttackGraphNode]: ...
    @property
    def attack_steps(self) -> list[AttackGraphNode]: ...
    @property
    def defense_steps(self) -> list[AttackGraphNode]: ...
    @property
    def detectors(self) -> list[Detector]:
        """Live, mutable flat list of every `Detector` in the graph,
        lazily seeded on first access and never automatically kept in
        sync with each node's own `.detectors` dict afterward."""
    def get_node_by_full_name(self, full_name: str) -> AttackGraphNode: ...
    def regenerate_graph(self) -> None:
        """Full rebuild from `self.model`, discarding every existing
        node. Requires `self.model` to be set."""
    def partially_regenerate_graph(
        self,
        new_assets: set[ModelAsset] | None = None,
        new_associations: set[tuple[ModelAsset, str, ModelAsset]] | None = None,
        removed_assets: set[ModelAsset] | None = None,
        removed_associations: set[tuple[ModelAsset, str, ModelAsset]] | None = None,
    ) -> list[AttackGraphNode]:
        """Incrementally update the graph for the given asset/association
        deltas. Requires `self.model` to be set. Returns the newly
        created nodes."""
    def add_node(
        self,
        lg_attack_step: LanguageGraphAttackStep,
        node_id: int | None = None,
        model_asset: ModelAsset | None = None,
        ttc_dist: dict[str, Any] | None = None,
        existence_status: bool | None = None,
        full_name: str | None = None,
    ) -> AttackGraphNode: ...
    def remove_node(self, node: AttackGraphNode) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...
    def _to_dict(self) -> dict[str, Any]: ...
    def save_to_file(self, filename: str) -> None: ...
    @staticmethod
    def load_from_file(
        filename: str,
        lang_graph: LanguageGraph,
        model: Model | None = None,
    ) -> AttackGraph: ...
    def __reduce__(self) -> tuple[Any, ...]: ...
    def __deepcopy__(self, memo: dict[int, Any]) -> AttackGraph: ...

def create_attack_graph(
    lang: str | LanguageGraph,
    model: str | Model,
) -> AttackGraph:
    """Create and return an attack graph.

    Arguments:
    ---------
    lang    - path to a language file (`.mar` or `.mal`), or an
              already-loaded `LanguageGraph` object
    model   - path to a model file (yaml or json), or an already-loaded
              `Model` object
    """

# ---------------------------------------------------------------------------
# Internal pickling/`__reduce__` helpers - not part of the public API, but
# importable (`maltoolbox._native._rebuild_...`) since `__reduce__` targets
# must be resolvable by name.
# ---------------------------------------------------------------------------

def _rebuild_language_graph_asset(owner: LanguageGraph, ffi_id: int) -> LanguageGraphAsset: ...
def _rebuild_language_graph_attack_step(
    owner: LanguageGraph, asset_name: str, step_name: str
) -> LanguageGraphAttackStep: ...
def _rebuild_attack_graph_node(owner: AttackGraph, id: int) -> AttackGraphNode: ...

def __getattr__(name: str) -> Any: ...
