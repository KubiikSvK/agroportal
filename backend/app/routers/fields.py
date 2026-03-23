from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Field
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/fields", tags=["fields"])

class FieldCreate(BaseModel):
    fs_field_id: int
    fs_farmland_id: Optional[int] = None
    name: str
    area_ha: Optional[float] = None
    owned: Optional[bool] = False

class FieldUpdate(BaseModel):
    fs_field_id: Optional[int] = None
    fs_farmland_id: Optional[int] = None
    name: Optional[str] = None
    area_ha: Optional[float] = None
    owned: Optional[bool] = None

class FieldResponse(BaseModel):
    id: str
    fs_field_id: int
    fs_farmland_id: Optional[int]
    name: str
    area_ha: Optional[float]
    owned: bool

    class Config:
        from_attributes = True

@router.get("/", response_model=list[FieldResponse])
def get_fields(db: Session = Depends(get_db)):
    return db.query(Field).all()

@router.get("/{field_id}", response_model=FieldResponse)
def get_field(field_id: str, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Pole nenalezeno")
    return field

@router.post("/", response_model=FieldResponse)
def create_field(field: FieldCreate, db: Session = Depends(get_db)):
    db_field = Field(**field.model_dump())
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field

@router.patch("/{field_id}", response_model=FieldResponse)
def update_field(field_id: str, field: FieldUpdate, db: Session = Depends(get_db)):
    db_field = db.query(Field).filter(Field.id == field_id).first()
    if not db_field:
        raise HTTPException(status_code=404, detail="Pole nenalezeno")
    for key, value in field.model_dump(exclude_unset=True).items():
        setattr(db_field, key, value)
    db.commit()
    db.refresh(db_field)
    return db_field
