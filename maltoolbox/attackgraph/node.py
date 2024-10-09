"""
MAL-Toolbox Attack Graph Node Dataclass
"""

from __future__ import annotations
import copy
from dataclasses import field, dataclass
from typing import Any, Optional

from . import Attacker

@dataclass
class AttackGraphNode:
    """Node part of AttackGraph"""
    type: str
    name: str
    ttc: Optional[dict] = None
    id: Optional[int] = None
    asset: Optional[Any] = None
    children: list[AttackGraphNode] = field(default_factory=list)
    parents: list[AttackGraphNode] = field(default_factory=list)
    defense_status: Optional[float] = None
    existence_status: Optional[bool] = None
    is_viable: bool = True
    is_necessary: bool = True
    compromised_by: list[Attacker] = field(default_factory=list)
    mitre_info: Optional[str] = None
    tags: list[str] = field(default_factory=lambda: [])
    attributes: Optional[dict] = None

    # Optional extra metadata for AttackGraphNode
    extras: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert node to dictionary"""
        node_dict: dict = {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'ttc': self.ttc,
            'children': {},
            'parents': {},
            'compromised_by': [attacker.name for attacker in \
                self.compromised_by]
        }

        for child in self.children:
            node_dict['children'][child.id] = child.full_name
        for parent in self.parents:
            node_dict['parents'][parent.id] = parent.full_name
        if self.asset is not None:
            node_dict['asset'] = str(self.asset.name)
        if self.defense_status is not None:
            node_dict['defense_status'] = str(self.defense_status)
        if self.existence_status is not None:
            node_dict['existence_status'] = str(self.existence_status)
        if self.is_viable is not None:
            node_dict['is_viable'] = str(self.is_viable)
        if self.is_necessary is not None:
            node_dict['is_necessary'] = str(self.is_necessary)
        if self.mitre_info is not None:
            node_dict['mitre_info'] = str(self.mitre_info)
        if self.tags:
            node_dict['tags'] = str(self.tags)
        if self.extras:
            node_dict['extras'] = self.extras

        return node_dict

    def __repr__(self) -> str:
        return str(self.to_dict())

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
            self.type,
            self.name,
            self.ttc,
            self.id,
            self.asset,
            [],
            [],
            self.defense_status,
            self.existence_status,
            self.is_viable,
            self.is_necessary,
            [],
            self.mitre_info,
            [],
            {},
            {}
        )

        copied_node.tags = copy.deepcopy(self.tags, memo)
        copied_node.attributes = copy.deepcopy(self.attributes, memo)
        copied_node.extras = copy.deepcopy(self.extras, memo)

        # Remember that self was already copied
        memo[id(self)] = copied_node

        return copied_node

    def is_compromised(self) -> bool:
        """
        Return True if any attackers have compromised this node.
        False, otherwise.
        """
        return len(self.compromised_by) > 0

    def is_compromised_by(self, attacker: Attacker) -> bool:
        """
        Return True if the attacker given as an argument has compromised this
        node.
        False, otherwise.

        Arguments:
        attacker    - the attacker we are interested in
        """
        return attacker in self.compromised_by

    def compromise(self, attacker: Attacker) -> None:
        """
        Have the attacker given as a parameter compromise this node.

        Arguments:
        attacker    - the attacker that will compromise the node
        """
        attacker.compromise(self)

    def undo_compromise(self, attacker: Attacker) -> None:
        """
        Remove the attacker given as a parameter from the list of attackers
        that have compromised this node.

        Arguments:
        attacker    - the attacker that we wish to remove from the compromised
                      list.
        """
        attacker.undo_compromise(self)

    def is_enabled_defense(self) -> bool:
        """
        Return True if this node is a defense node and it is enabled and not
        suppressed via tags.
        False, otherwise.
        """
        return self.type == 'defense' and \
            'suppress' not in self.tags and \
            self.defense_status == 1.0

    def is_available_defense(self) -> bool:
        """
        Return True if this node is a defense node and it is not fully enabled
        and not suppressed via tags. False otherwise.
        """
        return self.type == 'defense' and \
            'suppress' not in self.tags and \
            self.defense_status != 1.0

    @property
    def full_name(self) -> str:
        """
        Return the full name of the attack step. This is a combination of the
        asset name to which the attack step belongs and attack step name
        itself.
        """
        if self.asset:
            full_name = self.asset.name + ':' + self.name
        else:
            full_name = str(self.id) + ':' + self.name
        return full_name
