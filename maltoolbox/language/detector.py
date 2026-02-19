"""Detector functionality
- A detector represent a logging rule on an attack step
- It includes a context and a name
"""


from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, eq=True)
class Detector:
    name: str | None
    context: dict[str, Any]
    type: str | None
    tprate: dict | None

    def to_dict(self) -> dict:
        return {
            "context": self.context.to_dict(),
            "name": self.name,
            "type": self.type,
            "tprate": self.tprate,
        }

