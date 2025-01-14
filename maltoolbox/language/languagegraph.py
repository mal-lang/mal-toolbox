"""
MAL-Toolbox Language Graph Module
"""

from __future__ import annotations

import copy
import logging
import json
import zipfile

from dataclasses import dataclass, field
from typing import Any, Optional

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

def get_asset_name_from_full_attack_step(
        attack_step_full_name: str) -> str:
    return attack_step_full_name.split(':')[0]

def get_attack_step_name_from_full_attack_step(
        attack_step_full_name: str) -> str:
    return attack_step_full_name.split(':')[1]

@dataclass
class LanguageGraphAsset:
    name: str
    associations: dict[str, LanguageGraphAssociation] = \
        field(default_factory = dict)
    attack_steps: dict[str, LanguageGraphAttackStep] = \
        field(default_factory = dict)
    info: dict = field(default_factory = dict)
    # MAL languages currently do not support multiple inheritance, but this is
    # futureproofing at its most hopeful.
    super_assets: list[LanguageGraphAsset] = field(default_factory = list)
    sub_assets: list[LanguageGraphAsset] = field(default_factory = list)
    variables: dict = field(default_factory = dict)
    is_abstract: Optional[bool] = None

    def to_dict(self) -> dict:
        """Convert LanguageGraphAsset to dictionary"""
        node_dict: dict[str, Any] = {
            'name': self.name,
            'associations': {},
            'attack_steps': {},
            'info': self.info,
            'super_assets': [],
            'sub_assets': [],
            'variables': {},
            'is_abstract': self.is_abstract
        }

        for assoc_name, assoc in self.associations.items():
            node_dict['associations'][assoc_name] = assoc.to_dict()
        for attack_step_name, attack_step in self.attack_steps.items():
            node_dict['attack_steps'][attack_step_name] = \
                attack_step.to_dict()
        for super_asset in self.super_assets:
            node_dict['super_assets'].append(super_asset.name)
        for sub_asset in self.sub_assets:
            node_dict['sub_assets'].append(sub_asset.name)
        for variable_name, (var_target_asset, var_expr_chain) in \
                self.variables.items():
            node_dict['variables'][variable_name] = (
                var_target_asset.name,
                var_expr_chain.to_dict()
            )
        return node_dict


    def __repr__(self) -> str:
        return str(self.to_dict())


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
        current_assets = [self]
        while (current_assets):
            current_asset = current_assets.pop()
            if current_asset == target_asset:
                return True
            current_assets.extend(current_asset.super_assets)
        return False


    def get_all_subassets(self) -> list[LanguageGraphAsset]:
        """
        Return a list of all of the assets that directly or indirectly extend
        this asset.

        Return:
        A list of all of the assets that extend this asset plus itself.
        """
        current_assets = [self]
        subassets = [self]
        while (current_assets):
            current_asset = current_assets.pop()
            current_assets.extend(current_asset.sub_assets)
            subassets.extend(current_asset.sub_assets)
        return subassets


    def get_all_superassets(self) -> list[LanguageGraphAsset]:
        """
        Return a list of all of the assets that this asset directly or
        indirectly extends.

        Return:
        A list of all of the assets that this asset extends plus itself.
        """
        current_assets = [self]
        superassets = [self]
        while (current_assets):
            current_asset = current_assets.pop()
            current_assets.extend(current_asset.super_assets)
            superassets.extend(current_asset.super_assets)
        return superassets


    def get_all_associations(self) -> dict[str, LanguageGraphAssociation]:
        """
        Return a list of all of the associations that belong to this asset
        directly or indirectly via inheritance.

        Return:
        A list of all of the associations that apply to this asset, either
        directly or via inheritance.
        """

        associations = dict(self.associations)
        for super_asset in self.super_assets:
            associations |= super_asset.get_all_associations()
        return associations

    def get_all_variables(self) -> dict[str, ExpressionsChain]:
        """
        Return a list of all of the variables that belong to this asset
        directly or indirectly via inheritance.

        Return:
        A list of all of the variables that apply to this asset, either
        directly or via inheritance.
        """

        all_vars = dict(self.variables)
        for super_asset in self.super_assets:
            all_vars |= super_asset.get_all_variables()
        return all_vars


    def get_variable(
        self,
        var_name: str,
        ) -> Optional[tuple]:
        """
        Return a variable matching the given name if the asset or any of its
        super assets has its definition.

        Return:
        A tuple containing the target asset and expressions chain to it if the
        variable was defined.
        None otherwise.
        """
        current_assets = [self]
        while (current_assets):
            current_asset = current_assets.pop()
            if var_name in current_asset.variables:
                return current_asset.variables[var_name]
            current_assets.extend(current_asset.super_assets)
        return None


    def get_all_common_superassets(
            self, other: LanguageGraphAsset
        ) -> set[str]:
        """Return a set of all common ancestors between this asset
        and the other asset given as parameter"""
        self_superassets = set(
            asset.name for asset in self.get_all_superassets()
        )
        other_superassets = set(
            asset.name for asset in other.get_all_superassets()
        )
        return self_superassets.intersection(other_superassets)


