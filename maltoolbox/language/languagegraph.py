"""MAL-Toolbox Language Graph functionality
- A graph representation of a MAL language
- Used when creating models and when generating attack graphs
"""

from __future__ import annotations

import json
import logging
from typing import Any
import zipfile

from maltoolbox.exceptions import LanguageGraphAssociationError, LanguageGraphException, LanguageGraphSuperAssetNotFoundError
from maltoolbox.file_utils import load_dict_from_json_file, load_dict_from_yaml_file, save_dict_to_file
from maltoolbox.language.compiler.mal_compiler import MalCompiler
from maltoolbox.language.expression_chain import ExpressionsChain
from maltoolbox.language.language_graph_builder import generate_graph
from maltoolbox.language.languagegraph_asset import LanguageGraphAsset
from maltoolbox.language.languagegraph_assoc import LanguageGraphAssociation, LanguageGraphAssociationField
from maltoolbox.language.languagegraph_attack_step import LanguageGraphAttackStep
from maltoolbox.language.step_expression_processor import process_attack_step_expression, process_collect_step_expression, process_field_step_expression, process_set_operation_step_expression, process_step_expression, process_subType_step_expression, process_transitive_step_expression, process_variable_step_expression, reverse_expr_chain

logger = logging.getLogger(__name__)


class LanguageGraph:
    """Graph representation of a MAL language"""

    def __init__(self, lang_spec: dict | None = None):

        self.assets: dict[str, LanguageGraphAsset] = {}
        self.lang_spec = lang_spec

        if self.lang_spec is not None:
            self.metadata = {
                "version": self.lang_spec["defines"]["version"],
                "id": self.lang_spec["defines"]["id"],
            }
            self.assets = generate_graph(self.lang_spec)

    def __repr__(self) -> str:
        """String representation of a LanguageGraph"""
        return (
            f'LanguageGraph(id: "{self.metadata.get("id", "N/A")}", '
            f'version: "{self.metadata.get("version", "N/A")}")'
        )

    @classmethod
    def from_mal_spec(cls, mal_spec_file: str) -> LanguageGraph:
        """Create a LanguageGraph from a .mal file (a MAL spec).

        Arguments:
        ---------
        mal_spec_file   -   the path to the .mal file

        """
        return language_graph_from_mal_spec(mal_spec_file)

    @classmethod
    def from_mar_archive(cls, mar_archive: str) -> LanguageGraph:
        """Create a LanguageGraph from a ".mar" archive provided by malc
        (https://github.com/mal-lang/malc).

        Arguments:
        ---------
        mar_archive     -   the path to a ".mar" archive

        """
        return language_graph_from_mar_archive(mar_archive)

    @property
    def associations(self) -> set[LanguageGraphAssociation]:
        """Return all associations in the language graph.
        """
        return get_language_graph_associations(self)

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
        return save_dict_to_file(filename, language_graph_to_dict(self))

    @classmethod
    def load_from_file(cls, filename: str) -> LanguageGraph:
        """Create LanguageGraph from mal, mar, yaml or json"""
        return load_language_graph_from_file(filename)

    def save_language_specification_to_json(self, filename: str) -> None:
        """Save a MAL language specification dictionary to a JSON file

        Arguments:
        ---------
        filename        - the JSON filename where the language specification will be written

        """
        logger.info('Save language specification to %s', filename)
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(self.lang_spec, file, indent=4)

    def process_attack_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any]
    ) -> tuple[
                LanguageGraphAsset,
                None,
                str
            ]:
        """The attack step expression just adds the name of the attack
        step. All other step expressions only modify the target
        asset and parent associations chain.
        """
        return process_attack_step_expression(
            target_asset,
            step_expression['name']
        )

    def process_set_operation_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any],
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """The set operators are used to combine the left hand and right
        hand targets accordingly.
        """
        return process_set_operation_step_expression(
            self.assets, target_asset, expr_chain, step_expression, self.lang_spec
        )

    def process_variable_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        step_expression: dict[str, Any],
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:

        return process_variable_step_expression(
            self.assets, target_asset, step_expression, self.lang_spec
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
        """Change the target asset from the current one to the associated
        asset given the specified field name and add the parent
        fieldname and association to the parent associations chain.
        """
        return process_field_step_expression(
            target_asset, step_expression
        )

    def process_transitive_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any],
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """Create a transitive tuple entry that applies to the next
        component of the step expression.
        """
        return process_transitive_step_expression(
            self.assets, target_asset, expr_chain, step_expression, self.lang_spec
        )

    def process_subType_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any],
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain,
            None
        ]:
        """Create a subType tuple entry that applies to the next
        component of the step expression and changes the target
        asset to the subasset.
        """
        return process_subType_step_expression(
            self.assets, target_asset, expr_chain, step_expression, self.lang_spec
        )

    def process_collect_step_expression(
        self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict[str, Any],
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain | None,
            str | None
        ]:
        """Apply the right hand step expression to left hand step
        expression target asset and parent associations chain.
        """
        return process_collect_step_expression(
            self.assets, target_asset, expr_chain, step_expression, self.lang_spec
        )

    def process_step_expression(self,
        target_asset: LanguageGraphAsset,
        expr_chain: ExpressionsChain | None,
        step_expression: dict,
    ) -> tuple[
            LanguageGraphAsset,
            ExpressionsChain | None,
            str | None
        ]:
        """Recursively process an attack step expression.

        Arguments:
        ---------
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
        ------
        A tuple triplet containing the target asset, the resulting parent
        associations chain, and the name of the attack step.

        """
        return process_step_expression(
            self.assets, target_asset, expr_chain, step_expression, self.lang_spec
        )

    def reverse_expr_chain(
        self,
        expr_chain: ExpressionsChain | None,
        reverse_chain: ExpressionsChain | None
    ) -> ExpressionsChain | None:
        """Recursively reverse the associations chain. From parent to child or
        vice versa.

        Arguments:
        ---------
        expr_chain          - A chain of nested tuples that specify the
                              associations and set operations chain from an
                              attack step to its connected attack step.
        reverse_chain       - A chain of nested tuples that represents the
                              current reversed associations chain.

        Return:
        ------
        The resulting reversed associations chain.

        """
        return reverse_expr_chain(
            expr_chain, reverse_chain
        )

    def regenerate_graph(self) -> None:
        """Regenerate language graph starting from the MAL language specification
        given in the constructor.
        """
        self.assets = generate_graph(self.lang_spec)

    def _to_dict(self) -> dict[str, Any]:
        return language_graph_to_dict(self)


def disaggregate_attack_step_full_name(
    attack_step_full_name: str
) -> list[str]:
    """From an attack step full name, get (asset_name, attack_step_name)"""
    return attack_step_full_name.split(':')


def language_graph_to_dict(graph: LanguageGraph) -> dict:
    """Converts LanguageGraph into a dict"""
    logger.debug(
        'Serializing %s assets.', len(graph.assets.items())
    )

    serialized_graph = {'metadata': graph.metadata}
    for asset in graph.assets.values():
        serialized_graph[asset.name] = asset.to_dict()

    return serialized_graph


def language_graph_from_dict(serialized_graph: dict) -> LanguageGraph:
    """Rebuild a LanguageGraph instance from its serialized dict form."""
    logger.debug('Create language graph from dictionary.')
    lang_graph = LanguageGraph()
    lang_graph.metadata = serialized_graph.pop('metadata')

    # Create asset nodes
    for asset in serialized_graph.values():
        logger.debug('Create asset %s', asset['name'])
        lang_graph.assets[asset['name']] = LanguageGraphAsset(
            name=asset['name'],
            own_associations={},
            attack_steps={},
            info=asset['info'],
            own_super_asset=None,
            own_sub_assets=list(),
            own_variables={},
            is_abstract=asset['is_abstract']
        )

    # Link inheritance
    for asset in serialized_graph.values():
        asset_node = lang_graph.assets[asset['name']]
        if super_name := asset['super_asset']:
            try:
                super_asset = lang_graph.assets[super_name]
            except KeyError:
                msg = f'Super asset "{super_name}" for "{asset["name"]}" not found'
                logger.error(msg)
                raise LanguageGraphSuperAssetNotFoundError(msg)

            super_asset.own_sub_assets.append(asset_node)
            asset_node.own_super_asset = super_asset

    # Associations
    for asset in serialized_graph.values():
        logger.debug('Create associations for asset %s', asset['name'])
        a_node = lang_graph.assets[asset['name']]
        for assoc in asset['associations'].values():
            try:
                left = lang_graph.assets[assoc['left']['asset']]
                right = lang_graph.assets[assoc['right']['asset']]
            except KeyError as e:
                side = 'Left' if 'left' in str(e) else 'Right'
                msg = f'{side} asset for association "{assoc["name"]}" not found'
                logger.error(msg)
                raise LanguageGraphAssociationError(msg)
            assoc_node = LanguageGraphAssociation(
                name=assoc['name'],
                left_field=LanguageGraphAssociationField(
                    left, assoc['left']['fieldname'],
                    assoc['left']['min'], assoc['left']['max']
                ),
                right_field=LanguageGraphAssociationField(
                    right, assoc['right']['fieldname'],
                    assoc['right']['min'], assoc['right']['max']
                ),
                info=assoc['info']
            )
            lang_graph._link_association_to_assets(assoc_node, left, right)

    # Variables
    for asset in serialized_graph.values():
        a_node = lang_graph.assets[asset['name']]
        for var, (target_name, expr_dict) in asset['variables'].items():
            target = lang_graph.assets[target_name]
            a_node.own_variables[var] = (
                target, ExpressionsChain._from_dict(expr_dict, lang_graph)
            )

    # Attack steps
    for asset in serialized_graph.values():
        a_node = lang_graph.assets[asset['name']]
        for step in asset['attack_steps'].values():
            a_node.attack_steps[step['name']] = LanguageGraphAttackStep(
                name=step['name'],
                type=step['type'],
                asset=a_node,
                causal_mode=step.get('causal_mode'),
                ttc=step['ttc'],
                overrides=step['overrides'],
                own_children={}, own_parents={},
                info=step['info'],
                tags=list(step['tags'])
            )

    # Inheritance for attack steps
    for asset in serialized_graph.values():
        a_node = lang_graph.assets[asset['name']]
        for step in asset['attack_steps'].values():
            if not (inh := step.get('inherits')):
                continue
            a_step = a_node.attack_steps[step['name']]
            a_name, s_name = disaggregate_attack_step_full_name(inh)
            a_step.inherits = lang_graph.assets[a_name].attack_steps[s_name]

    # Expression chains and requirements
    for asset in serialized_graph.values():
        a_node = lang_graph.assets[asset['name']]
        for step in asset['attack_steps'].values():
            s_node = a_node.attack_steps[step['name']]
            for tgt_name, exprs in step['own_children'].items():
                t_asset, t_step = disaggregate_attack_step_full_name(tgt_name)
                t_node = lang_graph.assets[t_asset].attack_steps[t_step]
                for expr in exprs:
                    chain = ExpressionsChain._from_dict(expr, lang_graph)
                    s_node.own_children.setdefault(t_node, []).append(chain)
            for tgt_name, exprs in step['own_parents'].items():
                t_asset, t_step = disaggregate_attack_step_full_name(tgt_name)
                t_node = lang_graph.assets[t_asset].attack_steps[t_step]
                for expr in exprs:
                    chain = ExpressionsChain._from_dict(expr, lang_graph)
                    s_node.own_parents.setdefault(t_node, []).append(chain)
            if step['type'] in ('exist', 'notExist') and (reqs := step.get('requires')):
                s_node.own_requires = [
                    chain for expr in reqs
                    if (chain := ExpressionsChain._from_dict(expr, lang_graph))
                ]

    return lang_graph


