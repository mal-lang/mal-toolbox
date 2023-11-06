"""
MAL-Toolbox Language Graph Module
"""

import logging
import json

from dataclasses import dataclass
from typing import Any, List, Optional, ForwardRef

from maltoolbox.language import specification


logger = logging.getLogger(__name__)

@dataclass
class LanguageGraphAsset:
    name: str = None
    associations: List[ForwardRef('LanguageGraphAssociation')] = None
    attack_steps: List[ForwardRef('LanguageGraphAttackStep')] = None
    description: dict = None
    # MAL languages currently do not support multiple inheritance, but this is
    # futureproofing at its most hopeful.
    super_assets: list = None
    sub_assets: list = None

    def to_dict(self):
        node_dict = {
            'name': self.name,
            'associations': [],
            'attack_steps': [],
            'description': self.description,
            'super_assets': [],
            'sub_assets': []
        }

        for assoc in self.associations:
            node_dict['associations'].append((assoc.name,
                assoc.fields[0][1],
                assoc.fields[1][1]))
        for attack_step in self.attack_steps:
            node_dict['attack_steps'].append(attack_step.name)
        for super_asset in self.super_assets:
            node_dict['super_assets'].append(super_asset.name)
        for sub_asset in self.sub_assets:
            node_dict['sub_assets'].append(sub_asset.name)
        return node_dict

    def subclasses(self, target_asset):
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

@dataclass
class LanguageGraphAssociation:
    name: str = None
    # The left and right field of the association are tuples that contain a
    # reference to the asset type, the field name, minimum, and maximum
    # cardinality. Together the two form a tuple pair.
    fields: tuple[tuple[ForwardRef('LanguageGraphAsset'), str, int, int],
        tuple[ForwardRef('LanguageGraphAsset'), str, int, int]] = ()
    description: dict = None

    def to_dict(self):
        node_dict = {
            'name': self.name,
            'left': {
                'asset': self.fields[0][0].name,
                'fieldname': self.fields[0][1],
                'min': self.fields[0][2],
                'max': self.fields[0][3]
            },
            'right': {
                'asset': self.fields[1][0].name,
                'fieldname': self.fields[1][1],
                'min': self.fields[1][2],
                'max': self.fields[1][3]
            },
            'description': self.description
        }

        return node_dict

@dataclass
class LanguageGraphAttackStep:
    name: str = None
    type: str = None
    asset: List[ForwardRef('LanguageGraphAsset')] = None
    ttc: dict = None
    children: dict = None
    parents: dict = None
    description: dict = None

    def to_dict(self):
        node_dict = {
            'name': self.name,
            'type': self.type,
            'asset': self.asset.name,
            'ttc': self.ttc,
            'children': {},
            'parents': {},
            'description': self.description
        }

        def associations_chain_to_dict(associations_chain):
            if associations_chain:
                match (associations_chain[0]):
                    case 'union' | 'intersection' | 'difference':
                        return {associations_chain[0]: {
                            'left': associations_chain_to_dict(
                                associations_chain[1]),
                            'right': associations_chain_to_dict(
                                associations_chain[2])
                            }
                        }

                    case 'field':
                        association = associations_chain[2]
                        return {association.name:
                            {'fieldname': associations_chain[1],
                             'next_association':
                                 associations_chain_to_dict(
                                     associations_chain[3])
                            }
                        }

                    case 'transitive':
                        return {'transitive':
                            associations_chain_to_dict(
                                associations_chain[1])
                        }

                    case 'subType':
                        return {'subType': associations_chain[1],
                            'expression': associations_chain_to_dict(
                                associations_chain[2])
                        }

                    case _:
                        logger.error('Unknown associations chain element '
                            f'{associations_chain[0]}!')
                        return None
            else:
                return None

        for child in self.children:
            node_dict['children'][child] = []
            for (_, associations_chain) in self.children[child]:
                node_dict['children'][child].append(
                    associations_chain_to_dict(associations_chain))

        for parent in self.parents:
            node_dict['parents'][parent] = []
            for (_, associations_chain) in self.parents[parent]:
                node_dict['parents'][parent].append(
                    associations_chain_to_dict(associations_chain))

        return node_dict

