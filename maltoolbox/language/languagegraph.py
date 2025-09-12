"""
MAL-Toolbox Language Graph Module
"""

from __future__ import annotations

import logging
import json
import zipfile

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Literal, Optional

from maltoolbox.file_utils import (
    load_dict_from_yaml_file, load_dict_from_json_file,
    save_dict_to_file
)
from .compiler import MalCompiler
from ..exceptions import (
    LanguageGraphAssociationError,
    LanguageGraphStepExpressionError,
    LanguageGraphException,
    LanguageGraphSuperAssetNotFoundError
)

logger = logging.getLogger(__name__)


def disaggregate_attack_step_full_name(
        attack_step_full_name: str) -> list[str]:
    return attack_step_full_name.split(':')


@dataclass
class Detector:
    name: Optional[str]
    context: Context
    type: Optional[str]
    tprate: Optional[dict]

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
        return f"Context({str(self)}))"

@dataclass
class LanguageGraphAsset:
    """An asset type as defined in the MAL language"""
    name: str
    own_associations: dict[str, LanguageGraphAssociation] = \
        field(default_factory = dict)
    attack_steps: dict[str, LanguageGraphAttackStep] = \
        field(default_factory = dict)
    info: dict = field(default_factory = dict)
    own_super_asset: Optional[LanguageGraphAsset] = None
    own_sub_assets: set[LanguageGraphAsset] = field(default_factory = set)
    own_variables: dict = field(default_factory = dict)
    is_abstract: Optional[bool] = None


    def to_dict(self) -> dict:
        """Convert LanguageGraphAsset to dictionary"""
        node_dict: dict[str, Any] = {
            'name': self.name,
            'associations': {},
            'attack_steps': {},
            'info': self.info,
            'super_asset': self.own_super_asset.name \
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
        return hash(self.name)


    def is_subasset_of(self, target_asset: LanguageGraphAsset) -> bool:
        """
        Check if an asset extends the target asset through inheritance.

        Arguments:
        target_asset    - the target asset we wish to evaluate if this asset
                          extends

        Return:
        True if this asset extends the target_asset via inheritance.
        False otherwise.
        """
        current_asset: Optional[LanguageGraphAsset] = self
        while current_asset:
            if current_asset == target_asset:
                return True
            current_asset = current_asset.own_super_asset
        return False


    @cached_property
    def sub_assets(self) -> set[LanguageGraphAsset]:
        """
        Return a list of all of the assets that directly or indirectly extend
        this asset.

        Return:
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
        """
        Return a list of all of the assets that this asset directly or
        indirectly extends.

        Return:
        A list of all of the assets that this asset extends plus itself.
        """
        current_asset: Optional[LanguageGraphAsset] = self
        superassets = []
        while current_asset:
            superassets.append(current_asset)
            current_asset = current_asset.own_super_asset
        return superassets


    @cached_property
    def associations(self) -> dict[str, LanguageGraphAssociation]:
        """
        Return a list of all of the associations that belong to this asset
        directly or indirectly via inheritance.

        Return:
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
        """
        Return a list of all of the variables that belong to this asset
        directly or indirectly via inheritance.

        Return:
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
        and the other asset given as parameter"""
        self_superassets = set(
            asset.name for asset in self.super_assets
        )
        other_superassets = set(
            asset.name for asset in other.super_assets
        )
        return self_superassets.intersection(other_superassets)


@dataclass(frozen=True)
class LanguageGraphAssociationField:
    """A field in an association"""
    asset: LanguageGraphAsset
    fieldname: str
    minimum: int
    maximum: int


@dataclass(frozen=True, eq=True)
class LanguageGraphAssociation:
    """
    An association type between asset types as defined in the MAL language
    """
    name: str
    left_field: LanguageGraphAssociationField
    right_field: LanguageGraphAssociationField
    info: dict = field(default_factory = dict, compare=False)

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
        """
        Return the full name of the association. This is a combination of the
        association name, left field name, left asset type, right field name,
        and right asset type.
        """
        full_name = '%s_%s_%s' % (
            self.name,\
            self.left_field.fieldname,\
            self.right_field.fieldname
        )
        return full_name


    def get_field(self, fieldname: str) -> LanguageGraphAssociationField:
        """
        Return the field that matches the `fieldname` given as parameter.
        """
        if self.right_field.fieldname == fieldname:
            return self.right_field
        return self.left_field


    def contains_fieldname(self, fieldname: str) -> bool:
        """
        Check if the association contains the field name given as a parameter.

        Arguments:
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
        """
        Check if the association matches the asset given as a parameter. A
        match can either be an explicit one or if the asset given subassets
        either of the two assets that are part of the association.

        Arguments:
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
        """
        Return the opposite field name if the association contains the field
        name given as a parameter.

        Arguments:
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


@dataclass
class LanguageGraphAttackStep:
    """
    An attack step belonging to an asset type in the MAL language
    """
    name: str
    type: Literal["or", "and", "defense", "exist", "notExist"]
    asset: LanguageGraphAsset
    ttc: Optional[dict] = field(default_factory = dict)
    overrides: bool = False

    own_children: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]] = (
        field(default_factory = dict)
    )
    own_parents: dict[LanguageGraphAttackStep, list[ExpressionsChain | None]] = (
        field(default_factory = dict)
    )
    info: dict = field(default_factory = dict)
    inherits: Optional[LanguageGraphAttackStep] = None
    own_requires: list[ExpressionsChain] = field(default_factory=list)
    tags: list = field(default_factory = list)
    detectors: dict = field(default_factory = lambda: {})


    def __hash__(self):
        return hash(self.full_name)

    @property
    def children(self) -> dict[
        LanguageGraphAttackStep, list[ExpressionsChain | None]
    ]:
        """
        Get all (both own and inherited) children of a LanguageGraphAttackStep
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
        """
        Return the full name of the attack step. This is a combination of the
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


    def __repr__(self) -> str:
        return str(self.to_dict())


class ExpressionsChain:
    """
    A series of linked step expressions that specify the association path and
    operations to take to reach the child/parent attack step.
    """
    def __init__(self,
            type: str,
            left_link: Optional[ExpressionsChain] = None,
            right_link: Optional[ExpressionsChain] = None,
            sub_link: Optional[ExpressionsChain] = None,
            fieldname: Optional[str] = None,
            association = None,
            subtype = None
        ):
        self.type = type
        self.left_link: Optional[ExpressionsChain] = left_link
        self.right_link: Optional[ExpressionsChain] = right_link
        self.sub_link: Optional[ExpressionsChain] = sub_link
        self.fieldname: Optional[str] = fieldname
        self.association: Optional[LanguageGraphAssociation] = association
        self.subtype: Optional[Any] = subtype


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
                                indent = 2)
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
        ) -> Optional[ExpressionsChain]:
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
            logger.debug(json.dumps(serialized_expr_chain, indent = 2))
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
                    type = expr_chain_type,
                    left_link = left_link,
                    right_link = right_link
                )
                return new_expr_chain

            case 'field':
                assoc_name = list(serialized_expr_chain.keys())[0]
                target_asset = lang_graph.assets[\
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
                    type = 'field',
                    association = association,
                    fieldname = fieldname
                )
                return new_expr_chain

            case 'transitive':
                sub_link = cls._from_dict(
                    serialized_expr_chain['transitive'],
                    lang_graph
                )
                new_expr_chain = ExpressionsChain(
                    type = 'transitive',
                    sub_link = sub_link
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
                    type = 'subType',
                    sub_link = sub_link,
                    subtype = subtype_asset
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


class LanguageGraph():
    """Graph representation of a MAL language"""
    def __init__(self, lang: Optional[dict] = None):
        self.assets: dict[str, LanguageGraphAsset] = {}
        if lang is not None:
            self._lang_spec: dict = lang
            self.metadata = {
                "version": lang["defines"]["version"],
                "id": lang["defines"]["id"],
            }
            self._generate_graph()


    def __repr__(self) -> str:
        return (f'LanguageGraph(id: "{self.metadata.get("id", "N/A")}", '
            f'version: "{self.metadata.get("version", "N/A")}")')


    @classmethod
    def from_mal_spec(cls, mal_spec_file: str) -> LanguageGraph:
        """
        Create a LanguageGraph from a .mal file (a MAL spec).

        Arguments:
        mal_spec_file   -   the path to the .mal file
        """
        logger.info("Loading mal spec %s", mal_spec_file)
        return LanguageGraph(MalCompiler().compile(mal_spec_file))


    @classmethod
    def from_mar_archive(cls, mar_archive: str) -> LanguageGraph:
        """
        Create a LanguageGraph from a ".mar" archive provided by malc
        (https://github.com/mal-lang/malc).

        Arguments:
        mar_archive     -   the path to a ".mar" archive
        """
        logger.info('Loading mar archive %s', mar_archive)
        with zipfile.ZipFile(mar_archive, 'r') as archive:
            langspec = archive.read('langspec.json')
            return LanguageGraph(json.loads(langspec))

    def _to_dict(self):
        """Converts LanguageGraph into a dict"""

        logger.debug(
            'Serializing %s assets.', len(self.assets.items())
        )

        serialized_graph = {'metadata': self.metadata}
        for asset in self.assets.values():
            serialized_graph[asset.name] = asset.to_dict()

        return serialized_graph

    @property
    def associations(self) -> set[LanguageGraphAssociation]:
        """
        Return all associations in the language graph.
        """
        return {assoc for asset in self.assets.values() for assoc in asset.associations.values()}

    @staticmethod
    def _link_association_to_assets(
        assoc: LanguageGraphAssociation,
        left_asset: LanguageGraphAsset,
        right_asset: LanguageGraphAsset
    ):
        left_asset.own_associations[assoc.right_field.fieldname] = assoc
        right_asset.own_associations[assoc.left_field.fieldname] = assoc

    def save_to_file(self, filename: str) -> None:
        """Save to json/yml depending on extension"""
        return save_dict_to_file(filename, self._to_dict())


    @classmethod
    def _from_dict(cls, serialized_graph: dict) -> LanguageGraph:
        """Create LanguageGraph from dict
        Args:
        serialized_graph   - LanguageGraph in dict format
        """

        logger.debug('Create language graph from dictionary.')
        lang_graph = LanguageGraph()
        lang_graph.metadata = serialized_graph.pop('metadata')

        # Recreate all of the assets
        for asset_dict in serialized_graph.values():
            logger.debug(
                'Create asset language graph nodes for asset %s',
                asset_dict['name']
            )
            asset_node = LanguageGraphAsset(
                name = asset_dict['name'],
                own_associations = {},
                attack_steps = {},
                info = asset_dict['info'],
                own_super_asset = None,
                own_sub_assets = set(),
                own_variables = {},
                is_abstract = asset_dict['is_abstract']
            )
            lang_graph.assets[asset_dict['name']] = asset_node

        # Relink assets based on inheritance
        for asset_dict in serialized_graph.values():
            asset = lang_graph.assets[asset_dict['name']]
            super_asset_name = asset_dict['super_asset']
            if not super_asset_name:
                continue

            super_asset = lang_graph.assets[super_asset_name]
            if not super_asset:
                msg = 'Failed to find super asset "%s" for asset "%s"!'
                logger.error(
                    msg, asset_dict["super_asset"], asset_dict["name"])
                raise LanguageGraphSuperAssetNotFoundError(
                    msg % (asset_dict["super_asset"], asset_dict["name"]))

            super_asset.own_sub_assets.add(asset)
            asset.own_super_asset = super_asset

        # Generate all of the association nodes of the language graph.
        for asset_dict in serialized_graph.values():
            logger.debug(
                'Create association language graph nodes for asset %s',
                asset_dict['name']
            )

            asset = lang_graph.assets[asset_dict['name']]
            for association in asset_dict['associations'].values():
                left_asset = lang_graph.assets[association['left']['asset']]
                if not left_asset:
                    msg = 'Left asset "%s" for association "%s" not found!'
                    logger.error(
                        msg, association['left']['asset'],
                            association['name'])
                    raise LanguageGraphAssociationError(
                        msg % (association['left']['asset'],
                            association['name']))

                right_asset = lang_graph.assets[association['right']['asset']]
                if not right_asset:
                    msg = 'Right asset "%s" for association "%s" not found!'
                    logger.error(
                        msg, association['right']['asset'],
                            association['name'])
                    raise LanguageGraphAssociationError(
                        msg % (association['right']['asset'],
                            association['name'])
                    )

                assoc_node = LanguageGraphAssociation(
                    name = association['name'],
                    left_field = LanguageGraphAssociationField(
                        left_asset,
                        association['left']['fieldname'],
                        association['left']['min'],
                        association['left']['max']),
                    right_field = LanguageGraphAssociationField(
                        right_asset,
                        association['right']['fieldname'],
                        association['right']['min'],
                        association['right']['max']),
                    info = association['info']
                )

                # Add the association to the left and right asset
                lang_graph._link_association_to_assets(assoc_node,
                    left_asset, right_asset)

        # Recreate the variables
        for asset_dict in serialized_graph.values():
            asset = lang_graph.assets[asset_dict['name']]
            for variable_name, var_target in asset_dict['variables'].items():
                (target_asset_name, expr_chain_dict) = var_target
                target_asset = lang_graph.assets[target_asset_name]
                expr_chain = ExpressionsChain._from_dict(
                    expr_chain_dict,
                    lang_graph
                )
                asset.own_variables[variable_name] = (target_asset, expr_chain)

        # Recreate the attack steps
        for asset_dict in serialized_graph.values():
            asset = lang_graph.assets[asset_dict['name']]
            logger.debug(
                'Create attack steps language graph nodes for asset %s',
                asset_dict['name']
            )
            for attack_step_dict in asset_dict['attack_steps'].values():
                attack_step_node = LanguageGraphAttackStep(
                    name = attack_step_dict['name'],
                    type = attack_step_dict['type'],
                    asset = asset,
                    ttc = attack_step_dict['ttc'],
                    overrides = attack_step_dict['overrides'],
                    own_children = {},
                    own_parents = {},
                    info = attack_step_dict['info'],
                    tags = list(attack_step_dict['tags'])
                )
                asset.attack_steps[attack_step_dict['name']] = \
                    attack_step_node

        # Relink attack steps based on inheritence
        for asset_dict in serialized_graph.values():
            asset = lang_graph.assets[asset_dict['name']]
            for attack_step_dict in asset_dict['attack_steps'].values():
                if 'inherits' in attack_step_dict and \
                        attack_step_dict['inherits'] is not None:
                    attack_step = asset.attack_steps[
                        attack_step_dict['name']]
                    ancestor_asset_name, ancestor_attack_step_name = \
                        disaggregate_attack_step_full_name(
                            attack_step_dict['inherits'])
                    ancestor_asset = lang_graph.assets[ancestor_asset_name]
                    ancestor_attack_step = ancestor_asset.attack_steps[\
                        ancestor_attack_step_name]
                    attack_step.inherits = ancestor_attack_step


        # Relink attack steps based on expressions chains
        for asset_dict in serialized_graph.values():
            asset = lang_graph.assets[asset_dict['name']]
            for attack_step_dict in asset_dict['attack_steps'].values():
                attack_step = asset.attack_steps[attack_step_dict['name']]
                for child_target in attack_step_dict['own_children'].items():
                    target_full_attack_step_name = child_target[0]
                    expr_chains = child_target[1]
                    target_asset_name, target_attack_step_name = \
                        disaggregate_attack_step_full_name(target_full_attack_step_name)
                    target_asset = lang_graph.assets[target_asset_name]
                    target_attack_step = target_asset.attack_steps[
                        target_attack_step_name]
                    for expr_chain_dict in expr_chains:
                        expr_chain = ExpressionsChain._from_dict(
                            expr_chain_dict,
                            lang_graph
                        )

                        if target_attack_step in attack_step.own_children:
                            attack_step.own_children[target_attack_step].append(expr_chain)
                        else:
                            attack_step.own_children[target_attack_step] = [expr_chain]

                for (target_step_full_name, expr_chains) in attack_step_dict['own_parents'].items():
                    target_asset_name, target_attack_step_name = \
                        disaggregate_attack_step_full_name(
                            target_step_full_name
                        )
                    target_asset = lang_graph.assets[target_asset_name]
                    target_attack_step = target_asset.attack_steps[target_attack_step_name]
                    for expr_chain_dict in expr_chains:
                        expr_chain = ExpressionsChain._from_dict(
                            expr_chain_dict, lang_graph
                        )

                        if target_attack_step in attack_step.own_parents:
                            attack_step.own_parents[target_attack_step].append(
                                expr_chain
                            )
                        else:
                            attack_step.own_parents[target_attack_step] = [expr_chain]

                # Recreate the requirements of exist and notExist attack steps
                if attack_step.type == 'exist' or \
                        attack_step.type == 'notExist':
                    if 'requires' in attack_step_dict:
                        expr_chains = attack_step_dict['requires']
                        attack_step.own_requires = []
                        for expr_chain_dict in expr_chains:
                            expr_chain = ExpressionsChain._from_dict(
                                expr_chain_dict,
                                lang_graph
                            )
                            if expr_chain:
                                attack_step.own_requires.append(expr_chain)

        return lang_graph


    @classmethod
    def load_from_file(cls, filename: str) -> LanguageGraph:
        """Create LanguageGraph from mal, mar, yaml or json"""
        lang_graph = None
        if filename.endswith('.mal'):
            lang_graph = cls.from_mal_spec(filename)
        elif filename.endswith('.mar'):
            lang_graph = cls.from_mar_archive(filename)
        elif filename.endswith(('.yaml', '.yml')):
            lang_graph = cls._from_dict(load_dict_from_yaml_file(filename))
        elif filename.endswith(('.json')):
            lang_graph = cls._from_dict(load_dict_from_json_file(filename))
        else:
            raise TypeError(
                "Unknown file extension, expected json/mal/mar/yml/yaml"
            )

        if lang_graph:
            return lang_graph
        else:
            raise LanguageGraphException(
                f'Failed to load language graph from file "{filename}".'
            )


    def save_language_specification_to_json(self, filename: str) -> None:
        """
        Save a MAL language specification dictionary to a JSON file

        Arguments:
        filename        - the JSON filename where the language specification will be written
        """
        logger.info('Save language specification to %s', filename)

        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(self._lang_spec, file, indent=4)

    def process_attack_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any]
    ) -> tuple[
                LanguageGraphAsset,
                None,
                str
            ]:
        """
        The attack step expression just adds the name of the attack
        step. All other step expressions only modify the target
        asset and parent associations chain.
        """
        return (
            target_asset,
            None,
            step_expression['name']
        )

    def process_set_operation_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: Optional[ExpressionsChain],
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """
        The set operators are used to combine the left hand and right
        hand targets accordingly.
        """

        lh_target_asset, lh_expr_chain, _ = self.process_step_expression(
            target_asset,
            expr_chain,
            step_expression['lhs']
        )
        rh_target_asset, rh_expr_chain, _ = self.process_step_expression(
            target_asset,
            expr_chain,
            step_expression['rhs']
        )

        assert lh_target_asset, (
            f"No lh target in step expression {step_expression}"
        )
        assert rh_target_asset, (
            f"No rh target in step expression {step_expression}"
        )

        if not lh_target_asset.get_all_common_superassets(rh_target_asset):
            raise ValueError(
                "Set operation attempted between targets that do not share "
                f"any common superassets: {lh_target_asset.name} "
                f"and {rh_target_asset.name}!"
            )

        new_expr_chain = ExpressionsChain(
            type = step_expression['type'],
            left_link = lh_expr_chain,
            right_link = rh_expr_chain
        )
        return (
            lh_target_asset,
            new_expr_chain,
            None
        )

    def process_variable_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:

        var_name = step_expression['name']
        var_target_asset, var_expr_chain = (
            self._resolve_variable(target_asset, var_name)
        )

        if var_expr_chain is None:
            raise LookupError(
                f'Failed to find variable "{step_expression["name"]}" '
                f'for {target_asset.name}',
            )

        return (
            var_target_asset,
            var_expr_chain,
            None
        )

    def process_field_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """
        Change the target asset from the current one to the associated
        asset given the specified field name and add the parent
        fieldname and association to the parent associations chain.
        """

        fieldname = step_expression['name']

        if target_asset is None:
            raise ValueError(
                f'Missing target asset for field "{fieldname}"!'
            )

        new_target_asset = None
        for association in target_asset.associations.values():
            if (association.left_field.fieldname == fieldname and \
                target_asset.is_subasset_of(
                    association.right_field.asset)):
                new_target_asset = association.left_field.asset

            if (association.right_field.fieldname == fieldname and \
                target_asset.is_subasset_of(
                    association.left_field.asset)):
                new_target_asset = association.right_field.asset

            if new_target_asset:
                new_expr_chain = ExpressionsChain(
                    type = 'field',
                    fieldname = fieldname,
                    association = association
                )
                return (
                    new_target_asset,
                    new_expr_chain,
                    None
                )

        raise LookupError(
            f'Failed to find field {fieldname} on asset {target_asset.name}!',
        )

    def process_transitive_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: Optional[ExpressionsChain],
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """
        Create a transitive tuple entry that applies to the next
        component of the step expression.
        """
        result_target_asset, result_expr_chain, _ = (
            self.process_step_expression(
                target_asset,
                expr_chain,
                step_expression['stepExpression']
            )
        )
        new_expr_chain = ExpressionsChain(
            type = 'transitive',
            sub_link = result_expr_chain
        )
        return (
            result_target_asset,
            new_expr_chain,
            None
        )

    def process_subType_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: Optional[ExpressionsChain],
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """
        Create a subType tuple entry that applies to the next
        component of the step expression and changes the target
        asset to the subasset.
        """

        subtype_name = step_expression['subType']
        result_target_asset, result_expr_chain, _ = (
            self.process_step_expression(
                target_asset,
                expr_chain,
                step_expression['stepExpression']
            )
        )

        if subtype_name not in self.assets:
            raise LanguageGraphException(
                f'Failed to find subtype {subtype_name}'
            )

        subtype_asset = self.assets[subtype_name]

        if result_target_asset is None:
            raise LookupError("Nonexisting asset for subtype")

        if not subtype_asset.is_subasset_of(result_target_asset):
            raise ValueError(
                f'Found subtype {subtype_name} which does not extend '
                f'{result_target_asset.name}, subtype cannot be resolved.'
            )

        new_expr_chain = ExpressionsChain(
            type = 'subType',
            sub_link = result_expr_chain,
            subtype = subtype_asset
        )
        return (
            subtype_asset,
            new_expr_chain,
            None
        )

    def process_collect_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: Optional[ExpressionsChain],
        step_expression: dict[str, Any]
    ) -> tuple[
            LanguageGraphAsset,
            Optional[ExpressionsChain],
            Optional[str]
        ]:
        """
        Apply the right hand step expression to left hand step
        expression target asset and parent associations chain.
        """
        lh_target_asset, lh_expr_chain, _ = self.process_step_expression(
            target_asset, expr_chain, step_expression['lhs']
        )

        if lh_target_asset is None:
            raise ValueError(
                'No left hand asset in collect expression '
                f'{step_expression["lhs"]}'
            )

        rh_target_asset, rh_expr_chain, rh_attack_step_name = (
            self.process_step_expression(
                lh_target_asset, None, step_expression['rhs']
            )
        )

        new_expr_chain = lh_expr_chain
        if rh_expr_chain:
            new_expr_chain = ExpressionsChain(
                type = 'collect',
                left_link = lh_expr_chain,
                right_link = rh_expr_chain
            )

        return (
            rh_target_asset,
            new_expr_chain,
            rh_attack_step_name
        )

    def process_step_expression(self,
            target_asset: LanguageGraphAsset,
            expr_chain: Optional[ExpressionsChain],
            step_expression: dict
        ) -> tuple[
                LanguageGraphAsset,
                Optional[ExpressionsChain],
                Optional[str]
            ]:
        """
        Recursively process an attack step expression.

        Arguments:
        target_asset        - The asset type that this step expression should
                              apply to. Initially it will contain the asset
                              type to which the attack step belongs.
        expr_chain          - A expressions chain of linked of associations
                              and set operations from the attack step to its
                              parent attack step.
                              Note: This was done for the parent attack step
                              because it was easier to construct recursively
                              given the left-hand first expansion of the
                              current MAL language specification.
        step_expression     - A dictionary containing the step expression.

        Return:
        A tuple triplet containing the target asset, the resulting parent
        associations chain, and the name of the attack step.
        """

        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(
                'Processing Step Expression:\n%s',
                json.dumps(step_expression, indent = 2)
            )

        result: tuple[
            LanguageGraphAsset,
            Optional[ExpressionsChain],
            Optional[str]
        ]

        match (step_expression['type']):
            case 'attackStep':
                result = self.process_attack_step_expression(
                    target_asset, step_expression
                )
            case 'union' | 'intersection' | 'difference':
                result = self.process_set_operation_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case 'variable':
                result = self.process_variable_step_expression(
                    target_asset, step_expression
                )
            case 'field':
                result = self.process_field_step_expression(
                    target_asset, step_expression
                )
            case 'transitive':
                result = self.process_transitive_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case 'subType':
                result = self.process_subType_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case 'collect':
                result = self.process_collect_step_expression(
                    target_asset, expr_chain, step_expression
                )
            case _:
                raise LookupError(
                    f'Unknown attack step type: "{step_expression["type"]}"'
                )
        return result

    def reverse_expr_chain(
            self,
            expr_chain: Optional[ExpressionsChain],
            reverse_chain: Optional[ExpressionsChain]
        ) -> Optional[ExpressionsChain]:
        """
        Recursively reverse the associations chain. From parent to child or
        vice versa.

        Arguments:
        expr_chain          - A chain of nested tuples that specify the
                              associations and set operations chain from an
                              attack step to its connected attack step.
        reverse_chain       - A chain of nested tuples that represents the
                              current reversed associations chain.

        Return:
        The resulting reversed associations chain.
        """
        if not expr_chain:
            return reverse_chain
        else:
            match (expr_chain.type):
                case 'union' | 'intersection' | 'difference' | 'collect':
                    left_reverse_chain = \
                        self.reverse_expr_chain(expr_chain.left_link,
                        reverse_chain)
                    right_reverse_chain = \
                        self.reverse_expr_chain(expr_chain.right_link,
                        reverse_chain)
                    if expr_chain.type == 'collect':
                        new_expr_chain = ExpressionsChain(
                            type = expr_chain.type,
                            left_link = right_reverse_chain,
                            right_link = left_reverse_chain
                        )
                    else:
                        new_expr_chain = ExpressionsChain(
                            type = expr_chain.type,
                            left_link = left_reverse_chain,
                            right_link = right_reverse_chain
                        )

                    return new_expr_chain

                case 'transitive':
                    result_reverse_chain = self.reverse_expr_chain(
                        expr_chain.sub_link, reverse_chain)
                    new_expr_chain = ExpressionsChain(
                        type = 'transitive',
                        sub_link = result_reverse_chain
                    )
                    return new_expr_chain

                case 'field':
                    association = expr_chain.association

                    if not association:
                        raise LanguageGraphException(
                            "Missing association for expressions chain"
                        )

                    if not expr_chain.fieldname:
                        raise LanguageGraphException(
                            "Missing field name for expressions chain"
                        )

                    opposite_fieldname = association.get_opposite_fieldname(
                        expr_chain.fieldname)
                    new_expr_chain = ExpressionsChain(
                        type = 'field',
                        association = association,
                        fieldname = opposite_fieldname
                    )
                    return new_expr_chain

                case 'subType':
                    result_reverse_chain = self.reverse_expr_chain(
                        expr_chain.sub_link,
                        reverse_chain
                    )
                    new_expr_chain = ExpressionsChain(
                        type = 'subType',
                        sub_link = result_reverse_chain,
                        subtype = expr_chain.subtype
                    )
                    return new_expr_chain

                case _:
                    msg = 'Unknown assoc chain element "%s"'
                    logger.error(msg, expr_chain.type)
                    raise LanguageGraphAssociationError(msg % expr_chain.type)

    def _resolve_variable(self, asset: LanguageGraphAsset, var_name) -> tuple:
        """
        Resolve a variable for a specific asset by variable name.

        Arguments:
        asset       - a language graph asset to which the variable belongs
        var_name    - a string representing the variable name

        Return:
        A tuple containing the target asset and expressions chain required to
        reach it.
        """
        if var_name not in asset.variables:
            var_expr = self._get_var_expr_for_asset(asset.name, var_name)
            target_asset, expr_chain, _ = self.process_step_expression(
                asset,
                None,
                var_expr
            )
            asset.own_variables[var_name] = (target_asset, expr_chain)
            return (target_asset, expr_chain)
        return asset.variables[var_name]

    def _create_associations_for_assets(
            self,
            lang_spec: dict[str, Any],
            assets: dict[str, LanguageGraphAsset]
        ) -> None:
        """ Link associations to assets based on the language specification.
        Arguments:
        lang_spec   - the language specification dictionary
        assets      - a dictionary of LanguageGraphAsset objects
                      indexed by their names
        """

        for association_dict in lang_spec['associations']:
            logger.debug(
                'Create association language graph nodes for association %s',
                association_dict['name']
            )

            left_asset_name = association_dict['leftAsset']
            right_asset_name = association_dict['rightAsset']

            if left_asset_name not in assets:
                raise LanguageGraphAssociationError(
                    f'Left asset "{left_asset_name}" for '
                    f'association "{association_dict["name"]}" not found!'
                )
            if right_asset_name not in assets:
                raise LanguageGraphAssociationError(
                    f'Right asset "{right_asset_name}" for '
                    f'association "{association_dict["name"]}" not found!'
                )

            left_asset = assets[left_asset_name]
            right_asset = assets[right_asset_name]

            assoc_node = LanguageGraphAssociation(
                name = association_dict['name'],
                left_field = LanguageGraphAssociationField(
                    left_asset,
                    association_dict['leftField'],
                    association_dict['leftMultiplicity']['min'],
                    association_dict['leftMultiplicity']['max']
                ),
                right_field = LanguageGraphAssociationField(
                    right_asset,
                    association_dict['rightField'],
                    association_dict['rightMultiplicity']['min'],
                    association_dict['rightMultiplicity']['max']
                ),
                info = association_dict['meta']
            )

            # Add the association to the left and right asset
            self._link_association_to_assets(
                assoc_node, left_asset, right_asset
            )

    def _link_assets(
            self,
            lang_spec: dict[str, Any],
            assets: dict[str, LanguageGraphAsset]
        ) -> None:
        """
        Link assets based on inheritance and associations.
        """

        for asset_dict in lang_spec['assets']:
            asset = assets[asset_dict['name']]
            if asset_dict['superAsset']:
                super_asset = assets[asset_dict['superAsset']]
                if not super_asset:
                    msg = 'Failed to find super asset "%s" for asset "%s"!'
                    logger.error(
                        msg, asset_dict["superAsset"], asset_dict["name"])
                    raise LanguageGraphSuperAssetNotFoundError(
                        msg % (asset_dict["superAsset"], asset_dict["name"]))

                super_asset.own_sub_assets.add(asset)
                asset.own_super_asset = super_asset

    def _set_variables_for_assets(
            self, assets: dict[str, LanguageGraphAsset]
        ) -> None:
        """ Set the variables for each asset based on the language specification.
        Arguments:
        assets      - a dictionary of LanguageGraphAsset objects
                      indexed by their names
        """

        for asset in assets.values():
            logger.debug(
                'Set variables for asset %s', asset.name
            )
            variables = self._get_variables_for_asset_type(asset.name)
            for variable in variables:
                if logger.isEnabledFor(logging.DEBUG):
                    # Avoid running json.dumps when not in debug
                    logger.debug(
                        'Processing Variable Expression:\n%s',
                        json.dumps(variable, indent = 2)
                    )
                self._resolve_variable(asset, variable['name'])

    def _generate_attack_steps(self, assets) -> None:
        """
        Generate all of the attack steps for each asset type
        based on the language specification.
        """
        langspec_dict = {}
        for asset in assets.values():
            logger.debug(
                'Create attack steps language graph nodes for asset %s',
                asset.name
            )
            attack_steps = self._get_attacks_for_asset_type(asset.name)
            for attack_step_attribs in attack_steps.values():
                logger.debug(
                    'Create attack step language graph nodes for %s',
                    attack_step_attribs['name']
                )

                attack_step_node = LanguageGraphAttackStep(
                    name = attack_step_attribs['name'],
                    type = attack_step_attribs['type'],
                    asset = asset,
                    ttc = attack_step_attribs['ttc'],
                    overrides = (
                        attack_step_attribs['reaches']['overrides']
                        if attack_step_attribs['reaches'] else False
                    ),
                    own_children = {},
                    own_parents = {},
                    info = attack_step_attribs['meta'],
                    tags = list(attack_step_attribs['tags'])
                )
                langspec_dict[attack_step_node.full_name] = \
                    attack_step_attribs
                asset.attack_steps[attack_step_node.name] = \
                    attack_step_node

                detectors: dict = attack_step_attribs.get("detectors", {})
                for detector in detectors.values():
                    attack_step_node.detectors[detector["name"]] = Detector(
                        context=Context(
                            {
                                label: assets[asset]
                                for label, asset in detector["context"].items()
                            }
                        ),
                        name=detector.get("name"),
                        type=detector.get("type"),
                        tprate=detector.get("tprate"),
                    )

        # Create the inherited attack steps
        assets = list(self.assets.values())
        while len(assets) > 0:
            asset = assets.pop(0)
            if asset.own_super_asset in assets:
                # The asset still has super assets that should be resolved
                # first, moved it to the back.
                assets.append(asset)
            else:
                if asset.own_super_asset:
                    for attack_step in \
                            asset.own_super_asset.attack_steps.values():
                        if attack_step.name not in asset.attack_steps:
                            attack_step_node = LanguageGraphAttackStep(
                                name = attack_step.name,
                                type = attack_step.type,
                                asset = asset,
                                ttc = attack_step.ttc,
                                overrides = False,
                                own_children = {},
                                own_parents = {},
                                info = attack_step.info,
                                tags = list(attack_step.tags)
                            )
                            attack_step_node.inherits = attack_step
                            asset.attack_steps[attack_step.name] = attack_step_node
                        elif asset.attack_steps[attack_step.name].overrides:
                            # The inherited attack step was already overridden.
                            continue
                        else:
                            asset.attack_steps[attack_step.name].inherits = attack_step
                            asset.attack_steps[attack_step.name].tags += attack_step.tags
                            asset.attack_steps[attack_step.name].info |= attack_step.info

        # Then, link all of the attack step nodes according to their
        # associations.
        for asset in self.assets.values():
            for attack_step in asset.attack_steps.values():
                logger.debug(
                    'Determining children for attack step %s',
                    attack_step.name
                )

                if attack_step.full_name not in langspec_dict:
                    # This is simply an empty inherited attack step
                    continue

                langspec_entry = langspec_dict[attack_step.full_name]
                step_expressions = (
                    langspec_entry['reaches']['stepExpressions']
                    if langspec_entry['reaches'] else []
                )

                for step_expression in step_expressions:
                    # Resolve each of the attack step expressions listed for
                    # this attack step to determine children.
                    (target_asset, expr_chain, target_attack_step_name) = \
                        self.process_step_expression(
                            attack_step.asset,
                            None,
                            step_expression
                        )
                    if not target_asset:
                        msg = 'Failed to find target asset to link with for ' \
                            'step expression:\n%s'
                        raise LanguageGraphStepExpressionError(
                            msg % json.dumps(step_expression, indent = 2)
                        )

                    target_asset_attack_steps = target_asset.attack_steps
                    if target_attack_step_name not in \
                            target_asset_attack_steps:
                        msg = 'Failed to find target attack step %s on %s to ' \
                              'link with for step expression:\n%s'
                        raise LanguageGraphStepExpressionError(
                            msg % (
                                target_attack_step_name,
                                target_asset.name,
                                json.dumps(step_expression, indent = 2)
                            )
                        )

                    target_attack_step = target_asset_attack_steps[
                        target_attack_step_name]

                    # Link to the children target attack steps
                    attack_step.own_children.setdefault(target_attack_step, [])
                    attack_step.own_children[target_attack_step].append(expr_chain)

                    # Reverse the children associations chains to get the
                    # parents associations chain.
                    target_attack_step.own_parents.setdefault(attack_step, [])
                    target_attack_step.own_parents[attack_step].append(
                        self.reverse_expr_chain(expr_chain, None)
                    )

                # Evaluate the requirements of exist and notExist attack steps
                if attack_step.type in ('exist', 'notExist'):
                    step_expressions = (
                        langspec_entry['requires']['stepExpressions']
                        if langspec_entry['requires'] else []
                    )
                    if not step_expressions:
                        raise LanguageGraphStepExpressionError(
                            'Failed to find requirements for attack step'
                            ' "%s" of type "%s":\n%s' % (
                                attack_step.name,
                                attack_step.type,
                                json.dumps(langspec_entry, indent = 2)
                            )
                        )

                    for step_expression in step_expressions:
                        _, result_expr_chain, _ = \
                            self.process_step_expression(
                                attack_step.asset,
                                None,
                                step_expression
                            )
                        if result_expr_chain is None:
                            raise LanguageGraphException('Failed to find '
                            'existence step requirement for step '
                            f'expression:\n%s' % step_expression)
                        attack_step.own_requires.append(result_expr_chain)

    def _generate_graph(self) -> None:
        """
        Generate language graph starting from the MAL language specification
        given in the constructor.
        """
        # Generate all of the asset nodes of the language graph.
        self.assets = {}
        for asset_dict in self._lang_spec['assets']:
            logger.debug(
                'Create asset language graph nodes for asset %s',
                asset_dict['name']
            )
            asset_node = LanguageGraphAsset(
                name = asset_dict['name'],
                own_associations = {},
                attack_steps = {},
                info = asset_dict['meta'],
                own_super_asset = None,
                own_sub_assets = set(),
                own_variables = {},
                is_abstract = asset_dict['isAbstract']
            )
            self.assets[asset_dict['name']] = asset_node

        # Link assets to each other
        self._link_assets(self._lang_spec, self.assets)

        # Add and link associations to assets
        self._create_associations_for_assets(self._lang_spec, self.assets)

        # Set the variables for each asset
        self._set_variables_for_assets(self.assets)

        # Add attack steps to the assets
        self._generate_attack_steps(self.assets)

    def _get_attacks_for_asset_type(self, asset_type: str) -> dict[str, dict]:
        """
        Get all Attack Steps for a specific asset type.

        Arguments:
        asset_type      - the name of the asset type we want to
                          list the possible attack steps for

        Return:
        A dictionary containing the possible attacks for the
        specified asset type. Each key in the dictionary is an attack name
        associated with a dictionary containing other characteristics of the
        attack such as type of attack, TTC distribution, child attack steps
        and other information
        """
        attack_steps: dict = {}
        try:
            asset = next(
                asset for asset in self._lang_spec['assets'] \
                    if asset['name'] == asset_type
            )
        except StopIteration:
            logger.error(
                'Failed to find asset type %s when looking'
                'for attack steps.', asset_type
            )
            return attack_steps

        logger.debug(
            'Get attack steps for %s asset from '
            'language specification.', asset['name']
        )

        attack_steps = {step['name']: step for step in asset['attackSteps']}

        return attack_steps

    def _get_associations_for_asset_type(self, asset_type: str) -> list[dict]:
        """
        Get all associations for a specific asset type.

        Arguments:
        asset_type      - the name of the asset type for which we want to
                          list the associations

        Return:
        A list of dicts, where each dict represents an associations
        for the specified asset type. Each dictionary contains
        name and meta information about the association.
        """
        logger.debug(
            'Get associations for %s asset from '
            'language specification.', asset_type
        )
        associations: list = []

        asset = next((asset for asset in self._lang_spec['assets'] \
            if asset['name'] == asset_type), None)
        if not asset:
            logger.error(
                'Failed to find asset type %s when '
                'looking for associations.', asset_type
            )
            return associations

        assoc_iter = (assoc for assoc in self._lang_spec['associations'] \
            if assoc['leftAsset'] == asset_type or \
                assoc['rightAsset'] == asset_type)
        assoc = next(assoc_iter, None)
        while assoc:
            associations.append(assoc)
            assoc = next(assoc_iter, None)

        return associations

    def _get_variables_for_asset_type(
            self, asset_type: str) -> list[dict]:
        """
        Get variables for a specific asset type.
        Note: Variables are the ones specified in MAL through `let` statements

        Arguments:
        asset_type      - a string representing the asset type which
                          contains the variables

        Return:
        A list of dicts representing the step expressions for the variables
        belonging to the asset.
        """

        asset_dict = next((asset for asset in self._lang_spec['assets'] \
            if asset['name'] == asset_type), None)
        if not asset_dict:
            msg = 'Failed to find asset type %s in language specification '\
                'when looking for variables.'
            logger.error(msg, asset_type)
            raise LanguageGraphException(msg % asset_type)

        return asset_dict['variables']

    def _get_var_expr_for_asset(
            self, asset_type: str, var_name) -> dict:
        """
        Get a variable for a specific asset type by variable name.

        Arguments:
        asset_type      - a string representing the type of asset which
                          contains the variable
        var_name        - a string representing the variable name

        Return:
        A dictionary representing the step expression for the variable.
        """

        vars_dict = self._get_variables_for_asset_type(asset_type)

        var_expr = next((var_entry['stepExpression'] for var_entry \
            in vars_dict if var_entry['name'] == var_name), None)

        if not var_expr:
            msg = 'Failed to find variable name "%s" in language '\
                'specification when looking for variables for "%s" asset.'
            logger.error(msg, var_name, asset_type)
            raise LanguageGraphException(msg % (var_name, asset_type))
        return var_expr

    def regenerate_graph(self) -> None:
        """
        Regenerate language graph starting from the MAL language specification
        given in the constructor.
        """

        self.assets = {}
        self._generate_graph()
