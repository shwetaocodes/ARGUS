from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.analyst import Analyst

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SENIOR_ROLES = {"senior_analyst", "admin"}

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Analyst:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        analyst_id: str = payload.get("sub")
        if analyst_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    analyst = db.query(Analyst).filter(Analyst.id == int(analyst_id)).first()
    if analyst is None:
        raise credentials_exception
    return analyst

def require_senior_analyst(current_user: Analyst = Depends(get_current_user)) -> Analyst:
    if current_user.role not in SENIOR_ROLES:
        raise HTTPException(status_code=403, detail="Senior analyst role required for this action")
    return current_user