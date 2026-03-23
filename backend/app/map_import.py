import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _as_geojson_polygon(points: list[dict[str, Any]]) -> dict:
    coords = [[point.get("x"), point.get("y") or point.get("z")] for point in points]
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return {"type": "Polygon", "coordinates": [coords]}


def parse_field_geometry_payload(payload: Any, scale: float = 1.0, offset_x: float = 0.0, offset_y: float = 0.0) -> list[dict]:
    results = []
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        for feature in payload.get("features", []):
            field_id = feature.get("properties", {}).get("fieldId") or feature.get("id")
            geometry = feature.get("geometry")
            if geometry:
                results.append({"field_id": str(field_id), "geometry": _apply_transform(geometry, scale, offset_x, offset_y)})
        return results

    if isinstance(payload, list):
        for item in payload:
            field_id = item.get("fieldId") or item.get("id")
            points = item.get("points") or item.get("corners")
            if field_id is None or not points:
                continue
            geometry = _as_geojson_polygon(points)
            results.append({"field_id": str(field_id), "geometry": _apply_transform(geometry, scale, offset_x, offset_y)})
        return results

    return results


def _apply_transform(geometry: dict, scale: float, offset_x: float, offset_y: float) -> dict:
    def transform_pair(pair: list[float]) -> list[float]:
        return [pair[0] * scale + offset_x, pair[1] * scale + offset_y]

    if geometry.get("type") == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": [[transform_pair(p) for p in ring] for ring in geometry.get("coordinates", [])],
        }
    if geometry.get("type") == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [[transform_pair(p) for p in ring] for ring in poly] for poly in geometry.get("coordinates", [])
            ],
        }
    return geometry


def load_json_from_bytes(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"))


def _parse_translation(node: ET.Element | None) -> tuple[float, float, float]:
    if node is None:
        return 0.0, 0.0, 0.0
    translation = node.get("translation")
    if not translation:
        return 0.0, 0.0, 0.0
    parts = translation.split()
    if len(parts) < 3:
        return 0.0, 0.0, 0.0
    return float(parts[0]), float(parts[1]), float(parts[2])


def parse_i3d_polygons(i3d_path: Path) -> tuple[list[dict], dict]:
    tree = ET.parse(i3d_path)
    root = tree.getroot()
    fields_node = None
    for tg in root.iter("TransformGroup"):
        if tg.get("name") == "fields":
            fields_node = tg
            break
    if fields_node is None:
        return [], {}

    items = []
    bounds = {"min_x": None, "min_y": None, "max_x": None, "max_y": None}

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
        field_tx, field_ty, field_tz = _parse_translation(field_tg)
        poly_tx, poly_ty, poly_tz = _parse_translation(poly)
        points = []
        for point in poly.findall("./TransformGroup"):
            point_tx, point_ty, point_tz = _parse_translation(point)
            x = field_tx + poly_tx + point_tx
            z = field_tz + poly_tz + point_tz
            points.append({"x": x, "y": z})
            bounds["min_x"] = x if bounds["min_x"] is None else min(bounds["min_x"], x)
            bounds["min_y"] = z if bounds["min_y"] is None else min(bounds["min_y"], z)
            bounds["max_x"] = x if bounds["max_x"] is None else max(bounds["max_x"], x)
            bounds["max_y"] = z if bounds["max_y"] is None else max(bounds["max_y"], z)
        if points:
            items.append({"field_id": field_id, "points": points})

    return items, bounds
