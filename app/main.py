from fastapi import FastAPI
from app.routers import auth 
from app.services.scheduler import start_scheduler
from app.core.dependencies import get_current_user
from app.models.analyst import Analyst
from app.routers import ingestion
from app.routers import sitreps
from app.routers import incidents
from app.routers import review
from app.routers import entities, map as map_router
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import patterns, detections
from app.routers import entity_resolution, notifications
from app.routers import historical_import
from app.core.audit_middleware import AuditLogMiddleware

app = FastAPI(title="ARGUS — Predictive Threat Pattern Recognition Platform")

app.include_router(auth.router)
app.include_router(ingestion.router)
app.include_router(sitreps.router)
app.include_router(incidents.router)
app.include_router(review.router)
app.include_router(entities.router)
app.include_router(map_router.router)
app.include_router(patterns.router)
app.include_router(detections.router)
app.include_router(historical_import.router)
app.add_middleware(AuditLogMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Status": "API is running successfully!"}

@app.get("/me")
def read_me(current_user: Analyst = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role}

@app.on_event("startup")
def on_startup():
    start_scheduler()
