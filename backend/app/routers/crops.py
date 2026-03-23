from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Crop
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/crops", tags=["crops"])

class CropCreate(BaseModel):
    code: str
    name: str
    color: Optional[str] = None

class CropResponse(CropCreate):
    id: str

    class Config:
        from_attributes = True

@router.get("/", response_model=list[CropResponse])
def list_crops(db: Session = Depends(get_db)):
    return db.query(Crop).order_by(Crop.name.asc()).all()

@router.post("/", response_model=CropResponse)
def create_crop(crop: CropCreate, db: Session = Depends(get_db)):
    existing = db.query(Crop).filter(Crop.code == crop.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Crop already exists")
    db_crop = Crop(**crop.model_dump())
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    return db_crop