class LanguageGraph:
    def __init__(self):
        self.assets = []
        self.associations = []
        self.attack_steps = []

    def save_to_file(self, filename: str):
        """
        Save the language graph to a json file.

        Arguments:
        filename        - the name of the output file
        """

        logger.info(f'Saving language graph to \"{filename}\" file.')
        serialized_assets = []
        for asset in self.assets:
            serialized_assets.append(asset.to_dict())
        serialized_associations = []
        for associations in self.associations:
            serialized_associations.append(associations.to_dict())
        serialized_attack_steps = []
        for attack_step in self.attack_steps:
            serialized_attack_steps.append(attack_step.to_dict())
        logger.debug(f'Saving {len(serialized_assets)} assets, '
            f'{len(serialized_associations)} associations, and '
            f'{len(serialized_attack_steps)} attack steps to '
            f'\"{filename}\" file')
        serialized_graph = {
            'Assets': serialized_assets,
            'Associations': serialized_associations,
            'Attack Steps': serialized_attack_steps
        }
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(serialized_graph, file, indent=4)


    def process_step_expression(self,
        lang: dict,
        target_asset,
        associations_chain,
        step_expression: dict):
        """
        Recursively process an attack step expression.

        Arguments:
        lang                - A dictionary representing the MAL language
                              specification.
        target_asset        - The asset type that this step expression should
                              apply to. Initially it will contain the asset
                              type to which the attack step belongs.
        associations_chain  - A chain of nested tuples that specify the
                              associations and set operations chain from the
                              attack step to its parent attack step.
                              Note: This was done for the parent attack step
                              because it was easier to construct recursively
                              given the left-hand first expansion of the
                              current MAL language specification.
        step_expression     - A dictionary containing the step expression.

        Return:
        A tuple triplet containing the target asset, the resulting parent
        associations chain, and the name of the attack step.
        """
        logger.debug('Processing Step Expression:\n' \
            + json.dumps(step_expression, indent = 2))

        match (step_expression['type']):
            case 'attackStep':
                # The attack step expression just adds the name of the attack
                # step. All other step expressions only modify the target
                # asset and parent associations chain.
                return (target_asset,
                    associations_chain,
                    step_expression['name'])

            case 'union' | 'intersection' | 'difference':
                # The set operators are used to combine the left hand and right
                # hand targets accordingly.
                lh_target_asset, lh_associations_chain, _ = self.process_step_expression(
                    lang, target_asset, associations_chain, step_expression['lhs'])
                rh_target_asset, rh_associations_chain, _ = self.process_step_expression(
                    lang, target_asset, associations_chain, step_expression['rhs'])

                if lh_target_asset != rh_target_asset:
                    logger.error('Set operation has different target asset '
                        'types for each side of the expression: '
                        f'{lh_target_asset.name} and {rh_target_asset.name}!')
                    return (None, None, None)

                return (lh_target_asset,
                    (step_expression['type'],
                        lh_associations_chain,
                        rh_associations_chain),
                    None)


                return (new_target_assets, None)

            case 'variable':
                # Fetch the step expression associated with the variable from
                # the language specification and resolve that.
                variable_step_expr = specification.\
                    get_variable_for_class_by_name(lang,
                        target_asset.name, step_expression['name'])
                if variable_step_expr:
                    return self.process_step_expression(
                        lang,
                        target_asset,
                        associations_chain,
                        variable_step_expr)

                else:
                    logger.error('Failed to find variable '
                        f'{step_expression["name"]} for {target_asset.name}')
                    return (None, None, None)

            case 'field':
                # Change the target asset from the current one to the associated
                # asset given the specified field name and add the parent
                # fieldname and association to the parent associations chain.
                fieldname = step_expression['name']
                if not target_asset:
                    logger.error(f'Missing target asset for field \"{fieldname}\"!')
                    return (None, None, None)

                for association in target_asset.associations:
                    for side in range (0, 2):
                        if association.fields[side][1] == fieldname and \
                            target_asset.subclasses(
                                association.fields[1 - side][0]):
                            return (association.fields[side][0],
                                ('field',
                                    association.fields[1 - side][1],
                                    association,
                                    associations_chain
                                ),
                                None)
                logger.error(f'Failed to find field \"{fieldname}\" on '
                    f'asset \"{target_asset.name}\"!')
                return (None, None, None)

            case 'transitive':
                # Create a transitive tuple entry that applies to the next
                # component of the step expression.
                result_target_asset, \
                result_associations_chain, \
                attack_step = \
                    self.process_step_expression(lang,
                        target_asset,
                        associations_chain,
                        step_expression['stepExpression'])
                return (result_target_asset,
                    ('transitive',
                        result_associations_chain
                    ),
                    attack_step)

            case 'subType':
                # Create a subType tuple entry that applies to the next
                # component of the step expression and changes the target
                # asset to the subasset.
                subtype_name = step_expression['subType']
                result_target_asset, \
                result_associations_chain, \
                attack_step = \
                    self.process_step_expression(lang,
                        target_asset,
                        associations_chain,
                        step_expression['stepExpression'])

                subtype_asset = next((asset for asset in self.assets \
                    if asset.name == subtype_name), None)
                if not subtype_asset:
                    logger.error('Failed to find subtype attack step '
                        f'\"{subtype_name}\"')
                if not subtype_asset.subclasses(result_target_asset):
                    logger.error(f'Found subtype \"{subtype_name}\" which '
                        f'does not extend \"{result_target_asset.name}\". '
                        'Therefore the subtype cannot be resolved.')
                    return (None, None, None)
                return (subtype_asset,
                    ('subType',
                        subtype_name,
                        result_associations_chain
                    ),
                    attack_step)

            case 'collect':
                # Apply the right hand step expression to left hand step
                # expression target asset and parent associations chain.
                (lh_target_asset, lh_associations_chain, _) = \
                    self.process_step_expression(lang,
                        target_asset,
                        associations_chain,
                        step_expression['lhs'])
                (rh_target_asset,
                    rh_associations_chain,
                    rh_attack_step_name) = \
                    self.process_step_expression(lang,
                        lh_target_asset,
                        lh_associations_chain,
                        step_expression['rhs'])
                return (rh_target_asset, rh_associations_chain,
                    rh_attack_step_name)

            case _:
                logger.error('Unknown attack step type: '
                    f'{step_expression["type"]}')
                return (None, None, None)

    def reverse_associations_chain(self, associations_chain, reverse_chain):
        """
        Recursively reverse the associations chain. From parent to child or
        vice versa.

        Arguments:
        associations_chain  - A chain of nested tuples that specify the
                              associations and set operations chain from an
                              attack step to its connected attack step.
        reverse_chain       - A chain of nested tuples that represents the
                              current reversed associations chain.

        Return:
        The resulting reversed associations chain.
        """
        if not associations_chain:
            return reverse_chain
        else:
            match (associations_chain[0]):
                case 'union' | 'intersection' | 'difference':
                    left_reverse_chain = \
                        self.reverse_associations_chain(associations_chain[1],
                        reverse_chain)
                    right_reverse_chain = \
                        self.reverse_associations_chain(associations_chain[2],
                        reverse_chain)
                    return (associations_chain[0], left_reverse_chain,
                        right_reverse_chain)

                case 'transitive':
                    return ('transitive',  self.reverse_associations_chain(
                        associations_chain[1], reverse_chain))

                case 'field':
                    association = associations_chain[2]
                    for side in range (0, 2):
                        if association.fields[side][1] == associations_chain[1]:
                            opposite_fieldname = association.fields[1 - side][1]
                            break
                    reverse_chain = ('field', opposite_fieldname, association, reverse_chain)
                    return self.reverse_associations_chain(associations_chain[3],
                        reverse_chain)

                case 'subType':
                    return ('subType', associations_chain[1],
                        self.reverse_associations_chain(
                        associations_chain[2], reverse_chain))

                case _:
                    logger.error('Unknown associations chain element '
                        f'{associations_chain[0]}!')
                    return None


    def generate_graph(self, lang: dict):
        """
        Generate language graph starting from a MAL language specification

        Arguments:
        lang            - a dictionary representing the MAL language specification
        """
        # Generate all of the asset nodes of the language graph.
        for asset in lang['assets']:
            logger.debug(f'Create asset language graph nodes for asset '
                f'{asset["name"]}')
            asset_node = LanguageGraphAsset(
                name = asset['name'],
                associations = [],
                attack_steps = [],
                description = asset['meta'],
                super_assets = [],
                sub_assets = []
            )
            self.assets.append(asset_node)

        # Link assets based on inheritance
        for asset_info in lang['assets']:
            asset = next((asset for asset in self.assets \
                if asset.name == asset_info['name']), None)
            if not asset:
                logger.error('Failed to find asset '
                    f'\"{asset_info["name"]}\"!')
                return 1
            if asset_info['superAsset']:
                super_asset = next((asset for asset in self.assets \
                    if asset.name == asset_info['superAsset']), None)
                if not super_asset:
                    logger.error('Failed to find super asset '
                        f'\"{asset_info["superAsset"]}\" '
                        f'for asset \"{asset_info["name"]}\"!')
                    return 1
                super_asset.sub_assets.append(asset)
                asset.super_assets.append(super_asset)

        # Generate all of the association nodes of the language graph.
        for asset in self.assets:
            logger.debug(f'Create association language graph nodes for asset '
                f'{asset.name}')
            associations_nodes = []
            associations = specification.get_associations_for_class(lang,
                asset.name)
            for association in associations:
                left_asset = next((asset for asset in self.assets \
                    if asset.name == association['leftAsset']), None)
                if not left_asset:
                    logger.error('Failed to find left hand asset '
                        f'\"{association["leftAsset"]}\" for '
                        f'association \"{association["name"]}\"!')
                    return 1
                right_asset = next((asset for asset in self.assets \
                    if asset.name == association['rightAsset']), None)
                if not right_asset:
                    logger.error('Failed to find right hand asset '
                        f'\"{association["rightAsset"]}\" for '
                        f'association \"{association["name"]}\"!')
                    return 1

                assoc_node = next((assoc for assoc in self.associations \
                    if assoc.name == association['name'] and
                        assoc.fields[0][0] == left_asset and
                        assoc.fields[1][0] == right_asset),
                        None)
                if assoc_node:
                    # The association was already created, skip it
                    continue

                assoc_node = LanguageGraphAssociation(
                    name = association['name'],
                    fields = (
                        (left_asset,
                            association['leftField'],
                            association['leftMultiplicity']['min'],
                            association['leftMultiplicity']['max']
                        ),
                        (right_asset,
                            association['rightField'],
                            association['rightMultiplicity']['min'],
                            association['rightMultiplicity']['max']
                        )
                    ),
                    description = association['meta']
                )

                # Add the association to the left and right asset and all of
                # the assets that inherit them
                associated_assets = [left_asset, right_asset]
                while associated_assets != []:
                    asset = associated_assets.pop()
                    associated_assets.extend(asset.sub_assets)
                    if assoc_node not in asset.associations:
                        asset.associations.append(assoc_node)

                self.associations.append(assoc_node)

        # Generate all of the attack step nodes of the language graph.
        for asset in self.assets:
            logger.debug(f'Create attack steps language graph nodes for asset '
                f'{asset.name}.')
            attack_step_nodes = []
            attack_steps = specification.get_attacks_for_class(lang,
                asset.name)
            for attack_step_name, attack_step_attribs in attack_steps.items():
                logger.debug(f'Create attack step language graph nodes for '
                    f'{attack_step_name}.')

                attack_step_node = LanguageGraphAttackStep(
                    name = asset.name + ':' + attack_step_name,
                    type = attack_step_attribs['type'],
                    asset = asset,
                    ttc = attack_step_attribs['ttc'],
                    children = {},
                    parents = {},
                    description = attack_step_attribs['meta']
                )
                attack_step_node.attributes = attack_step_attribs
                asset.attack_steps.append(attack_step_node)
                self.attack_steps.append(attack_step_node)

        # Then, link all of the attack step nodes according to their associations.
        for attack_step in self.attack_steps:
            logger.debug('Determining children for attack step '\
                f'{attack_step.name}.')
            step_expressions = \
                attack_step.attributes['reaches']['stepExpressions'] if \
                    attack_step.attributes['reaches'] else []

            for step_expression in step_expressions:
                # Resolve each of the attack step expressions listed for this
                # attack step to determine children.
                (target_asset, associations_chain, attack_step_name) = \
                    self.process_step_expression(lang,
                        attack_step.asset,
                        None,
                        step_expression)
                if not target_asset:
                    logger.error('Failed to find target asset ' \
                    f'to link with for step expression:\n' +
                    json.dumps(step_expression, indent = 2))
                    print('Failed to find target asset ' \
                    f'to link with for step expression:\n' +
                    json.dumps(step_expression, indent = 2))
                    return 1

                attack_step_fullname = target_asset.name + ':' + attack_step_name
                target_attack_step = next((attack_step \
                    for attack_step in target_asset.attack_steps \
                        if attack_step.name == attack_step_fullname), None)

                if not target_attack_step:
                    logger.error('Failed to find target attack step on '
                        f'{target_asset.name} to link with for step '
                        'expression:\n' +
                        json.dumps(step_expression, indent = 2))
                    print('Failed to find target attack step on '
                        f'{target_asset.name} to link with for step '
                        'expression:\n' +
                        json.dumps(step_expression, indent = 2))
                    return 1

                # It is easier to create the parent associations chain due to
                # the left-hand first progression.
                if attack_step.name in target_attack_step.parents:
                    target_attack_step.parents[attack_step.name].append(
                        (target_attack_step, associations_chain))
                else:
                    target_attack_step.parents[attack_step.name] = \
                        [(target_attack_step, associations_chain)]
                # Reverse the parent associations chain to get the child
                # associations chain.
                if target_attack_step.name in attack_step.children:
                    attack_step.children[target_attack_step.name].append(
                        (attack_step,
                        self.reverse_associations_chain(associations_chain,
                            None)))
                else:
                    attack_step.children[target_attack_step.name] = \
                        [(attack_step,
                        self.reverse_associations_chain(associations_chain,
                            None))]

        return 0
