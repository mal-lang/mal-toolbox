"""
MAL-Toolbox Attack Graph Node
"""

from __future__ import annotations
import copy
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Optional
    from ..language import LanguageGraphAttackStep, Detector
    from ..model import ModelAsset

class AttackGraphNode:
    """Node part of AttackGraph"""

    def __init__(
        self,
        node_id: int,
        lg_attack_step: LanguageGraphAttackStep,
        model_asset: Optional[ModelAsset] = None,
        ttc_dist: Optional[dict] = None,
        existence_status: Optional[bool] = None
    ):
        self.lg_attack_step = lg_attack_step
        self.name = lg_attack_step.name
        self.type = lg_attack_step.type
        self.ttc = ttc_dist if ttc_dist is not None else lg_attack_step.ttc
        self.tags = lg_attack_step.tags
        self.detectors = lg_attack_step.detectors

        self.id = node_id
        self.model_asset = model_asset
        self.existence_status = existence_status
        self.children: set[AttackGraphNode] = set()
        self.parents: set[AttackGraphNode] = set()
        self.extras: dict = {}

    def to_dict(self) -> dict:
        """Convert node to dictionary"""
        node_dict: dict = {
            'id': self.id,
            'type': self.type,
            'lang_graph_attack_step': self.lg_attack_step.full_name,
            'name': self.name,
            'ttc': self.ttc,
            'children': {child.id: child.full_name for child in
                self.children},
            'parents': {parent.id: parent.full_name for parent in
                self.parents},
        }

        for detector in self.detectors.values():
            node_dict.setdefault('detectors', {})[detector.name] = detector.to_dict()
        if self.model_asset is not None:
            node_dict['asset'] = str(self.model_asset.name)
        if self.existence_status is not None:
            node_dict['existence_status'] = self.existence_status
        if self.tags:
            node_dict['tags'] = list(self.tags)
        if self.extras:
            node_dict['extras'] = self.extras

        return node_dict


    def __repr__(self) -> str:
        return (f'AttackGraphNode(name: "{self.full_name}", id: {self.id}, '
            f'type: {self.type})')


    def __deepcopy__(self, memo) -> AttackGraphNode:
        """Deep copy an attackgraph node

        The deepcopy will copy over node specific information, such as type,
        name, etc., but it will not copy attack graph relations such as
        parents, children, or attackers it is compromised by. These references
        should be recreated when deepcopying the attack graph itself.

        """

        # Check if the object is already in the memo dictionary
        if id(self) in memo:
            return memo[id(self)]

        copied_node = AttackGraphNode(
            node_id = self.id,
            model_asset = self.model_asset,
            lg_attack_step = self.lg_attack_step
        )

        copied_node.tags = copy.deepcopy(self.tags, memo)
        copied_node.extras = copy.deepcopy(self.extras, memo)
        copied_node.ttc = copy.deepcopy(self.ttc, memo)

        copied_node.existence_status = self.existence_status

        # Remember that self was already copied
        memo[id(self)] = copied_node

        return copied_node


    @property
    def full_name(self) -> str:
        """
        Return the full name of the attack step. This is a combination of the
        asset name to which the attack step belongs and attack step name
        itself.
        """
        if self.model_asset:
            full_name = self.model_asset.name + ':' + self.name
        else:
            full_name = str(self.id) + ':' + self.name
        return full_name


    @cached_property
    def info(self) -> dict[str, str]:
        return self.lg_attack_step.info
