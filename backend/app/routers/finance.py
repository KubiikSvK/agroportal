from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import FinanceSnapshot
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/finance", tags=["finance"])

class FinanceCreate(BaseModel):
    save_id: str
    game_day: Optional[int] = None
    balance: Optional[float] = None
    loan: Optional[float] = None
    harvest_income: Optional[float] = None
    mission_income: Optional[float] = None
    new_vehicles_cost: Optional[float] = None
    construction_cost: Optional[float] = None
    field_purchase: Optional[float] = None
    purchase_seeds: Optional[float] = None
    purchase_fertilizer: Optional[float] = None
    purchase_fuel: Optional[float] = None
    vehicle_running_cost: Optional[float] = None
    loan_interest: Optional[float] = None
    other: Optional[float] = None

class FinanceResponse(FinanceCreate):
    id: str

    class Config:
        from_attributes = True

@router.get("/", response_model=list[FinanceResponse])
def list_finance(save_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(FinanceSnapshot)
    if save_id:
        query = query.filter(FinanceSnapshot.save_id == save_id)
    return query.order_by(FinanceSnapshot.recorded_at.desc()).all()

@router.post("/", response_model=FinanceResponse)
def create_finance(snapshot: FinanceCreate, db: Session = Depends(get_db)):
    db_snapshot = FinanceSnapshot(**snapshot.model_dump())
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot
