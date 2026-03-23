from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
import app.models.models
from app.seed import ensure_crops, ensure_vehicle_property_state
from app.middleware import ApiKeyMiddleware
from app.routers import fields, saves, snapshots, finance, vehicles, sync, harvests, weather, maps, crops, rotation

app = FastAPI(
    title="AgroPortál API",
    description="FS25 farm management portal",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    ApiKeyMiddleware,
    protected_prefixes=["/sync/push", "/sync/pull", "/sync/replace", "/sync/deploy"],
)

Base.metadata.create_all(bind=engine)

app.mount("/storage", StaticFiles(directory="storage"), name="storage")

ensure_vehicle_property_state(engine)

_session = SessionLocal()
try:
    ensure_crops(_session)
finally:
    _session.close()

app.include_router(fields.router)
app.include_router(saves.router)
app.include_router(snapshots.router)
app.include_router(finance.router)
app.include_router(vehicles.router)
app.include_router(sync.router)
app.include_router(harvests.router)
app.include_router(weather.router)
app.include_router(maps.router)
app.include_router(crops.router)
app.include_router(rotation.router)

@app.get("/")
def root():
    return {"status": "ok", "app": "AgroPortál"}

@app.get("/health")
def health():
    return {"status": "healthy"}