@dataclass
class LanguageGraphAssociationField:
    asset: LanguageGraphAsset
    fieldname: str
    minimum: int
    maximum: int


@dataclass
class LanguageGraphAssociation:
    name: str
    left_field: LanguageGraphAssociationField
    right_field: LanguageGraphAssociationField
    info: dict = field(default_factory = dict)

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
        return str(self.to_dict())

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


    def get_opposite_asset(
            self, asset: LanguageGraphAsset
        ) -> Optional[LanguageGraphAsset]:
        """
        Return the opposite asset if the association matches the asset given
        as a parameter. A match can either be an explicit one or if the asset
        given subassets either of the two assets that are part of the
        association.

        Arguments:
        asset       - the asset to look for
        Return the other asset if the parameter matched either of the
        two. None, otherwise.
        """
        #TODO Should check to see which one is the tightest fit for
        #     associations between assets on different levels of the same
        #     inheritance chain.
        if asset.is_subasset_of(self.left_field.asset):
            return self.right_field.asset
        if asset.is_subasset_of(self.right_field.asset):
            return self.left_field.asset

        logger.warning(
            'Requested asset "%s" from association %s'
            'which did not contain it!', asset.name, self.name
        )
        return None


@dataclass
class LanguageGraphAttackStep:
    name: str
    type: str
    asset: LanguageGraphAsset
    ttc: dict = field(default_factory = dict)
    overrides: bool = False
    children: dict = field(default_factory = dict)
    parents: dict = field(default_factory = dict)
    info: dict = field(default_factory = dict)
    inherits: Optional[LanguageGraphAttackStep] = None
    tags: set = field(default_factory = set)
    _attributes: Optional[dict] = None

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
            'children': {},
            'parents': {},
            'info': self.info,
            'overrides': self.overrides,
            'inherits': self.inherits.full_name if self.inherits else None,
            'tags': list(self.tags)
        }

        for child in self.children:
            node_dict['children'][child] = []
            for (_, expr_chain) in self.children[child]:
                if expr_chain:
                    node_dict['children'][child].append(
                        expr_chain.to_dict())
                else:
                    node_dict['children'][child].append(None)

        for parent in self.parents:
            node_dict['parents'][parent] = []
            for (_, expr_chain) in self.parents[parent]:
                if expr_chain:
                    node_dict['parents'][parent].append(
                        expr_chain.to_dict())
                else:
                    node_dict['parents'][parent].append(None)

        if hasattr(self, 'requires'):
            node_dict['requires'] = []
            for requirement in self.requires:
                node_dict['requires'].append(requirement.to_dict())

        return node_dict


    def get_all_requirements(self):
        if not hasattr(self, 'requires'):
            requires = []
        else:
            requires = self.requires

        if self.inherits:
            requires.extend(self.inherits.get_all_requirements())
        return requires


    def __repr__(self) -> str:
        return str(self.to_dict())


