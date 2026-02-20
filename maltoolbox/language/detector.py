"""Detector functionality
- A detector represent a logging rule on an attack step
- It includes a context and a name
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from maltoolbox.language.expression_chain import ExpressionsChain
from maltoolbox.language.language_graph_asset import LanguageGraphAsset


@dataclass(frozen=True, eq=True)
class Detector:
    name: str | None
    context: dict[str, Any]
    type: str | None
    tprate: dict | None


@dataclass(frozen=True, eq=True)
class ContextItem:
    asset: LanguageGraphAsset
    attack_step: Optional[str]
    expression_chain: Optional[ExpressionsChain]
