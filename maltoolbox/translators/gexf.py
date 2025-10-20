from __future__ import annotations

from maltoolbox.attackgraph import AttackGraph

from gexfpy import stringify
from gexfpy import (
    Gexf,
    Graph,
    Nodes,
    Edges,
    Node,
    Edge,
    Color,
    Attvalues,
    Attvalue,
    Thickness,
    NodeShapeContent,
    NodeShapeType,
    EdgeShapeContent,
    EdgeShapeType,
    IdtypeType,
    ModeType,
    DefaultedgetypeType,
    Attribute,
    AttrtypeType,
    Attributes,
)


def attack_graph_to_gexf(
    attack_graph: AttackGraph,
    node_type_shape_map: dict[str, NodeShapeContent] = {
        "or": NodeShapeContent(value=NodeShapeType.DISC),
        "and": NodeShapeContent(value=NodeShapeType.DIAMOND),
        "exist": NodeShapeContent(value=NodeShapeType.TRIANGLE),
        "notExist": NodeShapeContent(value=NodeShapeType.TRIANGLE),
        "defense": NodeShapeContent(value=NodeShapeType.SQUARE),
    },
    color_map: dict[str, Color] | dict[int, Color] = {},
    edge_thickness: Thickness = Thickness(value=3.0),
    edge_shape: EdgeShapeContent = EdgeShapeContent(value=EdgeShapeType.SOLID),
) -> Gexf:
    """Export an attack graph to GEXF format"""

    node_list: list[Node] = []
    edge_list: list[Edge] = []
    for node_id, node in attack_graph.nodes.items():
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
                color=[color_map.get(node_id, Color(r=0, g=0, b=0, a=0.5))],
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
