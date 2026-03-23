from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import FieldSnapshot
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/snapshots", tags=["snapshots"])

class SnapshotCreate(BaseModel):
    field_id: str
    save_id: str
    crop_type: Optional[str] = None
    growth_state: Optional[int] = None
    ground_type: Optional[str] = None
    weed_state: Optional[int] = None
    spray_level: Optional[int] = None
    lime_level: Optional[int] = None

class SnapshotResponse(SnapshotCreate):
    id: str
    recorded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=list[SnapshotResponse])
def list_snapshots(field_id: Optional[str] = None, save_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(FieldSnapshot)
    if field_id:
        query = query.filter(FieldSnapshot.field_id == field_id)
    if save_id:
        query = query.filter(FieldSnapshot.save_id == save_id)
    return query.order_by(FieldSnapshot.recorded_at.desc()).all()

@router.post("/", response_model=SnapshotResponse)
def create_snapshot(snapshot: SnapshotCreate, db: Session = Depends(get_db)):
    db_snapshot = FieldSnapshot(**snapshot.model_dump())
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot
