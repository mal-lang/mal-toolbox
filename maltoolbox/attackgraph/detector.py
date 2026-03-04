from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maltoolbox.attackgraph.node import AttackGraphNode

@dataclass(frozen=True, eq=True)
class Detector:
    name: str | None
    node: AttackGraphNode
    potential_context: dict[str, set[AttackGraphNode]]
    tprate: float = 1.0
    fprate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "node": self.node,
            "potential_context": self.potential_context,
            "tprate": self.tprate
        }
