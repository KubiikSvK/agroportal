from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from pathlib import Path
from app.models.models import Vehicle
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

class VehicleCreate(BaseModel):
    save_id: str
    name: Optional[str] = None
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    purchase_price: Optional[float] = None
    age_days: Optional[int] = None
    damage: Optional[float] = None
    wear: Optional[float] = None
    operating_time: Optional[float] = None
    is_leased: Optional[bool] = False
    property_state: Optional[str] = None

class VehicleResponse(VehicleCreate):
    id: str
    display_name: Optional[str] = None
    ownership: Optional[str] = None
    icon_url: Optional[str] = None

    class Config:
        from_attributes = True

def _resolve_display_name(name: Optional[str], brand: Optional[str]) -> str:
    if not name:
        return "Neznámý stroj"
    raw = name.replace("$moddir$", "").replace("\\", "/")
    lower = raw.lower()
    if "weight1000" in lower:
        return "Závaží 1000 kg"
    if "versa3kr" in lower:
        return "Horsch Versa 3 KR"
    if "bredal/k105" in lower:
        return "Bredal K105"
    if "newholland/t7" in lower:
        return "New Holland T7"
    if "valtra" in lower and "sseries" in lower:
        return "Valtra S Series"
    parts = raw.split("/")
    model_guess = Path(raw).stem.replace("_", " ")
    if "data" in parts and "vehicles" in parts:
        try:
            idx = parts.index("vehicles")
            brand_guess = parts[idx + 1].replace("_", " ").title()
            model_guess = parts[idx + 2].replace("_", " ").title()
            brand = brand or brand_guess
        except Exception:
            pass
    display_brand = (brand or "").replace("_", " ").title().strip()
    display_model = model_guess.replace("_", " ").title().strip()
    if display_brand and display_model.lower().startswith(display_brand.lower()):
        display_model = display_model[len(display_brand):].strip()
    name_out = f"{display_brand} {display_model}".strip()
    return name_out or model_guess.title()


def _resolve_icon_url(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    slug = Path(name.replace("$moddir$", "").replace("\\", "/")).stem.lower()
    icon_path = Path("storage") / "icons" / f"{slug}.png"
    if icon_path.exists():
        return f"/storage/icons/{icon_path.name}"
    return None


@router.get("/", response_model=list[VehicleResponse])
def list_vehicles(save_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Vehicle)
    if save_id:
        query = query.filter(Vehicle.save_id == save_id)
    rows = query.all()
    result = []
    for row in rows:
        ownership = row.property_state or ("LEASED" if row.is_leased else "OWNED")
        result.append(VehicleResponse(
            id=row.id,
            save_id=row.save_id,
            name=row.name,
            vehicle_type=row.vehicle_type,
            brand=row.brand,
            purchase_price=row.purchase_price,
            age_days=row.age_days,
            damage=row.damage,
            wear=row.wear,
            operating_time=row.operating_time,
            is_leased=row.is_leased,
            property_state=row.property_state,
            display_name=_resolve_display_name(row.name, row.brand),
            ownership=ownership,
            icon_url=_resolve_icon_url(row.name),
        ))
    return result

@router.post("/", response_model=VehicleResponse)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    db_vehicle = Vehicle(**vehicle.model_dump())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle
