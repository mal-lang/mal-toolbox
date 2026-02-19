"""Expression chain functionality
- Used to specify association paths and operations to reach children/parents of steps

ExpressionsChain represents a tree of operations describing how to traverse
associations in a language graph. Each node has a type that determines:
- how it combines other expressions (union, intersection, difference, collect)
- how it follows a graph association (field)
- how it modifies traversal semantics (transitive)
- how it constrains by subtype (subType)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from dataclasses import dataclass
from enum import Enum

from maltoolbox.exceptions import (
    LanguageGraphAssociationError,
    LanguageGraphException,
)
from maltoolbox.language.language_graph_assoc import LanguageGraphAssociation

if TYPE_CHECKING:
    from maltoolbox.language.languagegraph import LanguageGraph


class ExprType(str, Enum):
    UNION = "union"
    INTERSECTION = "intersection"
    DIFFERENCE = "difference"
    COLLECT = "collect"
    FIELD = "field"
    TRANSITIVE = "transitive"
    SUBTYPE = "subType"

    def is_binary(self) -> bool:
        return self in {
            ExprType.UNION,
            ExprType.INTERSECTION,
            ExprType.DIFFERENCE,
            ExprType.COLLECT,
        }


@dataclass
class ExpressionsChain:
    """A series of linked step expressions that specify the association path and
    operations to take to reach the child/parent attack step.
    """

    type: ExprType
    left_link: ExpressionsChain | None = None
    right_link: ExpressionsChain | None = None
    sub_link: ExpressionsChain | None = None
    fieldname: str | None = None
    association: LanguageGraphAssociation | None = None
    subtype: Any | None = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.type.is_binary():
            return

        if self.type == ExprType.FIELD:
            if not self.association or not self.fieldname:
                raise ValueError("FIELD requires association and fieldname")

        if self.type == ExprType.TRANSITIVE:
            if not self.sub_link:
                raise ValueError("TRANSITIVE requires sub_link")

        if self.type == ExprType.SUBTYPE:
            if not self.sub_link or not self.subtype:
                raise ValueError("SUBTYPE requires sub_link and subtype")

    def to_dict(self) -> dict:
        if self.type.is_binary():
            return self._binary_to_dict()

        if self.type == ExprType.FIELD:
            return self._field_to_dict()

        if self.type == ExprType.TRANSITIVE:
            return self._transitive_to_dict()

        if self.type == ExprType.SUBTYPE:
            return self._subtype_to_dict()

        raise LanguageGraphAssociationError(
            f"Unknown expressions chain element {self.type}"
        )

    def _binary_to_dict(self) -> dict:
        return {
            self.type.value: {
                "left": self.left_link.to_dict() if self.left_link else {},
                "right": self.right_link.to_dict() if self.right_link else {},
            },
            "type": self.type.value,
        }

    def _transitive_to_dict(self) -> dict:
        return {
            "transitive": self.sub_link.to_dict(),
            "type": self.type.value,
        }

    def _subtype_to_dict(self) -> dict:
        return {
            "subType": self.subtype.name,
            "expression": self.sub_link.to_dict(),
            "type": self.type.value,
        }

    def _field_to_dict(self) -> dict:
        asset_type = self._resolve_field_asset_type()

        return {
            self.association.name: {
                "fieldname": self.fieldname,
                "asset type": asset_type,
            },
            "type": self.type.value,
        }

    def _resolve_field_asset_type(self) -> str:
        if self.fieldname == self.association.left_field.fieldname:
            return self.association.left_field.asset.name
        if self.fieldname == self.association.right_field.fieldname:
            return self.association.right_field.asset.name

        raise LanguageGraphException(
            f'Field "{self.fieldname}" not found in association '
            f"{self.association.name}"
        )

    @classmethod
    def _parse_binary(
        cls,
        data: dict,
        lang_graph: LanguageGraph,
        expr_type: ExprType,
    ) -> ExpressionsChain:
        payload = data[expr_type.value]

        left_link = cls._from_dict(payload.get("left"), lang_graph)
        right_link = cls._from_dict(payload.get("right"), lang_graph)

        return cls(
            type=expr_type,
            left_link=left_link,
            right_link=right_link,
        )

    @classmethod
    def _parse_field(
        cls,
        data: dict,
        lang_graph: LanguageGraph,
    ) -> ExpressionsChain:
        assoc_keys = [k for k in data.keys() if k != "type"]
        if len(assoc_keys) != 1:
            raise LanguageGraphException("Invalid field expression format")

        assoc_name = assoc_keys[0]
        field_data = data[assoc_name]

        asset_name = field_data["asset type"]
        fieldname = field_data["fieldname"]

        try:
            target_asset = lang_graph.assets[asset_name]
        except KeyError:
            raise LanguageGraphException(
                f'Unknown asset type "{asset_name}"'
            )

        association = cls._resolve_association(
            target_asset,
            assoc_name,
            fieldname,
        )

        return cls(
            type=ExprType.FIELD,
            association=association,
            fieldname=fieldname,
        )

    @staticmethod
    def _resolve_association(
        asset,
        assoc_name: str,
        fieldname: str,
    ):
        for assoc in asset.associations.values():
            if assoc.name == assoc_name and assoc.contains_fieldname(fieldname):
                return assoc

        raise LanguageGraphException(
            f'Failed to find association "{assoc_name}" '
            f'with fieldname "{fieldname}"'
        )

    @classmethod
    def _parse_transitive(
        cls,
        data: dict,
        lang_graph: LanguageGraph,
    ) -> ExpressionsChain:
        sub_link = cls._from_dict(
            data.get("transitive"),
            lang_graph,
        )

        return cls(
            type=ExprType.TRANSITIVE,
            sub_link=sub_link,
        )

    @classmethod
    def _parse_subtype(
        cls,
        data: dict,
        lang_graph: LanguageGraph,
    ) -> ExpressionsChain:
        sub_link = cls._from_dict(
            data.get("expression"),
            lang_graph,
        )

        subtype_name = data["subType"]

        try:
            subtype_asset = lang_graph.assets[subtype_name]
        except KeyError:
            raise LanguageGraphException(
                f"Failed to find subtype {subtype_name}"
            )

        return cls(
            type=ExprType.SUBTYPE,
            sub_link=sub_link,
            subtype=subtype_asset,
        )

    @classmethod
    def _from_dict(
        cls,
        serialized_expr_chain: dict,
        lang_graph: LanguageGraph,
    ) -> ExpressionsChain | None:
        if not serialized_expr_chain:
            return None

        try:
            expr_chain_type = ExprType(serialized_expr_chain["type"])
        except KeyError:
            raise LanguageGraphAssociationError(
                "Missing expressions chain type"
            )

        if expr_chain_type.is_binary():
            return cls._parse_binary(
                serialized_expr_chain,
                lang_graph,
                expr_chain_type,
            )

        if expr_chain_type == ExprType.FIELD:
            return cls._parse_field(
                serialized_expr_chain,
                lang_graph,
            )

        if expr_chain_type == ExprType.TRANSITIVE:
            return cls._parse_transitive(
                serialized_expr_chain,
                lang_graph,
            )

        if expr_chain_type == ExprType.SUBTYPE:
            return cls._parse_subtype(
                serialized_expr_chain,
                lang_graph,
            )

        raise LanguageGraphAssociationError(
            f"Unknown expressions chain type "
            f"{serialized_expr_chain['type']}"
        )

    def __repr__(self) -> str:
        return str(self.to_dict())
