"""
MAL-Toolbox Attack Graph Node Dataclass
"""

from dataclasses import field, dataclass
from typing import Any, List, Optional

from maltoolbox.attackgraph.attacker import Attacker

@dataclass
class AttackGraphNode:
    id: str
    type: str
    name: str
    ttc: dict
    asset: Any = None
    children: List['AttackGraphNode'] = field(default_factory=list)
    parents: List['AttackGraphNode'] = field(default_factory=list)
    defense_status: Optional[float] = None
    existence_status: Optional[bool] = None
    is_viable: bool = True
    is_necessary: bool = True
    compromised_by: List['Attacker'] = field(default_factory=list)
    extra: Optional[dict] = None
    mitre_info: Optional[str] = None
    tags: Optional[List[str]] = None
    observations: Optional[dict] = None
    attributes: Optional[dict] = None
    attacker: Optional['Attacker'] = None

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

        if self.asset is not None:
            node_dict['asset'] = self.asset.metaconcept + ':' \
                + str(self.asset.id)
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
        if self.observations is not None:
            node_dict['observations'] = self.observations

        return node_dict
