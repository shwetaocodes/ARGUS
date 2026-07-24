from fastapi import FastAPI
from app.routers import auth 
from app.services.scheduler import start_scheduler
from app.core.dependencies import get_current_user
from app.models.analyst import Analyst
from app.routers import ingestion
from app.routers import sitreps
from fastapi import Depends


app = FastAPI(title="ARGUS — Predictive Threat Pattern Recognition Platform")

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(ingestion.router)
app.include_router(sitreps.router)

@app.get("/")
def read_root():
    return {"Status": "API is running successfully!"}

@app.get("/me")
def read_me(current_user: Analyst = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role}

@app.on_event("startup")
def on_startup():
    start_scheduler()

