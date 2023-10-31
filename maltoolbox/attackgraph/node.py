"""
MAL-Toolbox Attack Graph Node Dataclass
"""

from dataclasses import dataclass
from typing import Any, List, Optional, ForwardRef

from maltoolbox.attackgraph import attacker

@dataclass
class AttackGraphNode:
    id: str = None
    type: str = None
    asset: Any = None
    name: str = None
    ttc: dict = None
    children: List[ForwardRef('AttackGraphNode')] = None
    parents: List[ForwardRef('AttackGraphNode')] = None
    defense_status: dict = None
    existence_status: bool = None
    is_viable: bool = True
    is_necessary: bool = True
    compromised_by: List[ForwardRef('Attacker')] = None
    extra: dict = None
    mitre_info: str = None
    tags: List[str] = None
    observations: dict = None

    def to_dict(self):
        node_dict = {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'ttc': self.ttc,
            'children': [child.id for child in self.children],
            'parents': [parent.id for parent in self.parents],
            'compromised_by': ['Attacker:' + attacker.id for attacker in \
                self.compromised_by]
        }

        if self.asset != None:
            node_dict['asset'] = self.asset.metaconcept + ':' \
                + str(self.asset.id)
        if self.defense_status != None:
            node_dict['defense_status'] = str(self.defense_status)
        if self.existence_status != None:
            node_dict['existence_status'] = str(self.existence_status)
        if self.is_viable != None:
            node_dict['is_viable'] = str(self.is_viable)
        if self.is_necessary != None:
            node_dict['is_necessary'] = str(self.is_necessary)
        if self.mitre_info != None:
            node_dict['mitre_info'] = str(self.mitre_info)
        if self.tags:
            node_dict['tags'] = str(self.tags)
        if self.observations != None:
            node_dict['observations'] = self.observations

        return node_dict
