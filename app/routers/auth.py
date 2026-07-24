from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.analyst import Analyst
from app.schemas.auth import Token, AnalystCreate, AnalystOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=AnalystOut)
def register(payload: AnalystCreate, db: Session = Depends(get_db)):
    existing = db.query(Analyst).filter(Analyst.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    analyst = Analyst(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="analyst",
    )
    db.add(analyst)
    db.commit()
    db.refresh(analyst)
    return analyst

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    analyst = db.query(Analyst).filter(Analyst.username == form_data.username).first()
    if not analyst or not verify_password(form_data.password, analyst.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": str(analyst.id)})
    return {"access_token": token, "token_type": "bearer"}