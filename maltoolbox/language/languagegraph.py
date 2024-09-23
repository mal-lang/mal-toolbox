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
        field(default_factory=lambda: {})
    attack_steps: dict[str, LanguageGraphAttackStep] = \
        field(default_factory = lambda: {})
    description: dict = field(default_factory=lambda: {})
    # MAL languages currently do not support multiple inheritance, but this is
    # futureproofing at its most hopeful.
    super_assets: list[LanguageGraphAsset] = field(default_factory=lambda: [])
    sub_assets: list[LanguageGraphAsset] = field(default_factory=lambda: [])
    variables: dict = field(default_factory=lambda: {})
    is_abstract: Optional[bool] = None

    def to_dict(self) -> dict:
        """Convert LanguageGraphAsset to dictionary"""
        node_dict: dict[str, Any] = {
            'name': self.name,
            'associations': {},
            'attack_steps': {},
            'description': self.description,
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
        for variable_name, (var_target_asset, var_dep_chain) in \
                self.variables.items():
            node_dict['variables'][variable_name] = (
                var_target_asset.name,
                var_dep_chain.to_dict()
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


    def get_associations(self) -> dict[str, LanguageGraphAssociation]:
        """
        Return a list of all of the associations that belong to this asset
        directly or indirectly via inheritance.

        Return:
        A list of all of the associations that apply to this asset, either
        directly or via inheritance.
        """

        associations = dict(self.associations)
        for super_asset in self.super_assets:
            associations |= super_asset.get_associations()
        return associations


    def get_variable(
        self,
        var_name: str,
        ) -> Optional[tuple]:
        """
        Return a variable matching the given name if the asset or any of its
        super assets has its definition.

        Return:
        A tuple containing the target asset and dependency chain to it if the
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
    description: dict = field(default_factory=lambda: {})

    def to_dict(self) -> dict:
        """Convert LanguageGraphAssociation to dictionary"""
        assoc_dict = {
            'name': self.name,
            'description': self.description,
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
        full_name = '%s_%s_%s_%s_%s' % (
            self.name,\
            self.left_field.fieldname,\
            self.left_field.asset.name,\
            self.right_field.fieldname,\
            self.right_field.asset.name
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
    ttc: dict = field(default_factory = lambda: {})
    overrides: bool = False
    children: dict = field(default_factory = lambda: {})
    parents: dict = field(default_factory = lambda: {})
    description: dict = field(default_factory = lambda: {})
    attributes: Optional[dict] = None
    inherits: Optional[LanguageGraphAttackStep] = None
    tags: set = field(default_factory = lambda: {})

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
            'description': self.description,
            'overrides': self.overrides,
            'inherits': self.inherits.full_name if self.inherits else None,
            'tags': list(self.tags)
        }

        for child in self.children:
            node_dict['children'][child] = []
            for (_, dep_chain) in self.children[child]:
                if dep_chain:
                    node_dict['children'][child].append(
                        dep_chain.to_dict())
                else:
                    node_dict['children'][child].append(None)

        for parent in self.parents:
            node_dict['parents'][parent] = []
            for (_, dep_chain) in self.parents[parent]:
                if dep_chain:
                    node_dict['parents'][parent].append(
                        dep_chain.to_dict())
                else:
                    node_dict['parents'][parent].append(None)

        if hasattr(self, 'requirements'):
            node_dict['requirements'] = []
            for requirement in self.requirements:
                node_dict['requirements'].append(requirement.to_dict())

        return node_dict


    def get_requirements(self):
        if not hasattr(self, 'requirements'):
            requirements = []
        else:
            requirements = self.requirements

        if self.inherits:
            requirements.extend(self.inherits.get_requirements())
        return requirements


    def __repr__(self) -> str:
        return str(self.to_dict())


class DependencyChain:
    def __init__(self, type: str, next_link: Optional[DependencyChain]):
        self.type = type
        self.next_link: Optional[DependencyChain] = next_link
        self.fieldname: str = ""
        self.association: Optional[LanguageGraphAssociation] = None
        self.left_chain: Optional[DependencyChain] = None
        self.right_chain: Optional[DependencyChain] = None
        self.subtype: Optional[Any] = None
        self.current_link: Optional[DependencyChain] = None

    def __iter__(self):
        self.current_link = self
        return self


    def __next__(self):
        if self.current_link:
            dep_chain = self.current_link
            self.current_link = self.current_link.next_link
            return dep_chain
        raise StopIteration


    def to_dict(self) -> dict:
        """Convert DependencyChain to dictionary"""
        match (self.type):
            case 'union' | 'intersection' | 'difference':
                return {
                    self.type: {
                        'left': self.left_chain.to_dict()
                                if self.left_chain else {},
                        'right': self.right_chain.to_dict()
                                 if self.right_chain else {}
                    },
                    'type': self.type
                }

            case 'field':
                if not self.association:
                    raise LanguageGraphAssociationError(
                        "Missing association for dep chain"
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
                            json.dumps(self.association.to_dict(), indent = 2)
                        )
                    )

                return {
                    self.association.full_name:
                    {
                        'fieldname': self.fieldname,
                         'asset type': asset_type,
                         'next_association':
                            self.next_link.to_dict()
                            if self.next_link else {}
                    },
                    'type': self.type
                }

            case 'transitive':
                if not self.next_link:
                    raise LanguageGraphException(
                        "No next link for transitive dependency chain"
                    )
                return {
                    'transitive': self.next_link.to_dict(),
                    'type': self.type
                }

            case 'subType':
                if not self.subtype:
                    raise LanguageGraphException(
                        "No subtype for dependency chain"
                    )
                if not self.next_link:
                    raise LanguageGraphException(
                        "No next link for subtype dependency chain"
                    )
                return {
                    'subType': self.subtype.name,
                    'expression': self.next_link.to_dict(),
                    'type': self.type
                }

            case 'collect':
                if not self.next_link:
                    raise LanguageGraphException(
                        "No next link for collect dependency chain"
                    )
                return {
                    'collect': self.next_link.to_dict(),
                    'type': self.type
                }

            case _:
                msg = 'Unknown associations chain element %s!'
                logger.error(msg, self.type)
                raise LanguageGraphAssociationError(msg % self.type)

    @classmethod
    def _from_dict(cls,
            serialized_dep_chain: dict,
            lang_graph: LanguageGraph,
        ) -> Optional[DependencyChain]:
        """Create LanguageGraph from dict
        Args:
        serialized_dep_chain    - dependency chain in dict format
        lang_graph              - the LanguageGraph that contains the assets,
                                  associations, and attack steps relevant for
                                  the dependency chain
        """

        if serialized_dep_chain is None or not serialized_dep_chain:
            return None

        if 'type' not in serialized_dep_chain:
            logger.debug(json.dumps(serialized_dep_chain, indent = 2))
            msg = 'Missing depenency chain type!'
            logger.error(msg)
            raise LanguageGraphAssociationError(msg)
            return None

        dep_chain_type = serialized_dep_chain['type']
        match (dep_chain_type ):
            case 'union' | 'intersection' | 'difference':
                new_dep_chain = DependencyChain(
                    type = dep_chain_type,
                    next_link = None
                )
                new_dep_chain.left_chain = cls._from_dict(
                    serialized_dep_chain[dep_chain_type]['left'],
                    lang_graph
                )
                new_dep_chain.right_chain = cls._from_dict(
                    serialized_dep_chain[dep_chain_type]['right'],
                    lang_graph
                )
                return new_dep_chain

            case 'field':
                assoc_name = list(serialized_dep_chain.keys())[0]
                next_link = cls._from_dict(
                    serialized_dep_chain[assoc_name]['next_association'],
                    lang_graph
                )
                new_dep_chain = DependencyChain(
                    type = 'field',
                    next_link = next_link
                )
                new_dep_chain.fieldname = serialized_dep_chain[assoc_name]\
                    ['fieldname']
                target_asset = lang_graph.assets[\
                    serialized_dep_chain[assoc_name]['asset type']]
                new_dep_chain.association = target_asset.associations[assoc_name]
                return new_dep_chain

            case 'transitive':
                next_link = cls._from_dict(
                    serialized_dep_chain['transitive'],
                    lang_graph
                )
                new_dep_chain = DependencyChain(
                    type = 'transitive',
                    next_link = next_link
                )
                return new_dep_chain

            case 'subType':
                next_link = cls._from_dict(
                    serialized_dep_chain['expression'],
                    lang_graph
                )
                subtype_name = serialized_dep_chain['subType']
                if subtype_name in lang_graph.assets:
                    subtype_asset = lang_graph.assets[subtype_name]
                else:
                    msg = 'Failed to find subtype %s'
                    logger.error(msg % subtype_name)
                    raise LanguageGraphException(msg % subtype_name)

                new_dep_chain = DependencyChain(
                    type = 'subType',
                    next_link = next_link
                )
                new_dep_chain.subtype = subtype_asset
                return new_dep_chain

            case 'collect':
                next_link = cls._from_dict(
                    serialized_dep_chain['collect'],
                    lang_graph
                )
                new_dep_chain = DependencyChain(
                    type = 'collect',
                    next_link = next_link
                )
                return new_dep_chain

            case _:
                msg = 'Unknown dependency chain type %s!'
                logger.error(msg, serialized_dep_chain['type'])
                raise LanguageGraphAssociationError(msg %
                    serialized_dep_chain['type'])


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
        for asset_name, asset_info in serialized_graph.items():
            logger.debug(
                'Create asset language graph nodes for asset %s',
                asset_info['name']
            )
            asset_node = LanguageGraphAsset(
                name = asset_info['name'],
                associations = {},
                attack_steps = {},
                description = asset_info['description'],
                super_assets = [],
                sub_assets = [],
                variables = {},
                is_abstract = asset_info['is_abstract']
            )
            lang_graph.assets[asset_info['name']] = asset_node

        # Relink assets based on inheritance
        for asset_name, asset_info in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for super_asset_name in asset_info['super_assets']:
                super_asset = lang_graph.assets[super_asset_name]
                if not super_asset:
                    msg = 'Failed to find super asset "%s" for asset "%s"!'
                    logger.error(
                        msg, asset_info["super_assets"], asset_info["name"])
                    raise LanguageGraphSuperAssetNotFoundError(
                        msg % (asset_info["super_assets"], asset_info["name"]))

                super_asset.sub_assets.append(asset)
                asset.super_assets.append(super_asset)

        # Generate all of the association nodes of the language graph.
        for asset_name, asset_info in serialized_graph.items():
            logger.debug(
                'Create association language graph nodes for asset %s',
                asset.name
            )

            asset = lang_graph.assets[asset_name]
            for association_name, association in \
                    asset_info['associations'].items():
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
                    description = association['description']
                )

                # Add the association to the left and right asset
                associated_assets = [left_asset, right_asset]
                while associated_assets != []:
                    asset = associated_assets.pop()
                    if assoc_node.full_name not in asset.associations:
                        asset.associations[assoc_node.full_name] = assoc_node

        # Recreate the variables
        for asset_name, asset_info in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for variable_name, var_info in asset_info['variables'].items():
                (target_asset_name, dep_chain_dict) = var_info
                target_asset = lang_graph.assets[target_asset_name]
                dep_chain = DependencyChain._from_dict(
                    dep_chain_dict,
                    lang_graph
                )
                asset.variables[variable_name] = (target_asset, dep_chain)

        # Recreate the attack steps
        for asset_name, asset_info in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            logger.debug(
                'Create attack steps language graph nodes for asset %s',
                asset.name
            )
            for attack_step_name, attack_step_info in \
                    asset_info['attack_steps'].items():
                attack_step_node = LanguageGraphAttackStep(
                    name = attack_step_name,
                    type = attack_step_info['type'],
                    asset = asset,
                    ttc = attack_step_info['ttc'],
                    overrides = attack_step_info['overrides'],
                    children = {},
                    parents = {},
                    description = attack_step_info['description'],
                    tags = set(attack_step_info['tags'])
                )
                asset.attack_steps[attack_step_name] = attack_step_node

        # Relink attack steps based on inheritence
        for asset_name, asset_info in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for attack_step_name, attack_step_info in \
                    asset_info['attack_steps'].items():
                if 'inherits' in attack_step_info and \
                        attack_step_info['inherits'] is not None:
                    attack_step = asset.attack_steps[attack_step_name]
                    ancestor_asset_name = get_asset_name_from_full_attack_step(
                        attack_step_info['inherits'])
                    ancestor_attack_step_name = \
                        get_attack_step_name_from_full_attack_step(
                            attack_step_info['inherits'])
                    ancestor_asset = lang_graph.assets[ancestor_asset_name]
                    ancestor_attack_step = ancestor_asset.attack_steps[\
                        ancestor_attack_step_name]
                    attack_step.inherits = ancestor_attack_step


        # Relink attack steps based on dependency chains
        for asset_name, asset_info in serialized_graph.items():
            asset = lang_graph.assets[asset_name]
            for attack_step_name, attack_step_info in \
                    asset_info['attack_steps'].items():
                attack_step = asset.attack_steps[attack_step_name]
                for child_info in attack_step_info['children'].items():
                    target_full_attack_step_name = child_info[0]
                    dep_chains = child_info[1]
                    target_asset_name = get_asset_name_from_full_attack_step(
                        target_full_attack_step_name)
                    target_attack_step_name = \
                        get_attack_step_name_from_full_attack_step(
                            target_full_attack_step_name)
                    target_asset = lang_graph.assets[target_asset_name]
                    target_attack_step = target_asset.attack_steps[
                        target_attack_step_name]
                    for dep_chain_dict in dep_chains:
                        dep_chain = DependencyChain._from_dict(
                            dep_chain_dict,
                            lang_graph
                        )
                        if target_attack_step.full_name in attack_step.children:
                            attack_step.children[target_attack_step.full_name].\
                                append((target_attack_step, dep_chain))
                        else:
                            attack_step.children[target_attack_step.full_name] = \
                                [(target_attack_step, dep_chain)]

                for parent_info in attack_step_info['parents'].items():
                    target_full_attack_step_name = parent_info[0]
                    dep_chains = parent_info[1]
                    target_asset_name = get_asset_name_from_full_attack_step(
                        target_full_attack_step_name)
                    target_attack_step_name = \
                        get_attack_step_name_from_full_attack_step(
                            target_full_attack_step_name)
                    target_asset = lang_graph.assets[target_asset_name]
                    target_attack_step = target_asset.attack_steps[
                        target_attack_step_name]
                    for dep_chain_dict in dep_chains:
                        dep_chain = DependencyChain._from_dict(
                            dep_chain_dict,
                            lang_graph
                        )
                        if target_attack_step.full_name in attack_step.parents:
                            attack_step.parents[target_attack_step.full_name].\
                                append((target_attack_step, dep_chain))
                        else:
                            attack_step.parents[target_attack_step.full_name] = \
                                [(target_attack_step, dep_chain)]

                # Recreate the requirements of exist and notExist attack steps
                if attack_step.type == 'exist' or \
                        attack_step.type == 'notExist':
                    if 'requirements' in attack_step_info:
                        dep_chains = attack_step_info['requirements']
                        attack_step.requirements = []
                        for dep_chain_dict in dep_chains:
                            dep_chain = DependencyChain._from_dict(
                                dep_chain_dict,
                                lang_graph
                            )
                            attack_step.requirements.append(dep_chain)

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
            dep_chain,
            step_expression: dict
        ) -> tuple:
        """
        Recursively process an attack step expression.

        Arguments:
        target_asset        - The asset type that this step expression should
                              apply to. Initially it will contain the asset
                              type to which the attack step belongs.
        dep_chain           - A dependency chain of linked of associations and
                              set operations from the attack step to its
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
                    dep_chain,
                    step_expression['name']
                )

            case 'union' | 'intersection' | 'difference':
                # The set operators are used to combine the left hand and right
                # hand targets accordingly.
                lh_target_asset, lh_dep_chain, _ = self.process_step_expression(
                    target_asset,
                    dep_chain,
                    step_expression['lhs']
                )
                rh_target_asset, rh_dep_chain, _ = self.process_step_expression(
                    target_asset,
                    dep_chain,
                    step_expression['rhs']
                )

                if not lh_target_asset.get_all_common_superassets(rh_target_asset):
                    logger.error(
                        "Set operation attempted between targets that"
                        " do not share any common superassets: %s and %s!",
                        lh_target_asset.name, rh_target_asset.name
                    )
                    return (None, None, None)

                new_dep_chain = DependencyChain(
                    type = step_expression['type'],
                    next_link = None)
                new_dep_chain.left_chain = lh_dep_chain
                new_dep_chain.right_chain = rh_dep_chain
                return (
                    lh_target_asset,
                    new_dep_chain,
                    None
                )

            case 'variable':
                var_name = step_expression['name']
                var_target_asset, var_dep_chain = \
                    target_asset.get_variable(var_name)
                if var_dep_chain is not None:
                    return (
                        var_target_asset,
                        var_dep_chain,
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
                        target_asset.get_associations().items():
                    if (association.left_field.fieldname == fieldname and \
                        target_asset.is_subasset_of(
                            association.right_field.asset)):
                        new_target_asset = association.left_field.asset

                    if (association.right_field.fieldname == fieldname and \
                        target_asset.is_subasset_of(
                            association.left_field.asset)):
                        new_target_asset = association.right_field.asset

                    if new_target_asset:
                        new_dep_chain = DependencyChain(
                            type = 'field',
                            next_link = dep_chain
                        )
                        new_dep_chain.fieldname = \
                            association.get_opposite_fieldname(fieldname)
                        new_dep_chain.association = association
                        return (
                            new_target_asset,
                            new_dep_chain,
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
                result_dep_chain, \
                attack_step = \
                    self.process_step_expression(
                        target_asset,
                        dep_chain,
                        step_expression['stepExpression']
                    )
                new_dep_chain = DependencyChain(
                    type = 'transitive',
                    next_link = result_dep_chain
                )
                return (
                    result_target_asset,
                    new_dep_chain,
                    attack_step
                )

            case 'subType':
                # Create a subType tuple entry that applies to the next
                # component of the step expression and changes the target
                # asset to the subasset.
                subtype_name = step_expression['subType']
                result_target_asset, \
                result_dep_chain, \
                attack_step = \
                    self.process_step_expression(
                        target_asset,
                        dep_chain,
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

                new_dep_chain = DependencyChain(
                    type = 'subType',
                    next_link = result_dep_chain)
                new_dep_chain.subtype = subtype_asset
                return (
                    subtype_asset,
                    new_dep_chain,
                    attack_step
                )

            case 'collect':
                # Apply the right hand step expression to left hand step
                # expression target asset and parent associations chain.
                (lh_target_asset, lh_dep_chain, _) = \
                    self.process_step_expression(
                        target_asset,
                        dep_chain,
                        step_expression['lhs']
                    )
                (rh_target_asset,
                    rh_dep_chain,
                    rh_attack_step_name) = \
                    self.process_step_expression(
                        lh_target_asset,
                        lh_dep_chain,
                        step_expression['rhs']
                    )
                new_dep_chain = DependencyChain(
                    type = 'collect',
                    next_link = rh_dep_chain)
                return (
                    rh_target_asset,
                    new_dep_chain,
                    rh_attack_step_name
                )

            case _:
                logger.error(
                    'Unknown attack step type: "%s"', step_expression["type"]
                )
                return (None, None, None)


    def reverse_dep_chain(
            self,
            dep_chain: Optional[DependencyChain],
            reverse_chain: Optional[DependencyChain]
        ) -> Optional[DependencyChain]:
        """
        Recursively reverse the associations chain. From parent to child or
        vice versa.

        Arguments:
        dep_chain  - A chain of nested tuples that specify the
                              associations and set operations chain from an
                              attack step to its connected attack step.
        reverse_chain       - A chain of nested tuples that represents the
                              current reversed associations chain.

        Return:
        The resulting reversed associations chain.
        """
        if not dep_chain:
            return reverse_chain
        else:
            match (dep_chain.type):
                case 'union' | 'intersection' | 'difference':
                    left_reverse_chain = \
                        self.reverse_dep_chain(dep_chain.left_chain,
                        reverse_chain)
                    right_reverse_chain = \
                        self.reverse_dep_chain(dep_chain.right_chain,
                        reverse_chain)
                    new_dep_chain = DependencyChain(
                        type = dep_chain.type,
                        next_link = None)
                    new_dep_chain.left_chain = left_reverse_chain
                    new_dep_chain.right_chain = right_reverse_chain
                    return new_dep_chain

                case 'transitive':
                    result_reverse_chain = self.reverse_dep_chain(
                        dep_chain.next_link, reverse_chain)
                    new_dep_chain = DependencyChain(
                        type = 'transitive',
                        next_link = result_reverse_chain)
                    return new_dep_chain

                case 'field':
                    association = dep_chain.association

                    if not association:
                        raise LanguageGraphException(
                            "Missing association for dep chain"
                        )

                    opposite_fieldname = association.get_opposite_fieldname(
                        dep_chain.fieldname)
                    new_dep_chain = DependencyChain(
                        type = 'field',
                        next_link = reverse_chain
                    )
                    new_dep_chain.fieldname = opposite_fieldname
                    new_dep_chain.association = association
                    return self.reverse_dep_chain(
                                dep_chain.next_link,
                                new_dep_chain
                            )

                case 'subType':
                    result_reverse_chain = self.reverse_dep_chain(
                        dep_chain.next_link,
                        reverse_chain
                    )
                    new_dep_chain = DependencyChain(
                        type = 'subType',
                        next_link = result_reverse_chain
                    )
                    new_dep_chain.subtype = dep_chain.subtype
                    return new_dep_chain

                case 'collect':
                    result_reverse_chain = self.reverse_dep_chain(
                        dep_chain.next_link,
                        reverse_chain
                    )
                    new_dep_chain = DependencyChain(
                        type = 'collect',
                        next_link = result_reverse_chain
                    )
                    return new_dep_chain

                case _:
                    msg = 'Unknown assoc chain element "%s"'
                    logger.error(msg, dep_chain.type)
                    raise LanguageGraphAssociationError(msg % dep_chain.type)


    def _generate_graph(self) -> None:
        """
        Generate language graph starting from the MAL language specification
        given in the constructor.
        """
        # Generate all of the asset nodes of the language graph.
        for asset_info in self._lang_spec['assets']:
            logger.debug(
                'Create asset language graph nodes for asset %s',
                asset_info['name']
            )
            asset_node = LanguageGraphAsset(
                name = asset_info['name'],
                associations = {},
                attack_steps = {},
                description = asset_info['meta'],
                super_assets = [],
                sub_assets = [],
                variables = {},
                is_abstract = asset_info['isAbstract']
            )
            self.assets[asset_info['name']] = asset_node

        # Link assets based on inheritance
        for asset_info in self._lang_spec['assets']:
            asset = self.assets[asset_info['name']]
            if asset_info['superAsset']:
                super_asset = self.assets[asset_info['superAsset']]
                if not super_asset:
                    msg = 'Failed to find super asset "%s" for asset "%s"!'
                    logger.error(
                        msg, asset_info["superAsset"], asset_info["name"])
                    raise LanguageGraphSuperAssetNotFoundError(
                        msg % (asset_info["superAsset"], asset_info["name"]))

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
                    description = association['meta']
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
                target_asset, dep_chain, _ = self.process_step_expression(
                    asset,
                    None,
                    variable['stepExpression']
                )
                asset.variables[variable['name']] = (target_asset, dep_chain)


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
                    description = attack_step_attribs['meta'],
                    tags = set(attack_step_attribs['tags'])
                )
                attack_step_node.attributes = attack_step_attribs
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
                                description = attack_step.description,
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

        # Then, link all of the attack step nodes according to their
        # associations.
        for asset_name, asset in self.assets.items():
            for attack_step_name, attack_step in asset.attack_steps.items():
                logger.debug(
                    'Determining children for attack step %s',
                    attack_step_name
                )

                if attack_step.attributes is None:
                    # This is simply an empty inherited attack step
                    continue

                step_expressions = \
                    attack_step.attributes['reaches']['stepExpressions'] if \
                        attack_step.attributes['reaches'] else []

                for step_expression in step_expressions:
                    # Resolve each of the attack step expressions listed for this
                    # attack step to determine children.
                    (target_asset, dep_chain, target_attack_step_name) = \
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

                    # It is easier to create the parent associations chain due to
                    # the left-hand first progression.
                    if attack_step.full_name in target_attack_step.parents:
                        target_attack_step.parents[attack_step.full_name].\
                            append((attack_step, dep_chain))
                    else:
                        target_attack_step.parents[attack_step.full_name] = \
                            [(attack_step, dep_chain)]
                    # Reverse the parent associations chain to get the child
                    # associations chain.
                    if target_attack_step.full_name in attack_step.children:
                        attack_step.children[target_attack_step.full_name].\
                            append((target_attack_step,
                            self.reverse_dep_chain(dep_chain,
                                None)))
                    else:
                        attack_step.children[target_attack_step.full_name] = \
                            [(target_attack_step,
                            self.reverse_dep_chain(dep_chain,
                                None))]

                # Evaluate the requirements of exist and notExist attack steps
                if attack_step.type == 'exist' or \
                        attack_step.type == 'notExist':
                    step_expressions = \
                        attack_step.attributes['requires']['stepExpressions'] \
                            if attack_step.attributes['requires'] else []
                    if not step_expressions:
                        msg = 'Failed to find requirements for attack step' \
                        ' "%s" of type "%s":\n%s'
                        raise LanguageGraphStepExpressionError(
                            msg % (
                                attack_step_name,
                                attack_step.type,
                                json.dumps(attack_step.attributes, indent = 2)
                            )
                        )

                    attack_step.requirements = []
                    for step_expression in step_expressions:
                        _, \
                        result_dep_chain, \
                        _ = \
                            self.process_step_expression(
                                attack_step.asset,
                                None,
                                step_expression
                            )
                        attack_step.requirements.append(result_dep_chain)

    def _get_attacks_for_asset_type(self, asset_type: str) -> dict:
        """
        Get all Attack Steps for a specific Class

        Arguments:
        asset_type      - a string representing the class for which we want to list
                          the possible attack steps

        Return:
        A dictionary representing the set of possible attacks for the specified
        class. Each key in the dictionary is an attack name and is associated
        with a dictionary containing other characteristics of the attack such as
        type of attack, TTC distribution, child attack steps and other information
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
            'language specification.', asset["name"]
        )

        for step in asset['attackSteps']:
            if step['name'] not in attack_steps:
                attack_steps[step['name']] = copy.deepcopy(step)

        return attack_steps

    def _get_associations_for_asset_type(self, asset_type: str) -> list:
        """
        Get all Associations for a specific Class

        Arguments:
        asset_type      - a string representing the class for which we want to list
                          the associations

        Return:
        A dictionary representing the set of associations for the specified
        class. Each key in the dictionary is an attack name and is associated
        with a dictionary containing other characteristics of the attack such as
        type of attack, TTC distribution, child attack steps and other information
        """
        logger.debug(
            'Get associations for %s asset from '
            'language specification.', asset_type
        )
        associations: list = []

        asset = next((asset for asset in self._lang_spec['assets'] if asset['name'] == \
            asset_type), None)
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
        NOTE: Variables are the ones specified in MAL through `let` statements

        Arguments:
        asset_type      - a string representing the type of asset which
                          contains the variable

        Return:
        A dictionary representing the step expressions for the variables
            belonging to the asset.
        """

        asset_info = next((asset for asset in self._lang_spec['assets'] if asset['name'] == \
            asset_type), None)
        if not asset_info:
            msg = 'Failed to find asset type %s in language specification '\
                'when looking for variables.'
            logger.error(msg, asset_type)
            raise LanguageGraphException(msg % asset_type)

        return asset_info['variables']

    def regenerate_graph(self) -> None:
        """
        Regenerate language graph starting from the MAL language specification
        given in the constructor.
        """

        self.assets = {}
        self._generate_graph()


    def get_asset_by_name(
            self,
            asset_name
    ) -> Optional[LanguageGraphAsset]:
        """
        Get an asset based on its name

        Arguments:
        asset_name  - a string containing the asset name

        Return:
        The asset matching the name.
        None if there is no match.
        """
        if asset_name in self.assets:
            return self.assets[asset_name]
        else:
            return None


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
        first_asset = self.get_asset_by_name(first_asset_name)
        if first_asset is None:
            raise LookupError(
                f'Failed to find asset with name \"{first_asset_name}\" in '
                'the language graph.'
            )

        second_asset = self.get_asset_by_name(second_asset_name)
        if second_asset is None:
            raise LookupError(
                f'Failed to find asset with name \"{second_asset_name}\" in '
                'the language graph.'
            )

        for assoc_name, assoc in first_asset.get_associations().items():
            logger.debug(
                'Compare ("%s", "%s", "%s", "%s") to ("%s", "%s", "%s", "%s").',
                first_asset_name, first_field,
                second_asset_name, second_field,
                assoc.left_field.asset.name, assoc.left_field.fieldname,
                assoc.right_field.asset.name, assoc.right_field.fieldname
            )

            # If the asset and fields match either way we accept it as a match.
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
