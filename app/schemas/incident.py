from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.incident import IncidentType

class IncidentCreate(BaseModel):
    incident_date: datetime
    location: str
    type: IncidentType
    description: str
    reliability_rating: int = Field(ge=1, le=5)
    event_id: Optional[int] = None

class IncidentOut(BaseModel):
    id: int
    analyst_id: int
    event_id: Optional[int]
    incident_date: datetime
    location: str
    type: IncidentType
    description: str
    reliability_rating: int
    created_at: datetime

    class Config:
        from_attributes = True