import random
import graphviz

from ..model import Model
from ..attackgraph import AttackGraph

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


def render_model(model: Model):
    """Render a model in graphviz, create pdf and open it"""
    dot = graphviz.Digraph(model.name)

    # Create nodes
    asset_type_colors: dict[str, str] = {}
    for asset in model.assets.values():
        bg_color = asset_type_colors.get(asset.lg_asset.name)
        if not bg_color:
            bg_color = random.choice(graphviz_bright_colors)
            asset_type_colors[asset.lg_asset.name] = bg_color
        dot.node(
            str(asset.id), asset.name, style="filled", fillcolor=bg_color
        )

    # Create edges
    for from_asset in model.assets.values():

        for fieldname, to_assets in from_asset.associated_assets.items():
            for to_asset in to_assets:
                dot.edge(
                    str(from_asset.id), str(to_asset.id), label=fieldname
                )
    dot.render(directory='.', view=True)

def render_attack_graph(attack_graph: AttackGraph):
    """Render attack graph graphviz, create pdf and open it"""
    assert attack_graph.model, "Attack graph needs a model"
    dot = graphviz.Graph(attack_graph.model.name)
    dot.graph_attr['nodesep'] = '3.0' # Node separation
    dot.graph_attr['ratio'] = 'compress'

    # Create nodes
    asset_colors: dict[str, str] = {}
    for node in attack_graph.nodes.values():
        assert node.model_asset, "Node needs model"
        bg_color = asset_colors.get(node.model_asset.name)
        if not bg_color:
            bg_color = random.choice(graphviz_bright_colors)
            asset_colors[node.model_asset.name] = bg_color
        path_color = 'white'
        match node.type:
            case 'defense':
                path_color = 'blue'
            case 'or':
                path_color = 'red'
            case 'and':
                path_color = 'red'
            case 'exist':
                path_color = 'grey'
            case 'notExist':
                path_color = 'grey'
            case t:
                raise ValueError(f'Type {t} not supported')

        dot.node(
            str(node.id), node.full_name, style="filled", color=path_color, fillcolor=bg_color
        )

    # Create edges
    for parent in attack_graph.nodes.values():
        for child in parent.children:
            dot.edge(str(parent.id), str(child.id))

    dot.render(directory='.', view=True)
