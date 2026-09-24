from __future__ import annotations

import colorsys
import hashlib
from typing import Literal

from maltoolbox.attackgraph import AttackGraph
from maltoolbox.model import Model

try:
    from gexfpy import (
        Attribute,
        Attributes,
        AttrtypeType,
        Attvalue,
        Attvalues,
        ClassType,
        Color,
        DefaultedgetypeType,
        Edge,
        Edges,
        EdgeShapeContent,
        EdgeShapeType,
        Gexf,
        Graph,
        IdtypeType,
        ModeType,
        Node,
        Nodes,
        NodeShapeContent,
        NodeShapeType,
        Thickness,
        stringify,
    )
except ImportError:
    raise ImportError(
        "The gexfpy package is required for GEXF export. Please install it using 'pip install \"mal-toolbox[gexf]\".'"
    )

_DEFAULT_COLOR = Color(r=0, g=0, b=0, a=0.5)

# Colors for the static AttackGraphNode types.
_NODE_TYPE_COLORS: dict[str, Color] = {
    "or": Color(r=31, g=119, b=180, a=0.8),
    "and": Color(r=214, g=39, b=40, a=0.8),
    "exist": Color(r=44, g=160, b=44, a=0.8),
    "notExist": Color(r=255, g=127, b=14, a=0.8),
    "defense": Color(r=148, g=103, b=189, a=0.8),
}

def _hash_color(value: str) -> Color:
    """Deterministically derive a display color from a string"""

    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    hue = (int(digest[:8], 16) % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.85)
    return Color(r=round(r * 255), g=round(g * 255), b=round(b * 255), a=0.8)


def attack_graph_to_gexf(
    attack_graph: AttackGraph,
    node_type_shape_map: dict[str, NodeShapeContent] = {
        "or": NodeShapeContent(value=NodeShapeType.DISC),
        "and": NodeShapeContent(value=NodeShapeType.DIAMOND),
        "exist": NodeShapeContent(value=NodeShapeType.TRIANGLE),
        "notExist": NodeShapeContent(value=NodeShapeType.TRIANGLE),
        "defense": NodeShapeContent(value=NodeShapeType.SQUARE),
    },
    color_map: Literal["node_type", "asset_type", "asset"] | None = None,
    edge_thickness: Thickness = Thickness(value=3.0),
    edge_shape: EdgeShapeContent = EdgeShapeContent(value=EdgeShapeType.SOLID),
) -> Gexf:
    """Export an attack graph to GEXF format

    color_map selects how node colors are generated automatically:
      - "node_type": color by AttackGraphNode type (or/and/exist/notExist/defense)
      - "asset_type": color by the underlying model asset's type
      - "asset": color by the underlying model asset (each asset gets its own color)
      - None: no automatic coloring
    """

    if color_map is not None and color_map not in ("node_type", "asset_type", "asset"):
        raise ValueError(
            f"color_map must be one of 'node_type', 'asset_type', 'asset' or None, "
            f"got {color_map!r}"
        )

    node_list: list[Node] = []
    edge_list: list[Edge] = []
    for node_id, node in attack_graph.nodes.items():
        color = _DEFAULT_COLOR
        if color_map == "node_type":
            color = _NODE_TYPE_COLORS.get(node.type, _DEFAULT_COLOR)
        elif color_map == "asset_type" and node.model_asset is not None:
            color = _hash_color(node.model_asset.type)
        elif color_map == "asset" and node.model_asset is not None:
            color = _hash_color(node.model_asset.name)

        node_list.append(
            Node(
                id=node_id,
                label=node.full_name,
                attvalues=Attvalues(
                    [
                        Attvalue(
                            for_value=(key if isinstance(key, int) else str(key)),
                            value=str(value),
                        )
                        for key, value in node.to_dict().items()
                        if key not in {"children", "parents"}
                    ]
                ),
                color=[color],
                shape=[
                    node_type_shape_map.get(
                        node.type, NodeShapeContent(value=NodeShapeType.DISC)
                    )
                ],
            )
        )

        for child in node.children:
            edge_list.append(
                Edge(
                    source=node_id,
                    target=child.id,
                    thickness=[edge_thickness],
                    shape=[edge_shape],
                )
            )

    graph = Graph(
        attributes=Attributes(
            class_value=ClassType.NODE,
            attribute=[
                Attribute(
                    default=[attack_graph.model.name],
                    id=0,
                    title="model_name",
                    type=AttrtypeType.STRING,
                ),
                Attribute(
                    default=[attack_graph.model.maltoolbox_version],
                    id=1,
                    title="maltoolbox_version",
                    type=AttrtypeType.STRING,
                ),
                Attribute(
                    default=[attack_graph.lang_graph.metadata["version"]],
                    id=2,
                    title="lang_version",
                    type=AttrtypeType.STRING,
                ),
                Attribute(
                    default=[attack_graph.lang_graph.metadata["id"]],
                    id=3,
                    title="lang_id",
                    type=AttrtypeType.STRING,
                ),
            ]
        ),
        nodes=Nodes(node=node_list, count=len(node_list)),
        edges=Edges(edge=edge_list, count=len(edge_list)),
        defaultedgetype=DefaultedgetypeType.DIRECTED,
        idtype=IdtypeType.INTEGER,
        mode=ModeType.STATIC,
    )

    return Gexf(graph=graph)


