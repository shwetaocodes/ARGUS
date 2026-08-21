from pydantic import BaseModel, Field, field_validator
from typing import Optional

VALID_ENTITY_TYPES = {"person", "org", "location", "military_unit", "weapon", "topic"}
VALID_CATEGORIES = {
    "infiltration_attempt", "ied", "protest", "troop_movement", "propaganda_broadcast",
    "ceasefire_violation", "supply_convoy", "aerial_activity", "other",
}
VALID_SENTIMENTS = {"hostile", "neutral", "de_escalatory"}
VALID_CONFIDENCE = {"high", "medium", "low"}


class ExtractedEntity(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    type: str
    confidence: str = "low"

    @field_validator("type")
    @classmethod
    def type_must_be_valid(cls, v):
        if v not in VALID_ENTITY_TYPES:
            raise ValueError(f"invalid entity type: {v}")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_valid(cls, v):
        return v if v in VALID_CONFIDENCE else "low"  
        

class NERResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list, max_length=50)


class ClassificationResult(BaseModel):
    category: str
    confidence: str = "low"

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, v):
        return v if v in VALID_CATEGORIES else "other"  


class SentimentResult(BaseModel):
    tone: str
    confidence: str = "low"

    @field_validator("tone")
    @classmethod
    def tone_must_be_valid(cls, v):
        if v not in VALID_SENTIMENTS:
            raise ValueError(f"invalid sentiment: {v}")
        return v