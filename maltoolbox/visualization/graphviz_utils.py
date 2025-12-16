from pathlib import Path
from os import PathLike
from typing import Optional
import random

import graphviz

from ..attackgraph import AttackGraph
from ..model import Model

graphviz_bright_colors = [
    "aliceblue", "antiquewhite", "antiquewhite1", "antiquewhite2", "azure", "azure1", "azure2",
    "beige", "bisque", "bisque1", "bisque2", "blanchedalmond",
    "cornsilk", "cornsilk1", "cornsilk2",
    "floralwhite", "gainsboro", "ghostwhite", "gold", "gold1", "gold2",
    "honeydew", "honeydew1", "honeydew2",
    "ivory", "ivory1", "ivory2",
    "khaki", "khaki1", "khaki2",
    "lavender", "lavenderblush", "lavenderblush1", "lavenderblush2",
    "lemonchiffon", "lemonchiffon1", "lemonchiffon2",
    "lightblue", "lightblue1", "lightblue2",
    "lightcyan", "lightcyan1", "lightcyan2",
    "lightgoldenrod", "lightgoldenrod1", "lightgoldenrod2",
    "lightgoldenrodyellow", "lightgray",
    "lightpink", "lightpink1", "lightpink2",
    "lightsalmon", "lightsalmon1", "lightsalmon2",
    "lightskyblue", "lightskyblue1", "lightskyblue2",
    "lightslategray", "lightsteelblue", "lightsteelblue1", "lightsteelblue2",
    "lightyellow", "lightyellow1", "lightyellow2",
    "linen", "mintcream", "mistyrose", "mistyrose1", "mistyrose2",
    "moccasin", "navajowhite", "navajowhite1", "navajowhite2",
    "oldlace", "papayawhip", "peachpuff", "peachpuff1", "peachpuff2",
    "pink", "pink1", "pink2", "plum", "plum1", "plum2", "powderblue",
    "seashell", "seashell1", "seashell2",
    "snow", "snow1", "snow2",
    "thistle", "thistle1", "thistle2",
    "wheat", "wheat1", "wheat2",
    "white", "whitesmoke", "yellow", "yellow1", "yellow2",
]


def _resolve_graphviz_path(path: Optional[PathLike], default_name: str):
    """
    Resolve a user-provided path into (directory, filename_without_ext).

    - If path is None → ('.', default_name)
    - If path is a directory → (path, default_name)
    - If path is a file → (parent_directory, file_stem)
    """
    if path is None:
        return ".", default_name

    p = Path(path)

    if p.is_dir():
        return str(p), default_name

    # It's a file path
    return str(p.parent), p.stem


def render_model(model: Model, path: Optional[PathLike] = None, view=True):
    """Render a model in graphviz, create PDF, and open it."""
    dot = graphviz.Digraph(model.name)

    # Create nodes
    asset_type_colors: dict[str, str] = {}
    for asset in model.assets.values():
        bg_color = asset_type_colors.get(asset.lg_asset.name)
        if not bg_color:
            bg_color = random.choice(graphviz_bright_colors)
            asset_type_colors[asset.lg_asset.name] = bg_color

        dot.node(str(asset.id), asset.name, style="filled", fillcolor=bg_color)

    # Create edges
    for from_asset in model.assets.values():
        for fieldname, to_assets in from_asset.associated_assets.items():
            for to_asset in to_assets:
                dot.edge(str(from_asset.id), str(to_asset.id), label=fieldname)

    directory, filename = _resolve_graphviz_path(path, model.name)
    dot.render(directory=directory, filename=f"{filename}.gv", view=view, format="pdf")


def render_attack_graph(attack_graph: AttackGraph, path: Optional[PathLike] = None, view = True):
    """Render attack graph graphviz, create PDF, and open it."""
    assert attack_graph.model, "Attack graph needs a model"

    name = attack_graph.model.name + "-attack_graph"
    dot = graphviz.Digraph(name)
    dot.graph_attr["nodesep"] = "3.0"
    dot.graph_attr["ratio"] = "compress"

    # Create nodes
    asset_colors: dict[str, str] = {}
    for node in attack_graph.nodes.values():
        assert node.model_asset, "Node needs model"

        bg_color = asset_colors.get(node.model_asset.name)
        if not bg_color:
            bg_color = random.choice(graphviz_bright_colors)
            asset_colors[node.model_asset.name] = bg_color

        match node.type:
            case "defense":
                path_color = "blue"
            case "or" | "and":
                path_color = "red"
            case "exist" | "notExist":
                path_color = "grey"
            case t:
                raise ValueError(f"Type {t} not supported")

        dot.node(
            str(node.id),
            node.full_name,
            style="filled",
            color=path_color,
            fillcolor=bg_color
        )

    # Create edges
    for parent in attack_graph.nodes.values():
        for child in parent.children:
            dot.edge(str(parent.id), str(child.id), arrowhead="normal")

    directory, filename = _resolve_graphviz_path(path, name)
    dot.render(directory=directory, filename=f"{filename}.gv", view=view, format="pdf")
