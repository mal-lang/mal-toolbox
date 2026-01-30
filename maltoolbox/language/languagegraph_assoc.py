"""LanguageGraphAssoc functionality
- Represents an association (type) defined in a MAL language
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging
from typing import Any

from maltoolbox.exceptions import LanguageGraphAssociationError
from maltoolbox.language.languagegraph_asset import LanguageGraphAsset

logger = logging.getLogger(__name__)


def link_association_to_assets(
    assoc: LanguageGraphAssociation,
    left_asset: LanguageGraphAsset,
    right_asset: LanguageGraphAsset,
) -> None:
    left_asset.own_associations[assoc.right_field.fieldname] = assoc
    right_asset.own_associations[assoc.left_field.fieldname] = assoc


@dataclass(frozen=True, eq=True)
class LanguageGraphAssociationField:
    """A field in an association"""

    asset: LanguageGraphAsset
    fieldname: str
    minimum: int
    maximum: int


@dataclass(frozen=True, eq=True)
class LanguageGraphAssociation:
    """An association type between asset types as defined in the MAL language
    """

    name: str
    left_field: LanguageGraphAssociationField
    right_field: LanguageGraphAssociationField
    info: dict = field(default_factory=dict, compare=False)

    def to_dict(self) -> dict:
        """Convert LanguageGraphAssociation to dictionary"""
        assoc_dict = {
            'name': self.name,
            'info': self.info,
            'left': {
                'asset': self.left_field.asset.name,
                'fieldname': self.left_field.fieldname,
                'min': self.left_field.minimum,
                'max': self.left_field.maximum
            },
            'right': {
                'asset': self.right_field.asset.name,
                'fieldname': self.right_field.fieldname,
                'min': self.right_field.minimum,
                'max': self.right_field.maximum
            }
        }

        return assoc_dict

    def __repr__(self) -> str:
        return (
            f'LanguageGraphAssociation(name: "{self.name}", '
            f'left_field: {self.left_field}, '
            f'right_field: {self.right_field})'
        )

    @property
    def full_name(self) -> str:
        """Return the full name of the association. This is a combination of the
        association name, left field name, left asset type, right field name,
        and right asset type.
        """
        full_name = '%s_%s_%s' % (
            self.name,
            self.left_field.fieldname,
            self.right_field.fieldname
        )
        return full_name

    def get_field(self, fieldname: str) -> LanguageGraphAssociationField:
        """Return the field that matches the `fieldname` given as parameter.
        """
        if self.right_field.fieldname == fieldname:
            return self.right_field
        return self.left_field

    def contains_fieldname(self, fieldname: str) -> bool:
        """Check if the association contains the field name given as a parameter.

        Arguments:
        ---------
        fieldname   - the field name to look for
        Return True if either of the two field names matches.
        False, otherwise.

        """
        if self.left_field.fieldname == fieldname:
            return True
        if self.right_field.fieldname == fieldname:
            return True
        return False

    def contains_asset(self, asset: Any) -> bool:
        """Check if the association matches the asset given as a parameter. A
        match can either be an explicit one or if the asset given subassets
        either of the two assets that are part of the association.

        Arguments:
        ---------
        asset       - the asset to look for
        Return True if either of the two asset matches.
        False, otherwise.

        """
        if asset.is_subasset_of(self.left_field.asset):
            return True
        if asset.is_subasset_of(self.right_field.asset):
            return True
        return False

    def get_opposite_fieldname(self, fieldname: str) -> str:
        """Return the opposite field name if the association contains the field
        name given as a parameter.

        Arguments:
        ---------
        fieldname   - the field name to look for
        Return the other field name if the parameter matched either of the
        two. None, otherwise.

        """
        if self.left_field.fieldname == fieldname:
            return self.right_field.fieldname
        if self.right_field.fieldname == fieldname:
            return self.left_field.fieldname

        msg = ('Requested fieldname "%s" from association '
               '%s which did not contain it!')
        logger.error(msg, fieldname, self.name)
        raise LanguageGraphAssociationError(msg % (fieldname, self.name))
    