def load_language_graph_from_file(filename: str) -> LanguageGraph:
    """Create LanguageGraph from mal, mar, yaml or json"""
    lang_graph = None
    if filename.endswith('.mal'):
        lang_graph = language_graph_from_mal_spec(filename)
    elif filename.endswith('.mar'):
        lang_graph = language_graph_from_mar_archive(filename)
    elif filename.endswith(('.yaml', '.yml')):
        lang_graph = language_graph_from_dict(load_dict_from_yaml_file(filename))
    elif filename.endswith('.json'):
        lang_graph = language_graph_from_dict(load_dict_from_json_file(filename))
    else:
        raise TypeError(
            "Unknown file extension, expected json/mal/mar/yml/yaml"
        )
    if lang_graph:
        return lang_graph
    raise LanguageGraphException(
        f'Failed to load language graph from file "{filename}".'
    )


def get_language_graph_associations(language_graph: LanguageGraph):
    return {
        assoc for asset in language_graph.assets.values()
        for assoc in asset.associations.values()
    }


def language_graph_from_mal_spec(mal_spec_file: str) -> LanguageGraph:
    """Create a LanguageGraph from a .mal file (a MAL spec).

    Arguments:
    ---------
    mal_spec_file   -   the path to the .mal file

    """
    logger.info("Loading mal spec %s", mal_spec_file)
    return LanguageGraph(MalCompiler().compile(mal_spec_file))


def language_graph_from_mar_archive(mar_archive: str) -> LanguageGraph:
    """Create a LanguageGraph from a ".mar" archive provided by malc
    (https://github.com/mal-lang/malc).

    Arguments:
    ---------
    mar_archive     -   the path to a ".mar" archive

    """
    logger.info('Loading mar archive %s', mar_archive)
    with zipfile.ZipFile(mar_archive, 'r') as archive:
        langspec = archive.read('langspec.json')
        return LanguageGraph(json.loads(langspec))


