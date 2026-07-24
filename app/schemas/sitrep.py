from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SitrepCreate(BaseModel):
    content: str
    event_id: Optional[int] = None

class SitrepOut(BaseModel):
    id: int
    analyst_id: int
    event_id: Optional[int]
    content: str
    created_at: datetime

    class Config:
        from_attributes = True