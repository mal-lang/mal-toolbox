"""DrawIO exporter made by Sandor"""
import math
import xml.etree.ElementTree as ET
from xml.dom import minidom

from maltoolbox.model import Model

from .utils import position_assets

type2iconURL = {
    "Hardware": "https://uxwing.com/wp-content/themes/uxwing/download/domain-hosting/server-rack-outline-icon.png",
    "SoftwareProduct": "https://uxwing.com/wp-content/themes/uxwing/download/logistics-shipping-delivery/packing-icon.png",
    "Application": "https://uxwing.com/wp-content/themes/uxwing/download/web-app-development/coding-icon.png",
    "IDPS": "https://uxwing.com/wp-content/themes/uxwing/download/web-app-development/web-page-source-code-icon.png",
    "PhysicalZone": "https://uxwing.com/wp-content/themes/uxwing/download/location-travel-map/address-location-icon.png",
    "Information": "https://uxwing.com/wp-content/themes/uxwing/download/web-app-development/more-info-icon.png",
    "Data": "https://uxwing.com/wp-content/themes/uxwing/download/web-app-development/database-line-icon.png",
    "IAMObject": "https://uxwing.com/wp-content/themes/uxwing/download/communication-chat-call/name-id-icon.png",
    "Identity": "https://uxwing.com/wp-content/themes/uxwing/download/communication-chat-call/name-id-icon.png",
    "Privileges": "https://uxwing.com/wp-content/themes/uxwing/download/banking-finance/access-hand-key-icon.png",
    "Group": "https://uxwing.com/wp-content/themes/uxwing/download/business-professional-services/team-icon.png",
    "Credentials": "https://uxwing.com/wp-content/themes/uxwing/download/household-and-furniture/key-line-icon.png",
    "User": "https://uxwing.com/wp-content/themes/uxwing/download/peoples-avatars/unisex-male-and-female-icon.png",
    "Network": "https://uxwing.com/wp-content/themes/uxwing/download/internet-network-technology/big-data-icon.png",
    "RoutingFirewall": "https://uxwing.com/wp-content/themes/uxwing/download/internet-network-technology/encryption-icon.png",
    "ConnectionRule": "https://uxwing.com/wp-content/themes/uxwing/download/internet-network-technology/pc-network-icon.png",
    "Vulnerability": "https://uxwing.com/wp-content/themes/uxwing/download/web-app-development/cyber-security-icon.png",
    "SoftwareVulnerability": "https://uxwing.com/wp-content/themes/uxwing/download/web-app-development/cyber-security-icon.png",
    "HardwareVulnerability": "https://uxwing.com/wp-content/themes/uxwing/download/crime-security-military-law/shield-sedo-line-icon.png",
}


