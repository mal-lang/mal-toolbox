"""Detector functionality
- A detector represent a logging rule on an attack step
- It includes a context and a name
"""


from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, eq=True)
class Detector:
    name: str | None
    context: Context
    type: str | None
    tprate: dict | None

    def to_dict(self) -> dict:
        return {
            "context": self.context.to_dict(),
            "name": self.name,
            "type": self.type,
            "tprate": self.tprate,
        }


class Context(dict):
    """Context is part of detectors to provide meta data about attackers"""

    def __init__(self, context) -> None:
        super().__init__(context)
        self._context_dict = context
        for label, asset in context.items():
            setattr(self, label, asset)

    def to_dict(self) -> dict:
        return {label: asset.name for label, asset in self.items()}

    def __str__(self) -> str:
        return str({label: asset.name for label, asset in self._context_dict.items()})

    def __repr__(self) -> str:
        return f"Context({self!s}))"
