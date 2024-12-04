"""
MAL-Toolbox Language Classes Factory Module
Uses python_jsonschema_objects to generate python classes from a MAL language
"""

from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING
from ..model import ModelAsset, ModelAssociation

import python_jsonschema_objects as pjs

if TYPE_CHECKING:
    from typing import Literal, Optional, TypeAlias
    from maltoolbox.language import LanguageGraph
    from python_jsonschema_objects.classbuilder import ProtocolBase

    SchemaGeneratedClass: TypeAlias = ProtocolBase

logger = logging.getLogger(__name__)


class LanguageClassesFactory():
    def __init__(self, lang_graph: LanguageGraph):
        self.lang_graph = lang_graph

    def get_asset_class(self, asset_type):
        lg_asset = self.lang_graph.assets[asset_type]

        return type(f"Asset_{asset_type}", (ModelAsset,), {"lg_asset": lg_asset})

    def get_association_class(self, assoc_name):
        lg_assoc = self.lang_graph.associations[assoc_name]

        return type(f"Assoc_{assoc_name}", (ModelAssociation,),
                    {"lg_assoc": lg_assoc, "type": assoc_name})


class LanguageClassesFactory2:
    # TODO: needed by ingestors/translators
    def get_association_by_signature(
        self, assoc_name: str, left_asset: str, right_asset: str
    ) -> Optional[str]:
        """
        Get association name based on its signature. This is primarily
        relevant for getting the exact association full name when multiple
        associations with the same name exist.

        Arguments:
        assoc_name          - the association name
        left_asset          - the name of the left asset type
        right_asset         - the name of the right asset type

        Return: The matching association name if a match is found.
        None if there is no match.
        """
        lang_assocs_entries = self.json_schema["definitions"]["LanguageAssociation"][
            "definitions"
        ]
        if not assoc_name in lang_assocs_entries:
            raise LookupError(
                'Failed to find "%s" association in the language json '
                "schema." % assoc_name
            )
        assoc_entry = lang_assocs_entries[assoc_name]
        # If the association has a oneOf property it should always have more
        # than just one alternative, but check just in case
        if "definitions" in assoc_entry and len(assoc_entry["definitions"]) > 1:
            full_name = "%s_%s_%s" % (assoc_name, left_asset, right_asset)
            full_name_flipped = "%s_%s_%s" % (assoc_name, right_asset, left_asset)
            if not full_name in assoc_entry["definitions"]:
                if not full_name_flipped in assoc_entry["definitions"]:
                    raise LookupError(
                        'Failed to find "%s" or "%s" association in the '
                        "language json schema." % (full_name, full_name_flipped)
                    )
                else:
                    return full_name_flipped
            else:
                return full_name
        else:
            return assoc_name
