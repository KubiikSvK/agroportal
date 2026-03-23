from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crop_rotation_engine import get_crop_rotation_engine
from app.database import get_db
from app.models.models import Crop, Field, FieldSnapshot

router = APIRouter(prefix="/rotation", tags=["rotation"])


def _build_history(snapshots: list[FieldSnapshot], max_len: int) -> list[str]:
    history: list[str] = []
    last = None
    for snap in snapshots:
        if not snap.crop_type:
            continue
        if last == snap.crop_type:
            continue
        history.append(snap.crop_type)
        last = snap.crop_type
        if len(history) >= max_len:
            break
    return history


@router.get("/config")
def rotation_config():
    engine = get_crop_rotation_engine()
    return {
        "settings": {
            "monoculturePenalty": engine.settings.monoculture_penalty,
            "breakPeriodsPenalty": engine.settings.break_periods_penalty,
            "foreCropsPenalties": engine.settings.fore_crops_penalties,
            "foreCropsVeryGoodBonuses": engine.settings.fore_crops_very_good_bonuses,
            "foreCropsGoodBonuses": engine.settings.fore_crops_good_bonuses,
            "fallowStateBonus": engine.settings.fallow_state_bonus,
            "veryGoodCatchCropBonus": engine.settings.very_good_catch_crop_bonus,
            "goodCatchCropBonus": engine.settings.good_catch_crop_bonus,
            "badCatchCropPenalty": engine.settings.bad_catch_crop_penalty,
        },
        "numHistory": engine.num_history_maps,
        "crops": [
            {
                "code": crop.code,
                "breakPeriods": crop.break_periods,
                "veryGood": crop.very_good,
                "good": crop.good,
                "bad": crop.bad,
                "ignoreInPlanner": crop.ignore_in_planner,
                "ignoreFallow": crop.ignore_fallow,
            }
            for crop in engine.crops.values()
        ],
    }


@router.get("/history")
def rotation_history(
    field_id: str | None = None,
    db: Session = Depends(get_db),
):
    engine = get_crop_rotation_engine()
    query = db.query(Field)
    if field_id:
        query = query.filter(Field.id == field_id)
    fields = query.all()
    results = []
    for field in fields:
        snaps = (
            db.query(FieldSnapshot)
            .filter(FieldSnapshot.field_id == field.id)
            .order_by(FieldSnapshot.recorded_at.desc())
            .all()
        )
        history = _build_history(snaps, engine.num_history_maps)
        results.append(
            {
                "field_id": field.id,
                "fs_field_id": field.fs_field_id,
                "name": field.name,
                "history": history,
            }
        )
    return results


@router.get("/recommendations")
def rotation_recommendations(
    field_id: str | None = None,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    engine = get_crop_rotation_engine()
    crop_name_map = {crop.code: crop.name for crop in db.query(Crop).all()}

    query = db.query(Field)
    if field_id:
        query = query.filter(Field.id == field_id)
    fields = query.all()

    results = []
    for field in fields:
        snaps = (
            db.query(FieldSnapshot)
            .filter(FieldSnapshot.field_id == field.id)
            .order_by(FieldSnapshot.recorded_at.desc())
            .all()
        )
        history = _build_history(snaps, engine.num_history_maps)
        current_crop = history[0] if history else None

        candidates = [
            crop
            for crop in engine.crops.values()
            if not crop.ignore_in_planner
        ]

        ranked = []
        for crop in candidates:
            mult, detail = engine.calculate_multiplier(history, crop.code)
            ranked.append(
                {
                    "code": crop.code,
                    "name": crop_name_map.get(crop.code, crop.code),
                    "multiplier": round(mult, 3),
                    "detail": detail,
                }
            )

        ranked.sort(key=lambda x: x["multiplier"], reverse=True)
        results.append(
            {
                "field_id": field.id,
                "fs_field_id": field.fs_field_id,
                "name": field.name,
                "current_crop": current_crop,
                "history": history,
                "recommendations": ranked[:limit],
            }
        )

    return results


@router.get("/plan")
def rotation_plan(
    years: int = Query(default=3, ge=1, le=6),
    field_id: str | None = None,
    db: Session = Depends(get_db),
):
    engine = get_crop_rotation_engine()
    crop_name_map = {crop.code: crop.name for crop in db.query(Crop).all()}

    query = db.query(Field)
    if field_id:
        query = query.filter(Field.id == field_id)
    fields = query.all()

    plans = []
    candidates = [crop for crop in engine.crops.values() if not crop.ignore_in_planner]

    for field in fields:
        snaps = (
            db.query(FieldSnapshot)
            .filter(FieldSnapshot.field_id == field.id)
            .order_by(FieldSnapshot.recorded_at.desc())
            .all()
        )
        history = _build_history(snaps, engine.num_history_maps)
        plan = []
        current_history = history[:]
        for step in range(1, years + 1):
            best = None
            for crop in candidates:
                mult, _detail = engine.calculate_multiplier(current_history, crop.code)
                if best is None or mult > best["multiplier"]:
                    best = {
                        "code": crop.code,
                        "name": crop_name_map.get(crop.code, crop.code),
                        "multiplier": round(mult, 3),
                    }
            if best is None:
                break
            plan.append({"year": step, **best})
            current_history = [best["code"], *current_history][: engine.num_history_maps]

        plans.append(
            {
                "field_id": field.id,
                "fs_field_id": field.fs_field_id,
                "name": field.name,
                "history": history,
                "plan": plan,
            }
        )
    return plans
