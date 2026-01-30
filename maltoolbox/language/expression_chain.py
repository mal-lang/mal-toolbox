"""Expression chain functionality
- Used to specify association paths and operations to reach children/parents of steps
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import json
import logging
from typing import Any

from maltoolbox.exceptions import LanguageGraphAssociationError, LanguageGraphException
from maltoolbox.language.language_graph_assoc import LanguageGraphAssociation

if TYPE_CHECKING:
    from maltoolbox.language.languagegraph import LanguageGraph

logger = logging.getLogger(__name__)

class ExpressionsChain:
    """A series of linked step expressions that specify the association path and
    operations to take to reach the child/parent attack step.
    """

    def __init__(self,
            type: str,
            left_link: ExpressionsChain | None = None,
            right_link: ExpressionsChain | None = None,
            sub_link: ExpressionsChain | None = None,
            fieldname: str | None = None,
            association=None,
            subtype=None
        ):
        self.type = type
        self.left_link: ExpressionsChain | None = left_link
        self.right_link: ExpressionsChain | None = right_link
        self.sub_link: ExpressionsChain | None = sub_link
        self.fieldname: str | None = fieldname
        self.association: LanguageGraphAssociation | None = association
        self.subtype: Any | None = subtype

    def to_dict(self) -> dict:
        """Convert ExpressionsChain to dictionary"""
        match (self.type):
            case 'union' | 'intersection' | 'difference' | 'collect':
                return {
                    self.type: {
                        'left': self.left_link.to_dict()
                                if self.left_link else {},
                        'right': self.right_link.to_dict()
                                 if self.right_link else {}
                    },
                    'type': self.type
                }

            case 'field':
                if not self.association:
                    raise LanguageGraphAssociationError(
                        "Missing association for expressions chain"
                    )
                if self.fieldname == self.association.left_field.fieldname:
                    asset_type = self.association.left_field.asset.name
                elif self.fieldname == self.association.right_field.fieldname:
                    asset_type = self.association.right_field.asset.name
                else:
                    raise LanguageGraphException(
                        'Failed to find fieldname "%s" in association:\n%s' %
                        (
                            self.fieldname,
                            json.dumps(self.association.to_dict(),
                                indent=2)
                        )
                    )

                return {
                    self.association.name:
                    {
                        'fieldname': self.fieldname,
                        'asset type': asset_type
                    },
                    'type': self.type
                }

            case 'transitive':
                if not self.sub_link:
                    raise LanguageGraphException(
                        "No sub link for transitive expressions chain"
                    )
                return {
                    'transitive': self.sub_link.to_dict(),
                    'type': self.type
                }

            case 'subType':
                if not self.subtype:
                    raise LanguageGraphException(
                        "No subtype for expressions chain"
                    )
                if not self.sub_link:
                    raise LanguageGraphException(
                        "No sub link for subtype expressions chain"
                    )
                return {
                    'subType': self.subtype.name,
                    'expression': self.sub_link.to_dict(),
                    'type': self.type
                }

            case _:
                msg = 'Unknown associations chain element %s!'
                logger.error(msg, self.type)
                raise LanguageGraphAssociationError(msg % self.type)

    @classmethod
    def _from_dict(cls,
            serialized_expr_chain: dict,
            lang_graph: LanguageGraph,
        ) -> ExpressionsChain | None:
        """Create ExpressionsChain from dict
        Args:
        serialized_expr_chain   - expressions chain in dict format
        lang_graph              - the LanguageGraph that contains the assets,
                                  associations, and attack steps relevant for
                                  the expressions chain
        """
        if serialized_expr_chain is None or not serialized_expr_chain:
            return None

        if 'type' not in serialized_expr_chain:
            logger.debug(json.dumps(serialized_expr_chain, indent=2))
            msg = 'Missing expressions chain type!'
            logger.error(msg)
            raise LanguageGraphAssociationError(msg)

        expr_chain_type = serialized_expr_chain['type']
        match (expr_chain_type):
            case 'union' | 'intersection' | 'difference' | 'collect':
                left_link = cls._from_dict(
                    serialized_expr_chain[expr_chain_type]['left'],
                    lang_graph
                )
                right_link = cls._from_dict(
                    serialized_expr_chain[expr_chain_type]['right'],
                    lang_graph
                )
                new_expr_chain = ExpressionsChain(
                    type=expr_chain_type,
                    left_link=left_link,
                    right_link=right_link
                )
                return new_expr_chain

            case 'field':
                assoc_name = list(serialized_expr_chain.keys())[0]
                target_asset = lang_graph.assets[
                    serialized_expr_chain[assoc_name]['asset type']]
                fieldname = serialized_expr_chain[assoc_name]['fieldname']

                association = None
                for assoc in target_asset.associations.values():
                    if assoc.contains_fieldname(fieldname) and \
                            assoc.name == assoc_name:
                        association = assoc
                        break

                if association is None:
                    msg = 'Failed to find association "%s" with '\
                        'fieldname "%s"'
                    logger.error(msg, assoc_name, fieldname)
                    raise LanguageGraphException(
                        msg % (assoc_name, fieldname)
                    )

                new_expr_chain = ExpressionsChain(
                    type='field',
                    association=association,
                    fieldname=fieldname
                )
                return new_expr_chain

            case 'transitive':
                sub_link = cls._from_dict(
                    serialized_expr_chain['transitive'],
                    lang_graph
                )
                new_expr_chain = ExpressionsChain(
                    type='transitive',
                    sub_link=sub_link
                )
                return new_expr_chain

            case 'subType':
                sub_link = cls._from_dict(
                    serialized_expr_chain['expression'],
                    lang_graph
                )
                subtype_name = serialized_expr_chain['subType']
                if subtype_name in lang_graph.assets:
                    subtype_asset = lang_graph.assets[subtype_name]
                else:
                    msg = 'Failed to find subtype %s'
                    logger.error(msg, subtype_name)
                    raise LanguageGraphException(msg % subtype_name)

                new_expr_chain = ExpressionsChain(
                    type='subType',
                    sub_link=sub_link,
                    subtype=subtype_asset
                )
                return new_expr_chain

            case _:
                msg = 'Unknown expressions chain type %s!'
                logger.error(msg, serialized_expr_chain['type'])
                raise LanguageGraphAssociationError(
                    msg % serialized_expr_chain['type']
                )

    def __repr__(self) -> str:
        return str(self.to_dict())
