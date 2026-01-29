"""LanguageGraphAsset functionality
- Represents an asset (type) defined in a MAL language
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from maltoolbox.language.languagegraph_attack_step import LanguageGraphAttackStep

if TYPE_CHECKING:
    from maltoolbox.language.expression_chain import ExpressionsChain
    from maltoolbox.language.languagegraph_assoc import LanguageGraphAssociation

@dataclass
class LanguageGraphAsset:
    """An asset type as defined in the MAL language"""

    name: str
    own_associations: dict[str, LanguageGraphAssociation] = \
        field(default_factory=dict)
    attack_steps: dict[str, LanguageGraphAttackStep] = \
        field(default_factory=dict)
    info: dict = field(default_factory=dict)
    own_super_asset: LanguageGraphAsset | None = None
    own_sub_assets: list[LanguageGraphAsset] = field(default_factory=list)
    own_variables: dict = field(default_factory=dict)
    is_abstract: bool | None = None

    def to_dict(self) -> dict:
        """Convert LanguageGraphAsset to dictionary"""
        node_dict: dict[str, Any] = {
            'name': self.name,
            'associations': {},
            'attack_steps': {},
            'info': self.info,
            'super_asset': self.own_super_asset.name
                if self.own_super_asset else "",
            'sub_assets': [asset.name for asset in self.own_sub_assets],
            'variables': {},
            'is_abstract': self.is_abstract
        }

        for fieldname, assoc in self.own_associations.items():
            node_dict['associations'][fieldname] = assoc.to_dict()
        for attack_step in self.attack_steps.values():
            node_dict['attack_steps'][attack_step.name] = \
                attack_step.to_dict()
        for variable_name, (var_target_asset, var_expr_chain) in \
                self.own_variables.items():
            node_dict['variables'][variable_name] = (
                var_target_asset.name,
                var_expr_chain.to_dict()
            )
        return node_dict

    def __repr__(self) -> str:
        return f'LanguageGraphAsset(name: "{self.name}")'

    def __hash__(self):
        return id(self)

    def is_subasset_of(self, target_asset: LanguageGraphAsset) -> bool:
        """Check if an asset extends the target asset through inheritance.

        Arguments:
        ---------
        target_asset    - the target asset we wish to evaluate if this asset
                          extends

        Return:
        ------
        True if this asset extends the target_asset via inheritance.
        False otherwise.

        """
        current_asset: LanguageGraphAsset | None = self
        while current_asset:
            if current_asset == target_asset:
                return True
            current_asset = current_asset.own_super_asset
        return False

    @cached_property
    def sub_assets(self) -> set[LanguageGraphAsset]:
        """Return a list of all of the assets that directly or indirectly extend
        this asset.

        Return:
        ------
        A list of all of the assets that extend this asset plus itself.

        """
        subassets: list[LanguageGraphAsset] = []
        for subasset in self.own_sub_assets:
            subassets.extend(subasset.sub_assets)

        subassets.extend(self.own_sub_assets)
        subassets.append(self)

        return set(subassets)

    @cached_property
    def super_assets(self) -> list[LanguageGraphAsset]:
        """Return a list of all of the assets that this asset directly or
        indirectly extends.

        Return:
        ------
        A list of all of the assets that this asset extends plus itself.

        """
        current_asset: LanguageGraphAsset | None = self
        superassets = []
        while current_asset:
            superassets.append(current_asset)
            current_asset = current_asset.own_super_asset
        return superassets

    def associations_to(
        self, asset_type: LanguageGraphAsset
    ) -> dict[str, LanguageGraphAssociation]:
        """Return dict of association types that go from self
        to given `asset_type`
        """
        associations_to_asset_type = {}
        for fieldname, association in self.associations.items():
            if association in asset_type.associations.values():
                associations_to_asset_type[fieldname] = association
        return associations_to_asset_type

    @cached_property
    def associations(self) -> dict[str, LanguageGraphAssociation]:
        """Return a list of all of the associations that belong to this asset
        directly or indirectly via inheritance.

        Return:
        ------
        A list of all of the associations that apply to this asset, either
        directly or via inheritance.

        """
        associations = dict(self.own_associations)
        if self.own_super_asset:
            associations |= self.own_super_asset.associations
        return associations

    @property
    def variables(
            self
        ) -> dict[str, tuple[LanguageGraphAsset, ExpressionsChain]]:
        """Return a list of all of the variables that belong to this asset
        directly or indirectly via inheritance.

        Return:
        ------
        A list of all of the variables that apply to this asset, either
        directly or via inheritance.

        """
        all_vars = dict(self.own_variables)
        if self.own_super_asset:
            all_vars |= self.own_super_asset.variables
        return all_vars

    def get_all_common_superassets(
            self, other: LanguageGraphAsset
        ) -> set[str]:
        """Return a set of all common ancestors between this asset
        and the other asset given as parameter
        """
        self_superassets = set(
            asset.name for asset in self.super_assets
        )
        other_superassets = set(
            asset.name for asset in other.super_assets
        )
        return self_superassets.intersection(other_superassets)
