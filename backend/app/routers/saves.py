from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Save
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/saves", tags=["saves"])

class SaveCreate(BaseModel):
    game_day: int
    game_year: int
    season: Optional[str] = None
    time_scale: Optional[float] = None
    balance: Optional[float] = None
    loan: Optional[float] = None
    map_id: Optional[str] = None
    map_title: Optional[str] = None
    uploaded_by: Optional[str] = None

class SaveResponse(SaveCreate):
    id: str

    class Config:
        from_attributes = True

@router.get("/", response_model=list[SaveResponse])
def list_saves(db: Session = Depends(get_db)):
    return db.query(Save).order_by(Save.pushed_at.desc()).all()

@router.post("/", response_model=SaveResponse)
def create_save(save: SaveCreate, db: Session = Depends(get_db)):
    db_save = Save(**save.model_dump())
    db.add(db_save)
    db.commit()
    db.refresh(db_save)
    return db_save
