"""LanguageGraphAttackStep functionality
- Represents a step (type) defined in a MAL language
"""

from __future__ import annotations

from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal


class AttackStepType(Enum):
    OR = 1
    AND = 2
    DEFENSE = 3
    EXIST = 4
    NOT_EXIST = 5
    NOTEXIST = 5 # noqa: PIE796 (to enable: AttackStepType['NOTEXIST'])

    def __str__(self):
        return self.name.lower().replace('_e', 'E')


if TYPE_CHECKING:
    from maltoolbox.language.expression_chain import ExpressionsChain
    from maltoolbox.language.language_graph_asset import LanguageGraphAsset
    from maltoolbox.language.language_graph_detector import LanguageGraphDetector
    from maltoolbox.language.language_graph_model_effect import LanguageGraphModelEffect

class LanguageGraphAttackStep:
    """An attack step belonging to an asset type in the MAL language."""

    name: str
    type: AttackStepType
    asset: LanguageGraphAsset
    causal_mode: Literal['action', 'effect'] | None
    ttc: dict | None
    overrides: bool

    own_children: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]]
    own_parents: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]]

    own_additive_model_effects: list[LanguageGraphModelEffect]
    own_subtractive_model_effects: list[LanguageGraphModelEffect]
    info: dict
    inherits: LanguageGraphAttackStep | None
    own_requires: list[ExpressionsChain]
    tags: list
    detectors: dict[str, LanguageGraphDetector]

    def __init__(
        self, name: str,
        type: AttackStepType | str,
        asset: LanguageGraphAsset,
        causal_mode: Literal['action', 'effect'] | None = None,
        ttc: dict | None | bool = False,
        overrides: bool = False,
        own_children: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]] | None = None,
        own_parents: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]] | None = None,
        own_additive_model_effects: list[LanguageGraphModelEffect] | None = None,
        own_subtractive_model_effects: list[LanguageGraphModelEffect] | None = None,
        info: dict | None = None,
        inherits: LanguageGraphAttackStep | None = None, 
        own_requires: list[ExpressionsChain] | None = None,
        tags: list | None = None,
        detectors: dict[str, LanguageGraphDetector] | None = None
    ):
        self.name = name
        self.type = AttackStepType[type.upper()] if isinstance(type, str) else type
        self.asset = asset 
        self.causal_mode = causal_mode
        self.ttc = {} if isinstance(ttc, bool) else ttc
        self.overrides = overrides
        self.own_children = {} if own_children is None else own_children
        self.own_parents = {} if own_parents is None else own_parents
        self.own_additive_model_effects = [] if own_additive_model_effects is None else own_additive_model_effects
        self.own_subtractive_model_effects = [] if own_subtractive_model_effects is None else own_subtractive_model_effects
        self.info = {} if info is None else info
        self.inherits = inherits
        self.own_requires = [] if own_requires is None else own_requires
        self.tags = [] if tags is None else tags
        self.detectors = {} if detectors is None else detectors

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
                all_children[child] += [
                    c for c in chains if c not in all_children[child]
                ]
            else:
                all_children[child] = list(chains)
        return all_children

    @property
    def parents(self) -> None:
        raise NotImplementedError("Fetching parents is not supported.")
    
    @property
    def additive_model_effects(self) -> list[LanguageGraphModelEffect]:
        """Return own and inherited additive model effects."""
        all_effects = list(self.own_additive_model_effects)
        # TODO: Figure out if self.overrides is correct here or only for "static" steps
        if self.overrides or not self.inherits:
            return all_effects

        all_effects += self.inherits.additive_model_effects
        return all_effects
    
    @property
    def subtractive_model_effects(self) -> list[LanguageGraphModelEffect]:
        """Return own and inherited subtractive model effects."""
        all_effects = list(self.own_subtractive_model_effects)
        if self.overrides or not self.inherits:
            return all_effects

        all_effects += self.inherits.subtractive_model_effects
        return all_effects

    @property
    def full_name(self) -> str:
        """Return a composite name: asset_name:attack_step_name."""
        return f'{self.asset.name}:{self.name}'

    def to_dict(self) -> dict:
        """Serialize the attack step to a dictionary."""
        node_dict: dict[Any, Any] = {
            'name': self.name,
            'type': str(self.type),
            'asset': self.asset.name,
            'ttc': self.ttc,
            'own_children': {},
            'own_parents': {},
            'info': self.info,
            'overrides': self.overrides,
            'inherits': self.inherits.full_name if self.inherits else None,
            'tags': list(self.tags),
            'detectors': {
                label: detector.to_dict() for label, detector in self.detectors.items()
            },
        }

        # Children
        for child, chains in self.own_children.items():
            node_dict['own_children'][child.full_name] = [
                chain.to_dict() if chain else None for chain in chains
            ]

        # Parents
        for parent, chains in self.own_parents.items():
            node_dict['own_parents'][parent.full_name] = [
                chain.to_dict() if chain else None for chain in chains
            ]

        # Requires
        if self.own_requires:
            node_dict['requires'] = [req.to_dict() for req in self.own_requires]

        return node_dict

    @cached_property
    def requires(self) -> list[ExpressionsChain]:
        """Return own and inherited requirements."""
        reqs = list(self.own_requires)
        if self.inherits:
            reqs.extend(self.inherits.requires)
        return reqs
