"""LanguageGraphAttackStep functionality
- Represents a step (type) defined in a MAL language
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Literal, Optional
from dataclasses import dataclass, field
from functools import cached_property

if TYPE_CHECKING:
    from maltoolbox.language.expression_chain import ExpressionsChain
    from maltoolbox.language.language_graph_asset import LanguageGraphAsset


@dataclass
class LanguageGraphAttackStep:
    """An attack step belonging to an asset type in the MAL language."""

    name: str
    type: Literal["or", "and", "defense", "exist", "notExist"]
    asset: LanguageGraphAsset
    causal_mode: Optional[Literal["action", "effect"]] = None
    ttc: dict | None = field(default_factory=dict)
    overrides: bool = False

    own_children: dict[
        LanguageGraphAttackStep, list[ExpressionsChain | None]
    ] = field(default_factory=dict)
    own_parents: dict[
        LanguageGraphAttackStep, list[ExpressionsChain | None]
    ] = field(default_factory=dict)
    info: dict = field(default_factory=dict)
    inherits: Optional[LanguageGraphAttackStep] = None
    own_requires: list[ExpressionsChain] = field(default_factory=list)
    tags: list = field(default_factory=list)
    detectors: dict = field(default_factory=dict)

    def __hash__(self):
        return id(self)

    @property
    def children(self) -> dict[LanguageGraphAttackStep, list[ExpressionsChain | None]]:
        """Return own and inherited children."""
        all_children = dict(self.own_children)
        if self.overrides or not self.inherits:
            return all_children

        for child, chains in self.inherits.children.items():
            if child in all_children:
                all_children[child] += [c for c in chains if c not in all_children[child]]
            else:
                all_children[child] = list(chains)
        return all_children

    @property
    def parents(self) -> None:
        raise NotImplementedError("Fetching parents is not supported.")

    @property
    def full_name(self) -> str:
        """Return a composite name: asset_name:attack_step_name."""
        return f"{self.asset.name}:{self.name}"

    def to_dict(self) -> dict:
        """Serialize the attack step to a dictionary."""
        node_dict: dict[Any, Any] = {
            "name": self.name,
            "type": self.type,
            "asset": self.asset.name,
            "ttc": self.ttc,
            "own_children": {},
            "own_parents": {},
            "info": self.info,
            "overrides": self.overrides,
            "inherits": self.inherits.full_name if self.inherits else None,
            "tags": list(self.tags),
            "detectors": {label: detector.to_dict() for label, detector in self.detectors.items()},
        }

        # Children
        for child, chains in self.own_children.items():
            node_dict["own_children"][child.full_name] = [
                chain.to_dict() if chain else None for chain in chains
            ]

        # Parents
        for parent, chains in self.own_parents.items():
            node_dict["own_parents"][parent.full_name] = [
                chain.to_dict() if chain else None for chain in chains
            ]

        # Requires
        if self.own_requires:
            node_dict["requires"] = [req.to_dict() for req in self.own_requires]

        return node_dict

    @cached_property
    def requires(self) -> list[ExpressionsChain]:
        """Return own and inherited requirements."""
        reqs = list(self.own_requires)
        if self.inherits:
            reqs.extend(self.inherits.requires)
        return reqs
