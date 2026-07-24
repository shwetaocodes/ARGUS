from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AnalystCreate(BaseModel):
    username: str
    password: str

class AnalystOut(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True