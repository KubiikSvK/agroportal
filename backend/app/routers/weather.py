from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import WeatherLog
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/weather", tags=["weather"])

class WeatherCreate(BaseModel):
    save_id: str
    season: Optional[str] = None
    condition: Optional[str] = None
    game_day: Optional[int] = None
    start_day: Optional[int] = None

class WeatherResponse(WeatherCreate):
    id: str

    class Config:
        from_attributes = True

@router.get("/", response_model=list[WeatherResponse])
def list_weather(save_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(WeatherLog)
    if save_id:
        query = query.filter(WeatherLog.save_id == save_id)
    return query.order_by(WeatherLog.start_day.desc()).all()

@router.post("/", response_model=WeatherResponse)
def create_weather(entry: WeatherCreate, db: Session = Depends(get_db)):
    db_entry = WeatherLog(**entry.model_dump())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry
