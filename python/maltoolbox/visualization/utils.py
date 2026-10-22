from maltoolbox.model import Model


def position_assets(model: Model):
    """Assigns (x, y) positions to assets in a graph where relations are stored
    in asset.associated_assets[relation_name] = [related_assets...].
    Positions are stored in asset.extras['position'] = {'x': ..., 'y': ...}.
    Layout is computed by traversing connected components.
    Adds uniform padding between assets.
    """
    visited = set()
    x_spacing = 200
    y_spacing = 200
    padding = 50  # uniform padding

    def traverse(asset, depth, index, component):
        if asset in visited:
            return
        visited.add(asset)
        component.append((asset, depth, index))
        neighbors = []
        for rel_list in asset.associated_assets.values():
            neighbors.extend(rel_list)
        for i, neighbor in enumerate(neighbors):
            if neighbor not in visited:
                traverse(neighbor, depth + 1, i, component)

    def assign_positions(component):
        for i, (asset, depth, index) in enumerate(component):
            x = index * (x_spacing + padding)
            y = depth * (y_spacing + padding)
            asset.extras.setdefault('position', {})
            asset.extras['position']['x'] = x
            asset.extras['position']['y'] = y

    for asset in model.assets.values():
        if asset not in visited:
            component: list[tuple] = []
            traverse(asset, 0, 0, component)
            assign_positions(component)
