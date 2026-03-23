import json
import shutil
import tempfile
import zipfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.database import SessionLocal
from app.models.models import (
    Save,
    Field,
    FieldSnapshot,
    FinanceSnapshot,
    Vehicle,
    Harvest,
    WeatherLog,
    SyncHistory,
    FieldGeometry,
    MapAsset,
)
from app.parser import parse_save_folder
from app.map_import import parse_i3d_polygons
from app.map_zip import extract_map_zip

router = APIRouter(prefix="/sync", tags=["sync"])

BASE_STORAGE = Path("storage")
CURRENT_DIR = BASE_STORAGE / "current"
BACKUP_DIR = BASE_STORAGE / "backups"
ARCHIVE_DIR = BASE_STORAGE / "archive"
TMP_DIR = BASE_STORAGE / "tmp"

DEPLOY_JOBS: dict[str, dict] = {}


def _ensure_dirs():
    for d in [CURRENT_DIR, BACKUP_DIR, ARCHIVE_DIR, TMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _save_upload(upload: UploadFile, target: Path) -> None:
    with target.open("wb") as f:
        shutil.copyfileobj(upload.file, f)


def _rotate_backups(keep_last: int = 3) -> None:
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[keep_last:]:
        old.unlink(missing_ok=True)


def _backup_db(db: Session, target: Path) -> None:
    data = {
        "saves": [row.__dict__ for row in db.query(Save).all()],
        "fields": [row.__dict__ for row in db.query(Field).all()],
        "field_snapshots": [row.__dict__ for row in db.query(FieldSnapshot).all()],
        "finance_snapshots": [row.__dict__ for row in db.query(FinanceSnapshot).all()],
        "vehicles": [row.__dict__ for row in db.query(Vehicle).all()],
        "harvests": [row.__dict__ for row in db.query(Harvest).all()],
        "weather_logs": [row.__dict__ for row in db.query(WeatherLog).all()],
        "field_geometry": [row.__dict__ for row in db.query(FieldGeometry).all()],
    }
    # Strip SQLAlchemy state
    for key, rows in data.items():
        for row in rows:
            row.pop("_sa_instance_state", None)
    target.write_text(json.dumps(data, default=str), encoding="utf-8")


def _clear_db_for_replace(db: Session) -> None:
    db.query(FieldSnapshot).delete()
    db.query(Harvest).delete()
    db.query(FinanceSnapshot).delete()
    db.query(Vehicle).delete()
    db.query(WeatherLog).delete()
    db.query(FieldGeometry).delete()
    db.query(Save).delete()
    db.query(Field).delete()
    db.commit()


def _import_i3d_into_db(db: Session, i3d_path: Path, progress_cb=None) -> int:
    items, _ = parse_i3d_polygons(i3d_path)
    if not items:
        return 0
    updated = 0
    total = max(len(items), 1)
    for item in items:
        field = db.query(Field).filter(Field.fs_field_id == int(item["field_id"])).first()
        if field is None:
            field = Field(fs_field_id=int(item["field_id"]), name=f"Pole {item['field_id']}")
            db.add(field)
            db.commit()
            db.refresh(field)
        existing = db.query(FieldGeometry).filter(FieldGeometry.field_id == field.id).first()
        coords = [[p["x"], p["y"]] for p in item["points"]]
        geometry = {"type": "Polygon", "coordinates": [coords]}
        if geometry["coordinates"][0] and geometry["coordinates"][0][0] != geometry["coordinates"][0][-1]:
            geometry["coordinates"][0].append(geometry["coordinates"][0][0])
        payload_json = json.dumps(geometry)
        if existing:
            existing.geometry_geojson = payload_json
        else:
            db.add(FieldGeometry(field_id=field.id, geometry_geojson=payload_json))
        updated += 1
        if progress_cb:
            progress_cb(updated / total * 100)
    db.commit()
    return updated


def _ingest_save(db: Session, extract_dir: Path, uploaded_by: str | None, action: str, progress_cb=None) -> Save:
    parsed = parse_save_folder(extract_dir)
    meta = parsed["meta"]

    save = Save(
        game_day=meta.get("game_day") or 0,
        game_year=meta.get("game_year") or 0,
        season=meta.get("season"),
        time_scale=meta.get("time_scale"),
        balance=meta.get("balance"),
        loan=meta.get("loan"),
        map_id=meta.get("map_id"),
        map_title=meta.get("map_title"),
        uploaded_by=uploaded_by,
    )
    db.add(save)
    db.commit()
    db.refresh(save)

    owned_farmlands = parsed["owned_farmlands"]
    field_index = {}
    total_items = max(len(parsed["fields"]) + len(parsed["vehicles"]) + len(parsed["precision"]), 1)
    done_items = 0
    for row in parsed["fields"]:
        fs_field_id = row["fs_field_id"]
        field = db.query(Field).filter(Field.fs_field_id == fs_field_id).first()
        if field is None:
            field = Field(
                fs_field_id=fs_field_id,
                fs_farmland_id=row.get("fs_farmland_id"),
                name=f"Pole {fs_field_id}",
                owned=row.get("fs_farmland_id") in owned_farmlands if row.get("fs_farmland_id") else False,
            )
            db.add(field)
        else:
            field.fs_farmland_id = row.get("fs_farmland_id")
            if row.get("fs_farmland_id"):
                field.owned = row.get("fs_farmland_id") in owned_farmlands
            if field.name is None or field.name.lower().startswith("horní"):
                field.name = f"Pole {fs_field_id}"
        db.commit()
        db.refresh(field)
        field_index[(row.get("fs_farmland_id"), fs_field_id)] = field

        snapshot = FieldSnapshot(
            field_id=field.id,
            save_id=save.id,
            crop_type=row.get("crop_type"),
            growth_state=row.get("growth_state"),
            ground_type=row.get("ground_type"),
            weed_state=row.get("weed_state"),
            spray_level=row.get("spray_level"),
            lime_level=row.get("lime_level"),
        )
        db.add(snapshot)
        done_items += 1
        if progress_cb:
            progress_cb(done_items / total_items * 100)

    if parsed.get("finance"):
        finance = parsed["finance"]
        db.add(FinanceSnapshot(
            save_id=save.id,
            game_day=finance.get("day"),
            balance=meta.get("balance"),
            loan=meta.get("loan"),
            harvest_income=finance.get("harvest_income"),
            mission_income=finance.get("mission_income"),
            new_vehicles_cost=finance.get("new_vehicles_cost"),
            construction_cost=finance.get("construction_cost"),
            field_purchase=finance.get("field_purchase"),
            purchase_seeds=finance.get("purchase_seeds"),
            purchase_fertilizer=finance.get("purchase_fertilizer"),
            purchase_fuel=finance.get("purchase_fuel"),
            vehicle_running_cost=finance.get("vehicle_running_cost"),
            loan_interest=finance.get("loan_interest"),
            other=finance.get("other"),
        ))

    for row in parsed["vehicles"]:
        db.add(Vehicle(
            save_id=save.id,
            name=row.get("name"),
            vehicle_type=row.get("vehicle_type"),
            brand=row.get("brand"),
            purchase_price=row.get("purchase_price"),
            age_days=row.get("age_days"),
            damage=row.get("damage"),
            wear=row.get("wear"),
            operating_time=row.get("operating_time"),
            is_leased=row.get("is_leased", False),
        ))
        done_items += 1
        if progress_cb:
            progress_cb(done_items / total_items * 100)

    for row in parsed["precision"]:
        farmland_id = row.get("farmland_id")
        field = None
        for key, value in field_index.items():
            if key[0] == farmland_id:
                field = value
                break
        if field:
            db.add(Harvest(
                field_id=field.id,
                save_id=save.id,
                crop_type=None,
                amount_kg=row.get("yield"),
                yield_per_ha=None,
                best_price=row.get("yield_best_price"),
                game_day=meta.get("game_day"),
                game_year=meta.get("game_year"),
                source="precision",
            ))
        done_items += 1
        if progress_cb:
            progress_cb(done_items / total_items * 100)

    db.add(SyncHistory(
        action=action,
        uploaded_by=uploaded_by,
        game_day=meta.get("game_day"),
        game_year=meta.get("game_year"),
        balance=meta.get("balance"),
        status="ok",
    ))

    db.commit()
    return save


@router.post("/push")
async def push_save(file: UploadFile = File(...), uploaded_by: str | None = None, db: Session = Depends(get_db)):
    _ensure_dirs()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    incoming = TMP_DIR / f"incoming_{timestamp}.zip"
    _save_upload(file, incoming)

    current_zip = CURRENT_DIR / "savegame.zip"
    shutil.copyfile(incoming, current_zip)
    backup_zip = BACKUP_DIR / f"save_{timestamp}.zip"
    shutil.copyfile(incoming, backup_zip)
    _rotate_backups(keep_last=3)

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tmpdir:
        with zipfile.ZipFile(incoming) as zf:
            zf.extractall(tmpdir)
        save = _ingest_save(db, Path(tmpdir), uploaded_by, action="push")

    incoming.unlink(missing_ok=True)
    return {"status": "ok", "save_id": save.id}


@router.post("/replace")
async def replace_save(file: UploadFile = File(...), uploaded_by: str | None = None, db: Session = Depends(get_db)):
    _ensure_dirs()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    current_zip = CURRENT_DIR / "savegame.zip"
    if current_zip.exists():
        archive_zip = ARCHIVE_DIR / f"save_{timestamp}_replaced.zip"
        shutil.copyfile(current_zip, archive_zip)

    backup_json = ARCHIVE_DIR / f"data_{timestamp}_backup.json"
    _backup_db(db, backup_json)
    _clear_db_for_replace(db)

    incoming = TMP_DIR / f"incoming_{timestamp}.zip"
    _save_upload(file, incoming)
    shutil.copyfile(incoming, current_zip)
    backup_zip = BACKUP_DIR / f"save_{timestamp}.zip"
    shutil.copyfile(incoming, backup_zip)
    _rotate_backups(keep_last=3)

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tmpdir:
        with zipfile.ZipFile(incoming) as zf:
            zf.extractall(tmpdir)
        save = _ingest_save(db, Path(tmpdir), uploaded_by, action="replace")

    incoming.unlink(missing_ok=True)
    return {"status": "ok", "save_id": save.id, "replaced": True}


@router.get("/pull")
async def pull_save():
    current_zip = CURRENT_DIR / "savegame.zip"
    if not current_zip.exists():
        raise HTTPException(status_code=404, detail="No savegame available")
    return FileResponse(current_zip, filename="savegame.zip")


@router.post("/reingest")
async def reingest_save(uploaded_by: str | None = None, db: Session = Depends(get_db)):
    _ensure_dirs()
    current_zip = CURRENT_DIR / "savegame.zip"
    if not current_zip.exists():
        raise HTTPException(status_code=404, detail="No savegame available")

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tmpdir:
        with zipfile.ZipFile(current_zip) as zf:
            zf.extractall(tmpdir)
        save = _ingest_save(db, Path(tmpdir), uploaded_by, action="reingest")

    return {"status": "ok", "save_id": save.id, "reingested": True}


@router.post("/deploy")
async def deploy_bundle(
    background_tasks: BackgroundTasks,
    map_zip: UploadFile = File(...),
    save_zip: UploadFile = File(...),
    mode: str = Form("replace"),
    map_id: str | None = Form(None),
    import_i3d: bool = Form(True),
    uploaded_by: str | None = Form(None),
    db: Session = Depends(get_db),
):
    _ensure_dirs()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    mode = mode.lower().strip()
    if mode not in {"push", "replace"}:
        raise HTTPException(status_code=400, detail="Invalid mode")

    job_id = str(uuid.uuid4())
    job_dir = TMP_DIR / f"deploy_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)

    incoming_map = job_dir / f"map_{timestamp}.zip"
    incoming_save = job_dir / f"save_{timestamp}.zip"
    _save_upload(map_zip, incoming_map)
    _save_upload(save_zip, incoming_save)

    DEPLOY_JOBS[job_id] = {
        "status": "running",
        "step": "upload",
        "progress": 100,
        "message": "Upload dokončen",
        "error": None,
    }

    def run_deploy():
        session = SessionLocal()
        try:
            DEPLOY_JOBS[job_id].update({"step": "ingest", "progress": 0, "message": "Zpracování savegame…"})

            with tempfile.TemporaryDirectory(dir=job_dir) as map_tmp:
                map_result = extract_map_zip(incoming_map, Path(map_tmp), BASE_STORAGE / "maps", timestamp)

                if mode == "replace":
                    current_zip = CURRENT_DIR / "savegame.zip"
                    if current_zip.exists():
                        archive_zip = ARCHIVE_DIR / f"save_{timestamp}_replaced.zip"
                        shutil.copyfile(current_zip, archive_zip)
                    backup_json = ARCHIVE_DIR / f"data_{timestamp}_backup.json"
                    _backup_db(session, backup_json)
                    _clear_db_for_replace(session)

                current_zip = CURRENT_DIR / "savegame.zip"
                shutil.copyfile(incoming_save, current_zip)
                backup_zip = BACKUP_DIR / f"save_{timestamp}.zip"
                shutil.copyfile(incoming_save, backup_zip)
                _rotate_backups(keep_last=3)

                with tempfile.TemporaryDirectory(dir=job_dir) as save_tmp:
                    with zipfile.ZipFile(incoming_save) as zf:
                        zf.extractall(save_tmp)

                    def ingest_progress(value):
                        DEPLOY_JOBS[job_id].update({"step": "ingest", "progress": int(value), "message": "Zpracování savegame…"})

                    save = _ingest_save(session, Path(save_tmp), uploaded_by, action="deploy", progress_cb=ingest_progress)

                target_map_id = map_id or save.map_id or map_result.map_id
                if map_result.image_path:
                    asset = MapAsset(
                        map_id=target_map_id,
                        source_url=None,
                        file_path=str(map_result.image_path),
                        asset_type="image",
                        status="stored",
                    )
                    session.add(asset)
                    session.commit()
                if map_result.map_xml_copy:
                    asset = MapAsset(
                        map_id=target_map_id,
                        source_url=None,
                        file_path=str(map_result.map_xml_copy),
                        asset_type="config",
                        status="stored",
                    )
                    session.add(asset)
                    session.commit()
                if map_result.warning:
                    DEPLOY_JOBS[job_id].update({"warning": map_result.warning})

                DEPLOY_JOBS[job_id].update({"step": "import", "progress": 0, "message": "Import I3D…"})

                updated_fields = 0
                if import_i3d and map_result.i3d_path:
                    def import_progress(value):
                        DEPLOY_JOBS[job_id].update({"step": "import", "progress": int(value), "message": "Import I3D…"})

                    updated_fields = _import_i3d_into_db(session, map_result.i3d_path, progress_cb=import_progress)

            DEPLOY_JOBS[job_id].update({
                "status": "done",
                "step": "done",
                "progress": 100,
                "message": "Hotovo",
                "result": {
                    "save_id": save.id,
                    "map_id": target_map_id,
                    "image_stored": bool(map_result.image_path),
                    "i3d_imported": import_i3d and map_result.i3d_path is not None,
                    "fields_updated": updated_fields,
                    "warning": map_result.warning,
                },
            })
        except Exception as exc:
            DEPLOY_JOBS[job_id].update({"status": "error", "error": str(exc), "message": "Deploy selhal"})
        finally:
            session.close()
            shutil.rmtree(job_dir, ignore_errors=True)

    if background_tasks is not None:
        background_tasks.add_task(run_deploy)
    else:
        run_deploy()

    return {"status": "accepted", "job_id": job_id}


@router.get("/deploy-status/{job_id}")
def deploy_status(job_id: str):
    job = DEPLOY_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job


@router.get("/status")
def sync_status(db: Session = Depends(get_db)):
    latest = db.query(Save).order_by(Save.pushed_at.desc()).first()
    if not latest:
        return {"status": "empty"}
    return {
        "status": "ok",
        "save_id": latest.id,
        "game_day": latest.game_day,
        "game_year": latest.game_year,
        "season": latest.season,
        "balance": latest.balance,
        "loan": latest.loan,
        "map_id": latest.map_id,
        "map_title": latest.map_title,
        "pushed_at": latest.pushed_at,
    }