def create_drawio_file_with_images(
    model: Model,
    show_edge_labels=True,
    line_thickness=2,
    coordinate_scale=0.75,
    output_filename=None
):
    """Create a draw.io file with all model assets as boxes using their actual positions and images

    Args:
    ----
        model: The model containing assets and associations
        output_filename: Name of the output draw.io file
        show_edge_labels: If True, show association type as text on edges. If False, edges will have no labels.
        line_thickness: Thickness of the edges in pixels (default: 2)
        coordinate_scale: Scale factor for model coordinates (default: 1.0, use 0.5 for half size, 2.0 for double size)

    """
    if not all(a.extras.get('position') for a in model.assets.values()):
        # Give assets positions if not already set
        position_assets(model)

    output_filename = output_filename or (
        (model.name or "model_assets_with_images") + ".drawio"
    )

    # Use the type2iconURL mapping for image URLs
    type_images = type2iconURL

    # Create root element
    root = ET.Element("mxfile")
    root.set("host", "app.diagrams.net")
    root.set("modified", "2024-01-01T00:00:00.000Z")
    root.set("agent", "5.0")
    root.set("version", "24.7.17")
    root.set("et", "https://www.diagrams.net/")
    root.set("type", "device")

    # Create diagram element
    diagram = ET.SubElement(root, "diagram")
    diagram.set("id", "model-assets")
    diagram.set("name", "Model Assets")

    # Create mxGraphModel
    mxgraph = ET.SubElement(diagram, "mxGraphModel")
    mxgraph.set("dx", "1422")
    mxgraph.set("dy", "754")
    mxgraph.set("grid", "1")
    mxgraph.set("gridSize", "10")
    mxgraph.set("guides", "1")
    mxgraph.set("tooltips", "1")
    mxgraph.set("connect", "1")
    mxgraph.set("arrows", "1")
    mxgraph.set("fold", "1")
    mxgraph.set("page", "1")
    mxgraph.set("pageScale", "1")
    mxgraph.set("pageWidth", "2000")
    mxgraph.set("pageHeight", "1500")
    mxgraph.set("math", "0")
    mxgraph.set("shadow", "0")

    # Create root cell
    root_cell = ET.SubElement(mxgraph, "root")

    # Create default parent
    default_parent = ET.SubElement(root_cell, "mxCell")
    default_parent.set("id", "0")

    # Create parent for edges (back layer)
    edges_parent = ET.SubElement(root_cell, "mxCell")
    edges_parent.set("id", "1")
    edges_parent.set("parent", "0")

    # Create default parent for model (front layer)
    model_parent = ET.SubElement(root_cell, "mxCell")
    model_parent.set("id", "2")
    model_parent.set("parent", "0")

    # Get assets and use their actual positions
    assets = list(model.assets.values())

    # Box dimensions
    box_width = 150
    box_height = 80

    # Find the bounds of all assets to center the diagram
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    for asset in assets:
        if asset.extras:
            x = asset.extras.get("position", {}).get("x", 0)
            y = asset.extras.get("position", {}).get("y", 0)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    # If no positions found, use default bounds
    if min_x == float("inf"):
        min_x = min_y = 0
        max_x = max_y = 1000

    # Add some padding
    padding = 100
    min_x -= padding
    min_y -= padding
    max_x += padding
    max_y += padding

    # Create boxes for each asset using their actual positions
    for asset in assets:

        # Get position from extras, with fallback to grid layout
        if hasattr(asset, "extras") and asset.extras and "position" in asset.extras:
            x = round(asset.extras["position"].get("x", 0) * coordinate_scale)
            y = round(asset.extras["position"].get("y", 0) * coordinate_scale)
        else:
            # Fallback to grid layout if no position data
            i = list(model.assets.keys()).index(asset.id)
            cols = math.ceil(math.sqrt(len(assets)))
            row = i // cols
            col = i % cols
            x = round((50 + col * 200) * coordinate_scale)
            y = round((50 + row * 120) * coordinate_scale)

        # Get image URL for asset type
        image_url = type_images.get(
            asset.type,
            "https://uxwing.com/wp-content/themes/uxwing/download/communication-chat-call/question-mark-icon.png",
        )

        # Define colors for each asset type (matching the design)
        type_colors = {
            "Hardware": "#4CAF50",  # Green
            "Application": "#2196F3",  # Blue
            "Network": "#9C27B0",  # Purple
            "ConnectionRule": "#FF9800",  # Orange
            "Identity": "#607D8B",  # Blue Grey
            "Credentials": "#4CAF50",  # Green
            "SoftwareVulnerability": "#F44336",  # Red
            "Data": "#795548",  # Brown
            "User": "#00BCD4",  # Cyan
        }

        # Get color for this asset type
        top_color = type_colors.get(asset.type, "#4CAF50")

        # Create the HTML content for the two-segment box
        html_content = f"""
        <div style="width: {box_width}px; height: {box_height}px; position: relative; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <!-- Top segment with icon and type -->
            <div style="background: linear-gradient(to bottom, {top_color}, {top_color}dd); height: 40%; display: flex; align-items: center; padding: 0 8px; position: relative;">
                <img src="{image_url}" width="20" height="20" style="margin-right: 8px;"/>
                <span style="color: white; font-weight: bold; font-size: 11px; flex: 1;">{asset.type}</span>
                <div style="width: 8px; height: 8px; background: {top_color}; position: absolute; top: 4px; right: 4px; border-radius: 2px;"></div>
            </div>
            <!-- Bottom segment with asset name -->
            <div style="background: #424242; height: 60%; display: flex; align-items: center; justify-content: center; padding: 0 8px;">
                <span style="color: white; font-size: 10px; text-align: center; line-height: 1.2;">{asset.name}</span>
            </div>
            <!-- Connecting line -->
            <div style="position: absolute; bottom: 40%; left: 0; width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-top: 8px solid {top_color};"></div>
        </div>
        """

        # Create mxCell for the asset box
        cell = ET.SubElement(root_cell, "mxCell")
        cell.set("id", f"asset_{asset.id}")
        cell.set("value", html_content)
        cell.set(
            "style",
            "rounded=0;whiteSpace=wrap;html=1;overflow=fill;"
            "align=center;verticalAlign=middle;spacing=0;"
            "fillColor=none;strokeColor=none;fontSize=10;fontStyle=1;",
        )
        cell.set("vertex", "1")
        cell.set("parent", "2")  # Put assets in front layer

        # Create geometry element
        geometry = ET.SubElement(cell, "mxGeometry")
        geometry.set("x", str(x))
        geometry.set("y", str(y))
        geometry.set("width", str(box_width))
        geometry.set("height", str(box_height))
        geometry.set("as", "geometry")

    # Create edges for associations (avoiding duplicates)
    edge_id = 1000  # Start edge IDs from 1000 to avoid conflicts with asset IDs
    processed_edges = set()  # Track processed edges to avoid duplicates

    for asset in assets:
        if hasattr(asset, "associated_assets") and asset.associated_assets:
            for asset_assoc_field, associated_assets in asset.associated_assets.items():
                association_type = asset.lg_asset.associations[asset_assoc_field].name
                for assoc_asset in associated_assets:
                    # Create a unique edge identifier (sorted to handle bidirectional associations)
                    edge_key = tuple(sorted([asset.id, assoc_asset.id]))

                    # Skip if we've already processed this edge
                    if edge_key in processed_edges:
                        continue

                    # Find the target asset
                    target_asset = None
                    for a in assets:
                        if a.id == assoc_asset.id:
                            target_asset = a
                            break

                    if target_asset:
                        # Mark this edge as processed
                        processed_edges.add(edge_key)
                        # Get positions for both assets
                        source_x = asset.extras.get("position", {}).get("x", 0) + box_width / 2
                        source_y = asset.extras.get("position", {}).get("y", 0) + box_height / 2
                        target_x = (
                            target_asset.extras.get("position", {}).get("x", 0) + box_width / 2
                        )
                        target_y = (
                            target_asset.extras.get("position", {}).get("y", 0) + box_height / 2
                        )

                        # Create edge cell
                        edge_cell = ET.SubElement(root_cell, "mxCell")
                        edge_cell.set("id", f"edge_{edge_id}")
                        edge_cell.set(
                            "value", association_type if show_edge_labels else ""
                        )
                        edge_cell.set(
                            "style",
                            f"edgeStyle=straightEdgeStyle;rounded=0;html=1;fontSize=10;fontStyle=1;endArrow=none;startArrow=none;strokeWidth={line_thickness};",
                        )
                        edge_cell.set("edge", "1")
                        edge_cell.set("parent", "1")  # Put edges in back layer
                        edge_cell.set("source", f"asset_{asset.id}")
                        edge_cell.set("target", f"asset_{assoc_asset.id}")

                        # Create geometry for edge
                        edge_geometry = ET.SubElement(edge_cell, "mxGeometry")
                        edge_geometry.set("relative", "1")
                        edge_geometry.set("as", "geometry")

                        # Create array of points for the edge
                        array = ET.SubElement(edge_geometry, "Array")
                        array.set("as", "points")

                        # Add source point
                        point1 = ET.SubElement(array, "mxPoint")
                        point1.set("x", str(source_x))
                        point1.set("y", str(source_y))
                        point1.set("as", "sourcePoint")

                        # Add target point
                        point2 = ET.SubElement(array, "mxPoint")
                        point2.set("x", str(target_x))
                        point2.set("y", str(target_y))
                        point2.set("as", "targetPoint")

                        edge_id += 1

    # Convert to pretty XML
    rough_string = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # Remove empty lines
    lines = [line for line in pretty_xml.split("\n") if line.strip()]
    pretty_xml = "\n".join(lines)

    # Write to file
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"Draw.io file with images created: {output_filename}")
    print(f"Total assets: {len(assets)}")
    print(f"Diagram bounds: x={min_x:.0f} to {max_x:.0f}, y={min_y:.0f} to {max_y:.0f}")

    # Print asset summary
    type_counts: dict[str, int] = {}
    for asset in assets:
        type_counts[asset.type] = type_counts.get(asset.type, 0) + 1

    print("\nAsset type distribution:")
    for asset_type, count in sorted(type_counts.items()):
        print(f"  {asset_type}: {count}")