class ExpressionsChain:
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
                    self.association.full_name:
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
        """Create LanguageGraph from dict
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
            return None

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
                new_expr_chain = ExpressionsChain(
                    type = 'field',
                    association = target_asset.associations[assoc_name],
                    fieldname = serialized_expr_chain[assoc_name]['fieldname']
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
                    logger.error(msg % subtype_name)
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
                raise LanguageGraphAssociationError(msg %
                    serialized_expr_chain['type'])


    def __repr__(self) -> str:
        return str(self.to_dict())


class LanguageGraph():
    """Graph representation of a MAL language"""
    def __init__(self, lang: Optional[dict] = None):
        self.assets: dict = {}
        if lang is not None:
            self._lang_spec: dict = lang
            self.metadata = {
                "version": lang["defines"]["version"],
                "id": lang["defines"]["id"],
            }
            self._generate_graph()


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

        serialized_graph = {}
        for asset_name, asset in self.assets.items():
            serialized_graph[asset_name] = asset.to_dict()

        return serialized_graph


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
        # Recreate all of the assets
        for asset_name, asset_dict in serialized_graph.items():
            logger.debug(
                'Create asset language graph nodes for asset %s',
                asset_dict['name']
            )
            asset_node = LanguageGraphAsset(
                name = asset_dict['name'],
                associations = {},
                attack_steps = {},
                info = asset_dict['info'],
                super_assets = [],
                sub_assets = [],
                variables = {},
                is_abstract = asset_dict['is_abstract']
            )
            lang_graph.assets[asset_dict['name']] = asset_node

        # Relink assets based on inheritance
        for asset_name, asset_dict in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for super_asset_name in asset_dict['super_assets']:
                super_asset = lang_graph.assets[super_asset_name]
                if not super_asset:
                    msg = 'Failed to find super asset "%s" for asset "%s"!'
                    logger.error(
                        msg, asset_dict["super_assets"], asset_dict["name"])
                    raise LanguageGraphSuperAssetNotFoundError(
                        msg % (asset_dict["super_assets"], asset_dict["name"]))

                super_asset.sub_assets.append(asset)
                asset.super_assets.append(super_asset)

        # Generate all of the association nodes of the language graph.
        for asset_name, asset_dict in serialized_graph.items():
            logger.debug(
                'Create association language graph nodes for asset %s',
                asset.name
            )

            asset = lang_graph.assets[asset_name]
            for association_name, association in \
                    asset_dict['associations'].items():
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
                associated_assets = [left_asset, right_asset]
                while associated_assets != []:
                    asset = associated_assets.pop()
                    if assoc_node.full_name not in asset.associations:
                        asset.associations[assoc_node.full_name] = assoc_node

        # Recreate the variables
        for asset_name, asset_dict in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for variable_name, var_target in asset_dict['variables'].items():
                (target_asset_name, expr_chain_dict) = var_target
                target_asset = lang_graph.assets[target_asset_name]
                expr_chain = ExpressionsChain._from_dict(
                    expr_chain_dict,
                    lang_graph
                )
                asset.variables[variable_name] = (target_asset, expr_chain)

        # Recreate the attack steps
        for asset_name, asset_dict in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            logger.debug(
                'Create attack steps language graph nodes for asset %s',
                asset.name
            )
            for attack_step_name, attack_step_dict in \
                    asset_dict['attack_steps'].items():
                attack_step_node = LanguageGraphAttackStep(
                    name = attack_step_name,
                    type = attack_step_dict['type'],
                    asset = asset,
                    ttc = attack_step_dict['ttc'],
                    overrides = attack_step_dict['overrides'],
                    children = {},
                    parents = {},
                    info = attack_step_dict['info'],
                    tags = set(attack_step_dict['tags'])
                )
                asset.attack_steps[attack_step_name] = attack_step_node

        # Relink attack steps based on inheritence
        for asset_name, asset_dict in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for attack_step_name, attack_step_dict in \
                    asset_dict['attack_steps'].items():
                if 'inherits' in attack_step_dict and \
                        attack_step_dict['inherits'] is not None:
                    attack_step = asset.attack_steps[attack_step_name]
                    ancestor_asset_name = get_asset_name_from_full_attack_step(
                        attack_step_dict['inherits'])
                    ancestor_attack_step_name = \
                        get_attack_step_name_from_full_attack_step(
                            attack_step_dict['inherits'])
                    ancestor_asset = lang_graph.assets[ancestor_asset_name]
                    ancestor_attack_step = ancestor_asset.attack_steps[\
                        ancestor_attack_step_name]
                    attack_step.inherits = ancestor_attack_step


        # Relink attack steps based on expressions chains
        for asset_name, asset_dict in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for attack_step_name, attack_step_dict in \
                    asset_dict['attack_steps'].items():
                attack_step = asset.attack_steps[attack_step_name]
                for child_target in attack_step_dict['children'].items():
                    target_full_attack_step_name = child_target[0]
                    expr_chains = child_target[1]
                    target_asset_name = get_asset_name_from_full_attack_step(
                        target_full_attack_step_name)
                    target_attack_step_name = \
                        get_attack_step_name_from_full_attack_step(
                            target_full_attack_step_name)
                    target_asset = lang_graph.assets[target_asset_name]
                    target_attack_step = target_asset.attack_steps[
                        target_attack_step_name]
                    for expr_chain_dict in expr_chains:
                        expr_chain = ExpressionsChain._from_dict(
                            expr_chain_dict,
                            lang_graph
                        )
                        if target_attack_step.full_name in attack_step.children:
                            attack_step.children[target_attack_step.full_name].\
                                append((target_attack_step, expr_chain))
                        else:
                            attack_step.children[target_attack_step.full_name] = \
                                [(target_attack_step, expr_chain)]

                for parent_target in attack_step_dict['parents'].items():
                    target_full_attack_step_name = parent_target[0]
                    expr_chains = parent_target[1]
                    target_asset_name = get_asset_name_from_full_attack_step(
                        target_full_attack_step_name)
                    target_attack_step_name = \
                        get_attack_step_name_from_full_attack_step(
                            target_full_attack_step_name)
                    target_asset = lang_graph.assets[target_asset_name]
                    target_attack_step = target_asset.attack_steps[
                        target_attack_step_name]
                    for expr_chain_dict in expr_chains:
                        expr_chain = ExpressionsChain._from_dict(
                            expr_chain_dict,
                            lang_graph
                        )
                        if target_attack_step.full_name in attack_step.parents:
                            attack_step.parents[target_attack_step.full_name].\
                                append((target_attack_step, expr_chain))
                        else:
                            attack_step.parents[target_attack_step.full_name] = \
                                [(target_attack_step, expr_chain)]

                # Recreate the requirements of exist and notExist attack steps
                if attack_step.type == 'exist' or \
                        attack_step.type == 'notExist':
                    if 'requires' in attack_step_dict:
                        expr_chains = attack_step_dict['requires']
                        attack_step.requires = []
                        for expr_chain_dict in expr_chains:
                            expr_chain = ExpressionsChain._from_dict(
                                expr_chain_dict,
                                lang_graph
                            )
                            attack_step.requires.append(expr_chain)

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


    def process_step_expression(self,
            target_asset,
            expr_chain,
            step_expression: dict
        ) -> tuple:
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
        lang = self._lang_spec

        match (step_expression['type']):
            case 'attackStep':
                # The attack step expression just adds the name of the attack
                # step. All other step expressions only modify the target
                # asset and parent associations chain.
                return (
                    target_asset,
                    None,
                    step_expression['name']
                )

            case 'union' | 'intersection' | 'difference':
                # The set operators are used to combine the left hand and right
                # hand targets accordingly.
                lh_target_asset, lh_expr_chain, _ = self.process_step_expression(
                    target_asset,
                    expr_chain,
                    step_expression['lhs']
                )
                rh_target_asset, rh_expr_chain, _ = \
                    self.process_step_expression(
                        target_asset,
                        expr_chain,
                        step_expression['rhs']
                    )

                if not lh_target_asset.get_all_common_superassets(
                        rh_target_asset):
                    logger.error(
                        "Set operation attempted between targets that"
                        " do not share any common superassets: %s and %s!",
                        lh_target_asset.name, rh_target_asset.name
                    )
                    return (None, None, None)

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

            case 'variable':
                var_name = step_expression['name']
                var_target_asset, var_expr_chain = self._resolve_variable(
                    target_asset, var_name)
                var_target_asset, var_expr_chain = \
                    target_asset.get_variable(var_name)
                if var_expr_chain is not None:
                    return (
                        var_target_asset,
                        var_expr_chain,
                        None
                    )
                else:
                    logger.error(
                        'Failed to find variable \"%s\" for %s',
                        step_expression["name"], target_asset.name
                    )
                    return (None, None, None)

            case 'field':
                # Change the target asset from the current one to the associated
                # asset given the specified field name and add the parent
                # fieldname and association to the parent associations chain.
                fieldname = step_expression['name']
                if not target_asset:
                    logger.error(
                        'Missing target asset for field "%s"!', fieldname
                    )
                    return (None, None, None)

                new_target_asset = None
                for association_name, association in \
                        target_asset.get_all_associations().items():
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
                logger.error(
                    'Failed to find field "%s" on asset "%s"!',
                    fieldname, target_asset.name
                )
                return (None, None, None)

            case 'transitive':
                # Create a transitive tuple entry that applies to the next
                # component of the step expression.
                result_target_asset, \
                result_expr_chain, \
                attack_step = \
                    self.process_step_expression(
                        target_asset,
                        expr_chain,
                        step_expression['stepExpression']
                    )
                new_expr_chain = ExpressionsChain(
                    type = 'transitive',
                    sub_link = result_expr_chain
                )
                return (
                    result_target_asset,
                    new_expr_chain,
                    attack_step
                )

            case 'subType':
                # Create a subType tuple entry that applies to the next
                # component of the step expression and changes the target
                # asset to the subasset.
                subtype_name = step_expression['subType']
                result_target_asset, \
                result_expr_chain, \
                attack_step = \
                    self.process_step_expression(
                        target_asset,
                        expr_chain,
                        step_expression['stepExpression']
                    )

                if subtype_name in self.assets:
                    subtype_asset = self.assets[subtype_name]
                else:
                    msg = 'Failed to find subtype %s'
                    logger.error(msg % subtype_name)
                    raise LanguageGraphException(msg % subtype_name)

                if not subtype_asset.is_subasset_of(result_target_asset):
                    logger.error(
                        'Found subtype "%s" which does not extend "%s", '
                        'therefore the subtype cannot be resolved.',
                        subtype_name, result_target_asset.name
                    )
                    return (None, None, None)

                new_expr_chain = ExpressionsChain(
                    type = 'subType',
                    sub_link = result_expr_chain,
                    subtype = subtype_asset
                )
                return (
                    subtype_asset,
                    new_expr_chain,
                    attack_step
                )

            case 'collect':
                # Apply the right hand step expression to left hand step
                # expression target asset and parent associations chain.
                (lh_target_asset, lh_expr_chain, _) = \
                    self.process_step_expression(
                        target_asset,
                        expr_chain,
                        step_expression['lhs']
                    )
                (rh_target_asset,
                    rh_expr_chain,
                    rh_attack_step_name) = \
                    self.process_step_expression(
                        lh_target_asset,
                        None,
                        step_expression['rhs']
                    )
                if rh_expr_chain:
                    new_expr_chain = ExpressionsChain(
                        type = 'collect',
                        left_link = lh_expr_chain,
                        right_link = rh_expr_chain
                    )
                else:
                    new_expr_chain = lh_expr_chain

                return (
                    rh_target_asset,
                    new_expr_chain,
                    rh_attack_step_name
                )

            case _:
                logger.error(
                    'Unknown attack step type: "%s"', step_expression["type"]
                )
                return (None, None, None)


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

    def _resolve_variable(self, asset, var_name) -> tuple:
        """
        Resolve a variable for a specific asset by variable name.

        Arguments:
        asset       - a language graph asset to which the variable belongs
        var_name    - a string representing the variable name

        Return:
        A tuple containing the target asset and expressions chain required to
        reach it.
        """
        all_vars = asset.get_all_variables()
        if var_name not in all_vars:
            var_expr = self._get_var_expr_for_asset(asset.name, var_name)
            target_asset, expr_chain, _ = self.process_step_expression(
                asset,
                None,
                var_expr
            )
            asset.variables[var_name] = (target_asset, expr_chain)
            return (target_asset, expr_chain)
        return all_vars[var_name]


    def _generate_graph(self) -> None:
        """
        Generate language graph starting from the MAL language specification
        given in the constructor.
        """
        # Generate all of the asset nodes of the language graph.
        for asset_dict in self._lang_spec['assets']:
            logger.debug(
                'Create asset language graph nodes for asset %s',
                asset_dict['name']
            )
            asset_node = LanguageGraphAsset(
                name = asset_dict['name'],
                associations = {},
                attack_steps = {},
                info = asset_dict['meta'],
                super_assets = [],
                sub_assets = [],
                variables = {},
                is_abstract = asset_dict['isAbstract']
            )
            self.assets[asset_dict['name']] = asset_node

        # Link assets based on inheritance
        for asset_dict in self._lang_spec['assets']:
            asset = self.assets[asset_dict['name']]
            if asset_dict['superAsset']:
                super_asset = self.assets[asset_dict['superAsset']]
                if not super_asset:
                    msg = 'Failed to find super asset "%s" for asset "%s"!'
                    logger.error(
                        msg, asset_dict["superAsset"], asset_dict["name"])
                    raise LanguageGraphSuperAssetNotFoundError(
                        msg % (asset_dict["superAsset"], asset_dict["name"]))

                super_asset.sub_assets.append(asset)
                asset.super_assets.append(super_asset)

        # Generate all of the association nodes of the language graph.
        for asset_name, asset in self.assets.items():
            logger.debug(
                'Create association language graph nodes for asset %s',
                asset.name
            )

            associations = self._get_associations_for_asset_type(asset.name)
            for association in associations:
                left_asset = self.assets[association['leftAsset']]
                if not left_asset:
                    msg = 'Left asset "%s" for association "%s" not found!'
                    logger.error(
                        msg, association["leftAsset"], association["name"])
                    raise LanguageGraphAssociationError(
                        msg % (association["leftAsset"], association["name"]))

                right_asset = self.assets[association['rightAsset']]
                if not right_asset:
                    msg = 'Right asset "%s" for association "%s" not found!'
                    logger.error(
                        msg, association["rightAsset"], association["name"])
                    raise LanguageGraphAssociationError(
                        msg % (association["rightAsset"], association["name"])
                    )

                assoc_node = LanguageGraphAssociation(
                    name = association['name'],
                    left_field = LanguageGraphAssociationField(
                        left_asset,
                        association['leftField'],
                        association['leftMultiplicity']['min'],
                        association['leftMultiplicity']['max']),
                    right_field = LanguageGraphAssociationField(
                        right_asset,
                        association['rightField'],
                        association['rightMultiplicity']['min'],
                        association['rightMultiplicity']['max']),
                    info = association['meta']
                )

                # Add the association to the left and right asset
                associated_assets = [left_asset, right_asset]
                while associated_assets != []:
                    asset = associated_assets.pop()
                    if assoc_node.full_name not in asset.associations:
                        asset.associations[assoc_node.full_name] = assoc_node

        # Set the variables
        for asset_name, asset in self.assets.items():
            for variable in self._get_variables_for_asset_type(asset_name):
                if logger.isEnabledFor(logging.DEBUG):
                    # Avoid running json.dumps when not in debug
                    logger.debug(
                        'Processing Variable Expression:\n%s',
                        json.dumps(variable, indent = 2)
                    )
                self._resolve_variable(asset, variable['name'])


        # Generate all of the attack step nodes of the language graph.
        for asset_name, asset in self.assets.items():
            logger.debug(
                'Create attack steps language graph nodes for asset %s',
                asset.name
            )
            attack_steps = self._get_attacks_for_asset_type(asset_name)
            for attack_step_name, attack_step_attribs in attack_steps.items():
                logger.debug(
                    'Create attack step language graph nodes for %s',
                    attack_step_name
                )

                attack_step_node = LanguageGraphAttackStep(
                    name = attack_step_name,
                    type = attack_step_attribs['type'],
                    asset = asset,
                    ttc = attack_step_attribs['ttc'],
                    overrides = attack_step_attribs['reaches']['overrides'] \
                        if attack_step_attribs['reaches'] else False,
                    children = {},
                    parents = {},
                    info = attack_step_attribs['meta'],
                    tags = set(attack_step_attribs['tags'])
                )
                attack_step_node._attributes = attack_step_attribs
                asset.attack_steps[attack_step_name] = attack_step_node

        # Create the inherited attack steps
        assets = list(self.assets.values())
        while len(assets) > 0:
            asset = assets.pop(0)
            if any(super_asset in assets for super_asset in \
                asset.super_assets):
                # The asset still has super assets that should be resolved
                # first, moved it to the back.
                assets.append(asset)
            else:
                for super_asset in asset.super_assets:
                    for attack_step_name, attack_step in super_asset.attack_steps.items():
                        if attack_step_name not in asset.attack_steps:
                            attack_step_node = LanguageGraphAttackStep(
                                name = attack_step_name,
                                type = attack_step.type,
                                asset = asset,
                                ttc = attack_step.ttc,
                                overrides = False,
                                children = {},
                                parents = {},
                                info = attack_step.info,
                                tags = set(attack_step.tags)
                            )
                            attack_step_node.inherits = attack_step
                            asset.attack_steps[attack_step_name] = attack_step_node
                        elif asset.attack_steps[attack_step_name].overrides:
                            # The inherited attack step was already overridden.
                            continue
                        else:
                            asset.attack_steps[attack_step_name].inherits = \
                                attack_step
                            asset.attack_steps[attack_step_name].tags |= \
                                attack_step.tags
                            asset.attack_steps[attack_step_name].info |= \
                                attack_step.info

        # Then, link all of the attack step nodes according to their
        # associations.
        for asset_name, asset in self.assets.items():
            for attack_step_name, attack_step in asset.attack_steps.items():
                logger.debug(
                    'Determining children for attack step %s',
                    attack_step_name
                )

                if attack_step._attributes is None:
                    # This is simply an empty inherited attack step
                    continue

                step_expressions = \
                    attack_step._attributes['reaches']['stepExpressions'] if \
                        attack_step._attributes['reaches'] else []

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
                    if target_attack_step.full_name in attack_step.children:
                        attack_step.children[target_attack_step.full_name].\
                            append((target_attack_step, expr_chain))
                    else:
                        attack_step.children[target_attack_step.full_name] = \
                            [(target_attack_step, expr_chain)]
                    # Reverse the children associations chains to get the
                    # parents associations chain.
                    if attack_step.full_name in target_attack_step.parents:
                        target_attack_step.parents[attack_step.full_name].\
                            append((attack_step,
                            self.reverse_expr_chain(expr_chain,
                                None)))
                    else:
                        target_attack_step.parents[attack_step.full_name] = \
                            [(attack_step,
                            self.reverse_expr_chain(expr_chain,
                                None))]

                # Evaluate the requirements of exist and notExist attack steps
                if attack_step.type == 'exist' or \
                        attack_step.type == 'notExist':
                    step_expressions = \
                        attack_step._attributes['requires']['stepExpressions'] \
                            if attack_step._attributes['requires'] else []
                    if not step_expressions:
                        msg = 'Failed to find requirements for attack step' \
                        ' "%s" of type "%s":\n%s'
                        raise LanguageGraphStepExpressionError(
                            msg % (
                                attack_step_name,
                                attack_step.type,
                                json.dumps(attack_step._attributes, indent = 2)
                            )
                        )

                    attack_step.requires = []
                    for step_expression in step_expressions:
                        _, \
                        result_expr_chain, \
                        _ = \
                            self.process_step_expression(
                                attack_step.asset,
                                None,
                                step_expression
                            )
                        attack_step.requires.append(
                            self.reverse_expr_chain(result_expr_chain, None))

    def _get_attacks_for_asset_type(self, asset_type: str) -> dict:
        """
        Get all Attack Steps for a specific Class

        Arguments:
        asset_type      - a string representing the class for which we want to
                          list the possible attack steps

        Return:
        A dictionary representing the set of possible attacks for the
        specified class. Each key in the dictionary is an attack name and is
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

    def _get_associations_for_asset_type(self, asset_type: str) -> list:
        """
        Get all Associations for a specific Class

        Arguments:
        asset_type      - a string representing the class for which we want to
                          list the associations

        Return:
        A dictionary representing the set of associations for the specified
        class. Each key in the dictionary is an attack name and is associated
        with a dictionary containing other characteristics of the attack such
        as type of attack, TTC distribution, child attack steps and other
        information
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
        while (assoc):
            associations.append(assoc)
            assoc = next(assoc_iter, None)

        return associations

    def _get_variables_for_asset_type(
            self, asset_type: str) -> dict:
        """
        Get a variables for a specific asset type by name.
        Note: Variables are the ones specified in MAL through `let` statements

        Arguments:
        asset_type      - a string representing the type of asset which
                          contains the variables

        Return:
        A dictionary representing the step expressions for the variables
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


    def get_association_by_fields_and_assets(
            self,
            first_field: str,
            second_field: str,
            first_asset_name: str,
            second_asset_name: str
        ) -> Optional[LanguageGraphAssociation]:
        """
        Get an association based on its field names and asset types

        Arguments:
        first_field         - a string containing the first field
        second_field        - a string containing the second field
        first_asset_name    - a string representing the first asset type
        second_asset_name   - a string representing the second asset type

        Return:
        The association matching the fieldnames and asset types.
        None if there is no match.
        """
        first_asset = self.assets[first_asset_name]
        if first_asset is None:
            raise LookupError(
                f'Failed to find asset with name \"{first_asset_name}\" in '
                'the language graph.'
            )

        second_asset = self.assets[second_asset_name]
        if second_asset is None:
            raise LookupError(
                f'Failed to find asset with name \"{second_asset_name}\" in '
                'the language graph.'
            )

        for assoc_name, assoc in first_asset.get_all_associations().items():
            logger.debug(
                'Compare ("%s", "%s", "%s", "%s") to '
                '("%s", "%s", "%s", "%s").',
                first_asset_name, first_field,
                second_asset_name, second_field,
                assoc.left_field.asset.name, assoc.left_field.fieldname,
                assoc.right_field.asset.name, assoc.right_field.fieldname
            )

            # If the asset and fields match either way we accept it as a
            # match.
            if assoc.left_field.fieldname == first_field and \
                assoc.right_field.fieldname == second_field and \
                first_asset.is_subasset_of(assoc.left_field.asset) and \
                second_asset.is_subasset_of(assoc.right_field.asset):
                return assoc

            if assoc.left_field.fieldname == second_field and \
                assoc.right_field.fieldname == first_field and \
                second_asset.is_subasset_of(assoc.left_field.asset) and \
                first_asset.is_subasset_of(assoc.right_field.asset):
                return assoc

        return None
