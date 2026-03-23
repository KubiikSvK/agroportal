from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Harvest
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/harvests", tags=["harvests"])

class HarvestCreate(BaseModel):
    field_id: str
    save_id: str
    crop_type: Optional[str] = None
    amount_kg: Optional[float] = None
    yield_per_ha: Optional[float] = None
    best_price: Optional[float] = None
    game_day: Optional[int] = None
    game_year: Optional[int] = None
    source: Optional[str] = "inferred"

class HarvestResponse(HarvestCreate):
    id: str

    class Config:
        from_attributes = True

@router.get("/", response_model=list[HarvestResponse])
def list_harvests(field_id: Optional[str] = None, year: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Harvest)
    if field_id:
        query = query.filter(Harvest.field_id == field_id)
    if year:
        query = query.filter(Harvest.game_year == year)
    return query.order_by(Harvest.game_year.desc(), Harvest.game_day.desc()).all()

@router.post("/", response_model=HarvestResponse)
def create_harvest(harvest: HarvestCreate, db: Session = Depends(get_db)):
    db_harvest = Harvest(**harvest.model_dump())
    db.add(db_harvest)
    db.commit()
    db.refresh(db_harvest)
    return db_harvest
