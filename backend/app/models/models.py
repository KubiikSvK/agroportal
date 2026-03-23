from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class Save(Base):
    __tablename__ = "saves"
    id = Column(String, primary_key=True, default=gen_uuid)
    game_day = Column(Integer, nullable=False)
    game_year = Column(Integer, nullable=False)
    season = Column(String)
    time_scale = Column(Float)
    balance = Column(Float)
    loan = Column(Float)
    map_id = Column(String)
    map_title = Column(String)
    uploaded_by = Column(String)
    pushed_at = Column(DateTime, server_default=func.now())
    field_snapshots = relationship("FieldSnapshot", back_populates="save")
    finance_snapshots = relationship("FinanceSnapshot", back_populates="save")
    vehicles = relationship("Vehicle", back_populates="save")
    weather_logs = relationship("WeatherLog", back_populates="save")
    harvests = relationship("Harvest", back_populates="save")

class Field(Base):
    __tablename__ = "fields"
    id = Column(String, primary_key=True, default=gen_uuid)
    fs_field_id = Column(Integer, nullable=False)
    fs_farmland_id = Column(Integer)
    name = Column(String)
    area_ha = Column(Float)
    owned = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    snapshots = relationship("FieldSnapshot", back_populates="field")
    rotations = relationship("CropRotation", back_populates="field")
    harvests = relationship("Harvest", back_populates="field")

class FieldSnapshot(Base):
    __tablename__ = "field_snapshots"
    id = Column(String, primary_key=True, default=gen_uuid)
    field_id = Column(String, ForeignKey("fields.id"))
    save_id = Column(String, ForeignKey("saves.id"))
    crop_type = Column(String)
    growth_state = Column(Integer)
    ground_type = Column(String)
    weed_state = Column(Integer)
    spray_level = Column(Integer)
    lime_level = Column(Integer)
    recorded_at = Column(DateTime, server_default=func.now())
    field = relationship("Field", back_populates="snapshots")
    save = relationship("Save", back_populates="field_snapshots")

class CropRotation(Base):
    __tablename__ = "crop_rotation"
    id = Column(String, primary_key=True, default=gen_uuid)
    field_id = Column(String, ForeignKey("fields.id"))
    game_year = Column(Integer)
    game_day = Column(Integer)
    crop_type = Column(String)
    notes = Column(Text)
    field = relationship("Field", back_populates="rotations")

class Harvest(Base):
    __tablename__ = "harvests"
    id = Column(String, primary_key=True, default=gen_uuid)
    field_id = Column(String, ForeignKey("fields.id"))
    save_id = Column(String, ForeignKey("saves.id"))
    crop_type = Column(String)
    amount_kg = Column(Float)
    yield_per_ha = Column(Float)
    best_price = Column(Float)
    game_day = Column(Integer)
    game_year = Column(Integer)
    source = Column(String, default="inferred")
    field = relationship("Field", back_populates="harvests")
    save = relationship("Save", back_populates="harvests")

class FinanceSnapshot(Base):
    __tablename__ = "finance_snapshots"
    id = Column(String, primary_key=True, default=gen_uuid)
    save_id = Column(String, ForeignKey("saves.id"))
    game_day = Column(Integer)
    balance = Column(Float)
    loan = Column(Float)
    harvest_income = Column(Float)
    mission_income = Column(Float)
    new_vehicles_cost = Column(Float)
    construction_cost = Column(Float)
    field_purchase = Column(Float)
    purchase_seeds = Column(Float)
    purchase_fertilizer = Column(Float)
    purchase_fuel = Column(Float)
    vehicle_running_cost = Column(Float)
    loan_interest = Column(Float)
    other = Column(Float)
    recorded_at = Column(DateTime, server_default=func.now())
    save = relationship("Save", back_populates="finance_snapshots")

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(String, primary_key=True, default=gen_uuid)
    save_id = Column(String, ForeignKey("saves.id"))
    name = Column(String)
    vehicle_type = Column(String)
    brand = Column(String)
    purchase_price = Column(Float)
    age_days = Column(Integer)
    damage = Column(Float)
    wear = Column(Float)
    operating_time = Column(Float)
    is_leased = Column(Boolean, default=False)
    save = relationship("Save", back_populates="vehicles")

class WeatherLog(Base):
    __tablename__ = "weather_log"
    id = Column(String, primary_key=True, default=gen_uuid)
    save_id = Column(String, ForeignKey("saves.id"))
    season = Column(String)
    condition = Column(String)
    game_day = Column(Integer)
    start_day = Column(Integer)
    save = relationship("Save", back_populates="weather_logs")

class SyncHistory(Base):
    __tablename__ = "sync_history"
    id = Column(String, primary_key=True, default=gen_uuid)
    action = Column(String)
    uploaded_by = Column(String)
    game_day = Column(Integer)
    game_year = Column(Integer)
    balance = Column(Float)
    synced_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="ok")