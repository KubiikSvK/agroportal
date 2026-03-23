import json
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Field, FieldGeometry, MapAsset, Save
from app.map_import import load_json_from_bytes, parse_field_geometry_payload, parse_i3d_polygons

router = APIRouter(prefix="/maps", tags=["maps"])

MAP_DIR = Path("storage") / "maps"
MAP_DIR.mkdir(parents=True, exist_ok=True)

class MapFromUrl(BaseModel):
    url: str
    map_id: str | None = None

class GeometryUpsert(BaseModel):
    field_id: str
    geometry_geojson: dict

@router.post("/pdf/upload")
async def upload_map_pdf(file: UploadFile = File(...), map_id: str | None = None, db: Session = Depends(get_db)):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = MAP_DIR / f"map_{timestamp}.pdf"
    with target.open("wb") as f:
        f.write(await file.read())

    asset = MapAsset(map_id=map_id, source_url=None, file_path=str(target), asset_type="pdf", status="stored")
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"status": "ok", "map_asset_id": asset.id}

@router.post("/pdf/from-url")
async def download_map_pdf(payload: MapFromUrl, db: Session = Depends(get_db)):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = MAP_DIR / f"map_{timestamp}.pdf"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(payload.url)
            resp.raise_for_status()
        target.write_bytes(resp.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {exc}")

    asset = MapAsset(map_id=payload.map_id, source_url=payload.url, file_path=str(target), asset_type="pdf", status="stored")
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"status": "ok", "map_asset_id": asset.id}


@router.post("/image/upload")
async def upload_map_image(file: UploadFile = File(...), map_id: str | None = None, db: Session = Depends(get_db)):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = MAP_DIR / f"map_{timestamp}.png"
    with target.open("wb") as f:
        f.write(await file.read())

    asset = MapAsset(map_id=map_id, source_url=None, file_path=str(target), asset_type="image", status="stored")
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"status": "ok", "map_asset_id": asset.id}

@router.post("/geometry")
def upsert_geometry(item: GeometryUpsert, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == item.field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    existing = db.query(FieldGeometry).filter(FieldGeometry.field_id == item.field_id).first()
    if existing:
        existing.geometry_geojson = json.dumps(item.geometry_geojson)
        db.commit()
        return {"status": "updated", "field_id": item.field_id}

    db.add(FieldGeometry(field_id=item.field_id, geometry_geojson=json.dumps(item.geometry_geojson)))
    db.commit()
    return {"status": "created", "field_id": item.field_id}

@router.get("/geometry")
def list_geometry(
    scale: float = 1.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    invert_y: bool = False,
    db: Session = Depends(get_db),
):
    rows = db.query(FieldGeometry).all()
    results = []
    for row in rows:
        geometry = json.loads(row.geometry_geojson)
        if scale != 1.0 or offset_x != 0.0 or offset_y != 0.0 or invert_y:
            geometry = _transform_geometry(geometry, scale, offset_x, offset_y, invert_y)
        results.append({"field_id": row.field_id, "geometry_geojson": geometry})
    return results

@router.post("/extract")
def extract_from_pdf():
    raise HTTPException(
        status_code=501,
        detail="PDF extraction not implemented yet. Upload geometry via /maps/geometry.",
    )


@router.post("/import-geometry")
async def import_geometry(
    file: UploadFile = File(...),
    scale: float = 1.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    db: Session = Depends(get_db),
):
    data = await file.read()
    payload = load_json_from_bytes(data)
    items = parse_field_geometry_payload(payload, scale=scale, offset_x=offset_x, offset_y=offset_y)
    if not items:
        raise HTTPException(status_code=400, detail="No geometry found in payload")

    created = 0
    for item in items:
        field = db.query(Field).filter(Field.fs_field_id == int(item["field_id"])).first()
        if not field:
            continue
        existing = db.query(FieldGeometry).filter(FieldGeometry.field_id == field.id).first()
        payload_json = json.dumps(item["geometry"])
        if existing:
            existing.geometry_geojson = payload_json
        else:
            db.add(FieldGeometry(field_id=field.id, geometry_geojson=payload_json))
        created += 1
    db.commit()
    return {"status": "ok", "updated": created}


@router.post("/import-i3d")
async def import_i3d(
    file: UploadFile = File(...),
    scale: float = 1.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    invert_y: bool = False,
    db: Session = Depends(get_db),
):
    data = await file.read()
    tmp_path = MAP_DIR / "temp_map.i3d"
    tmp_path.write_bytes(data)
    items, bounds = parse_i3d_polygons(tmp_path)
    tmp_path.unlink(missing_ok=True)

    if not items:
        raise HTTPException(status_code=400, detail="No field polygons found in i3d")

    created = 0
    for item in items:
        field = db.query(Field).filter(Field.fs_field_id == int(item["field_id"])).first()
        if not field:
            field = Field(fs_field_id=int(item["field_id"]), name=f"Field {item['field_id']}")
            db.add(field)
            db.commit()
            db.refresh(field)
        existing = db.query(FieldGeometry).filter(FieldGeometry.field_id == field.id).first()
        coords = []
        for p in item["points"]:
            y_val = -p["y"] if invert_y else p["y"]
            coords.append([p["x"] * scale + offset_x, y_val * scale + offset_y])
        geometry = {"type": "Polygon", "coordinates": [coords]}
        if geometry["coordinates"][0] and geometry["coordinates"][0][0] != geometry["coordinates"][0][-1]:
            geometry["coordinates"][0].append(geometry["coordinates"][0][0])
        payload_json = json.dumps(geometry)
        if existing:
            existing.geometry_geojson = payload_json
        else:
            db.add(FieldGeometry(field_id=field.id, geometry_geojson=payload_json))
        created += 1
    db.commit()
    return {"status": "ok", "updated": created, "bounds": bounds}


@router.get("/assets")
def list_assets(db: Session = Depends(get_db)):
    rows = db.query(MapAsset).order_by(MapAsset.created_at.desc()).all()
    return [
        {
            "id": row.id,
            "map_id": row.map_id,
            "asset_type": row.asset_type,
            "file_path": row.file_path,
            "source_url": row.source_url,
            "status": row.status,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/active-image")
def active_image(map_id: str | None = None, db: Session = Depends(get_db)):
    target_map_id = map_id
    if target_map_id is None:
        latest = db.query(Save).order_by(Save.pushed_at.desc()).first()
        if latest and latest.map_id:
            target_map_id = latest.map_id

    query = db.query(MapAsset).filter(MapAsset.asset_type == "image")
    image = None
    if target_map_id:
        image = query.filter(MapAsset.map_id == target_map_id).order_by(MapAsset.created_at.desc()).first()
        if image is None:
            candidates = query.order_by(MapAsset.created_at.desc()).all()
            for cand in candidates:
                if cand.map_id and (cand.map_id in target_map_id or target_map_id in cand.map_id):
                    image = cand
                    break
    def is_valid(img: MapAsset) -> bool:
        try:
            path = Path(img.file_path)
            if not path.exists():
                return False
            if path.stat().st_size < 50_000:
                return False
        except Exception:
            return False
        return True

    if image is None:
        image = query.order_by(MapAsset.created_at.desc()).first()
    if image and not is_valid(image):
        candidates = query.order_by(MapAsset.created_at.desc()).all()
        image = None
        for cand in candidates:
            if is_valid(cand):
                image = cand
                break
    if not image:
        raise HTTPException(status_code=404, detail="No image asset found")
    map_width = None
    map_height = None
    try:
        config_query = db.query(MapAsset).filter(MapAsset.asset_type == "config")
        config_asset = None
        if target_map_id:
            config_asset = config_query.filter(MapAsset.map_id == target_map_id).order_by(MapAsset.created_at.desc()).first()
            if config_asset is None:
                candidates = config_query.order_by(MapAsset.created_at.desc()).all()
                for cand in candidates:
                    if cand.map_id and (cand.map_id in target_map_id or target_map_id in cand.map_id):
                        config_asset = cand
                        break
        if config_asset is None:
            config_asset = config_query.order_by(MapAsset.created_at.desc()).first()
        if config_asset:
            config_path = Path(config_asset.file_path)
            if config_path.exists():
                tree = ET.parse(config_path)
                root = tree.getroot()
                map_width = root.get("width")
                map_height = root.get("height")
                if map_width is not None:
                    map_width = int(float(map_width))
                if map_height is not None:
                    map_height = int(float(map_height))
    except Exception:
        map_width = None
        map_height = None
    try:
        rel_path = Path(image.file_path).relative_to("storage").as_posix()
        url = f"/storage/{rel_path}"
    except ValueError:
        url = image.file_path
    return {
        "id": image.id,
        "map_id": image.map_id,
        "file_path": image.file_path,
        "url": url,
        "map_width": map_width,
        "map_height": map_height,
    }


def _transform_geometry(geometry: dict, scale: float, offset_x: float, offset_y: float, invert_y: bool) -> dict:
    def transform_pair(pair: list[float]) -> list[float]:
        y_val = -pair[1] if invert_y else pair[1]
        return [pair[0] * scale + offset_x, y_val * scale + offset_y]

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
