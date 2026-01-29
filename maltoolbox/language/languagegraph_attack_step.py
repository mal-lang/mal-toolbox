"""LanguageGraphAttackStep functionality
- Represents a step (type) defined in a MAL language
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Literal, Optional

if TYPE_CHECKING:
    from maltoolbox.language.expression_chain import ExpressionsChain
    from maltoolbox.language.languagegraph_asset import LanguageGraphAsset

@dataclass
class LanguageGraphAttackStep:
    """An attack step belonging to an asset type in the MAL language"""

    name: str
    type: Literal["or", "and", "defense", "exist", "notExist"]
    asset: LanguageGraphAsset
    causal_mode: Optional[Literal["action", "effect"]] = None
    ttc: dict | None = field(default_factory=dict)
    overrides: bool = False

    own_children: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]] = (
        field(default_factory=dict)
    )
    own_parents: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]] = (
        field(default_factory=dict)
    )
    info: dict = field(default_factory=dict)
    inherits: LanguageGraphAttackStep | None = None
    own_requires: list[ExpressionsChain] = field(default_factory=list)
    tags: list = field(default_factory=list)
    detectors: dict = field(default_factory=dict)

    def __hash__(self):
        return id(self)

    @property
    def children(self) -> dict[
        LanguageGraphAttackStep, list[ExpressionsChain | None]
    ]:
        """Get all (both own and inherited) children of a LanguageGraphAttackStep
        """
        all_children = dict(self.own_children)

        if self.overrides:
            # Override overrides the children
            return all_children

        if not self.inherits:
            return all_children

        for child_step, chains in self.inherits.children.items():
            if child_step in all_children:
                all_children[child_step] += [
                    chain for chain in chains
                    if chain not in all_children[child_step]
                ]
            else:
                all_children[child_step] = chains

        return all_children

    @property
    def parents(self) -> None:
        raise NotImplementedError(
            "Can not fetch parents of a LanguageGraphAttackStep"
        )

    @property
    def full_name(self) -> str:
        """Return the full name of the attack step. This is a combination of the
        asset type name to which the attack step belongs and attack step name
        itself.
        """
        full_name = self.asset.name + ':' + self.name
        return full_name

    def to_dict(self) -> dict:
        node_dict: dict[Any, Any] = {
            'name': self.name,
            'type': self.type,
            'asset': self.asset.name,
            'ttc': self.ttc,
            'own_children': {},
            'own_parents': {},
            'info': self.info,
            'overrides': self.overrides,
            'inherits': self.inherits.full_name if self.inherits else None,
            'tags': list(self.tags),
            'detectors': {label: detector.to_dict() for label, detector in
            self.detectors.items()},
        }

        for child, expr_chains in self.own_children.items():
            node_dict['own_children'][child.full_name] = []
            for chain in expr_chains:
                if chain:
                    node_dict['own_children'][child.full_name].append(chain.to_dict())
                else:
                    node_dict['own_children'][child.full_name].append(None)
        for parent, expr_chains in self.own_children.items():
            node_dict['own_parents'][parent.full_name] = []
            for chain in expr_chains:
                if chain:
                    node_dict['own_parents'][parent.full_name].append(chain.to_dict())
                else:
                    node_dict['own_parents'][parent.full_name].append(None)

        if self.own_requires:
            node_dict['requires'] = []
            for requirement in self.own_requires:
                node_dict['requires'].append(requirement.to_dict())

        return node_dict

    @cached_property
    def requires(self):
        if not hasattr(self, 'own_requires'):
            requirements = []
        else:
            requirements = self.own_requires

        if self.inherits:
            requirements.extend(self.inherits.requires)
        return requirements
