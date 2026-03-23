import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def parse_map_size(map_xml: Path) -> tuple[int | None, int | None]:
    if not map_xml.exists():
        return None, None
    root = ET.parse(map_xml).getroot()
    width = root.get("width")
    height = root.get("height")
    return (int(width) if width else None, int(height) if height else None)


def parse_i3d_fields(i3d_path: Path):
    tree = ET.parse(i3d_path)
    root = tree.getroot()

    fields_node = None
    for tg in root.iter("TransformGroup"):
        if tg.get("name") == "fields":
            fields_node = tg
            break
    if fields_node is None:
        return []

    features = []
    for field_tg in fields_node.findall("./TransformGroup"):
        name = field_tg.get("name") or ""
        if not name.startswith("field"):
            continue
        try:
            field_id = int(name.replace("field", ""))
        except ValueError:
            continue

        poly = field_tg.find("./TransformGroup[@name='polygonPoints']")
        if poly is None:
            continue
        coords = []
        for point in poly.findall("./TransformGroup"):
            translation = point.get("translation")
            if not translation:
                continue
            parts = translation.split()
            if len(parts) < 3:
                continue
            x = float(parts[0])
            z = float(parts[2])
            coords.append([x, z])

        if len(coords) < 3:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        features.append({
            "type": "Feature",
            "properties": {"fieldId": field_id},
            "geometry": {"type": "Polygon", "coordinates": [coords]},
        })

    return features


def main():
    parser = argparse.ArgumentParser(description="Extract field polygons from FS i3d map.")
    parser.add_argument("--i3d", required=True, help="Path to map i3d file")
    parser.add_argument("--map-xml", help="Path to map XML for width/height metadata")
    parser.add_argument("--out", required=True, help="Output GeoJSON file")
    args = parser.parse_args()

    i3d_path = Path(args.i3d)
    if not i3d_path.exists():
        raise SystemExit(f"i3d file not found: {i3d_path}")

    features = parse_i3d_fields(i3d_path)
    width, height = (None, None)
    if args.map_xml:
        width, height = parse_map_size(Path(args.map_xml))

    data = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "mapWidth": width,
            "mapHeight": height,
            "source": str(i3d_path),
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(features)} field polygons to {out_path}")


if __name__ == "__main__":
    main()