def model_to_gexf(
    model: Model,
    color_map: dict[str, Color] | dict[int, Color] | None = None,
    edge_thickness: Thickness = Thickness(value=8.0),
    edge_shape: EdgeShapeContent = EdgeShapeContent(value=EdgeShapeType.SOLID),
) -> Gexf:
    """Export a model to GEXF format

    If color_map is not provided, colors are generated automatically based on
    each asset's type. Pass an explicit dict (keyed by asset id) to override.
    """

    if not color_map:
        type_colors = {
            asset.type: _hash_color(asset.type) for asset in model.assets.values()
        }
        color_map = {
            asset_id: type_colors[asset.type]
            for asset_id, asset in model.assets.items()
        }

    node_list: list[Node] = []
    edge_list: list[Edge] = []

    # Create nodes for each asset
    for asset_id, asset in model.assets.items():
        node_list.append(
            Node(
                id=asset_id,
                label=asset.name,
                attvalues=Attvalues(
                    [
                        Attvalue(
                            for_value="type",
                            value=asset.type,
                        ),
                        Attvalue(
                            for_value="name",
                            value=asset.name,
                        ),
                    ]
                    + [
                        Attvalue(
                            for_value=defense_name,
                            value=str(defense_value),
                        )
                        for defense_name, defense_value in asset.defenses.items()
                    ]
                ),
                color=[color_map.get(asset_id, _DEFAULT_COLOR)],
                shape=[NodeShapeContent(value=NodeShapeType.SQUARE)],
            )
        )

        # Create edges for associations
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                edge_list.append(
                    Edge(
                        source=asset_id,
                        target=associated_asset.id,
                        thickness=[edge_thickness],
                        shape=[edge_shape],
                        label=fieldname,
                    )
                )

    graph = Graph(
        attributes=Attributes(
            class_value=ClassType.NODE,
            attribute=[
                Attribute(
                    default=[model.name],
                    id=0,
                    title="model_name",
                    type=AttrtypeType.STRING,
                ),
                Attribute(
                    default=[model.maltoolbox_version],
                    id=1,
                    title="maltoolbox_version",
                    type=AttrtypeType.STRING,
                ),
                Attribute(
                    default=[model.lang_graph.metadata["version"]],
                    id=2,
                    title="lang_version",
                    type=AttrtypeType.STRING,
                ),
                Attribute(
                    default=[model.lang_graph.metadata["id"]],
                    id=3,
                    title="lang_id",
                    type=AttrtypeType.STRING,
                ),
            ]
        ),
        nodes=Nodes(node=node_list, count=len(node_list)),
        edges=Edges(edge=edge_list, count=len(edge_list)),
        defaultedgetype=DefaultedgetypeType.UNDIRECTED,
        idtype=IdtypeType.INTEGER,
        mode=ModeType.STATIC,
    )

    return Gexf(graph=graph)


def save_gexf_to_file(
    gexf: Gexf, filename: str, pretty_print: bool = True
) -> None:
    """Write a GEXF object to a file"""

    if not filename.endswith(".gexf"):
        filename += ".gexf"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(stringify(gexf, pretty_print=pretty_print))
