from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
import app.models.models
from app.routers import fields

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

Base.metadata.create_all(bind=engine)

app.include_router(fields.router)

@app.get("/")
def root():
    return {"status": "ok", "app": "AgroPortál"}

@app.get("/health")
def health():
    return {"status": "healthy"}