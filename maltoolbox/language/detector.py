"""Detector functionality
- A detector represent a logging rule on an attack step
- It includes a context and a name
"""

from __future__ import annotations
from dataclasses import dataclass

from maltoolbox.language.expression_chain import ExpressionsChain
from maltoolbox.language.language_graph_asset import LanguageGraphAsset

@dataclass(frozen=True, eq=True)
class Detector:
    name: str | None
    context: dict[str, ContextItem]
    type: str | None
    tprate: dict | None

    def to_dict(self) -> dict:
        """Convert Detector to dictionary"""
        return {
            "name": self.name,
            "context": {k: v.to_dict() for k, v in self.context.items()},
            "type": self.type,
            "tprate": self.tprate,
        }

@dataclass(frozen=True, eq=True)
class ContextItem:
    """Represents a single item in the context of a detector, which specifies
    the label and attack step that the detector is associated with.
    """

    label: str
    asset_type: LanguageGraphAsset
    attack_step_name: str | None
    expr: ExpressionsChain | None

    def to_dict(self) -> dict:
        """Convert ContextItem to dictionary"""
        return {
            "label": self.label,
            "asset_type": self.asset_type.name,
            "attack_step_name": self.attack_step_name,
            "expr": self.expr.to_dict() if self.expr else None,
        }
