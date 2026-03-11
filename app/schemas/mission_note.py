from pydantic import BaseModel
from datetime import datetime


class MissionNoteCreate(BaseModel):
    content: str


class MissionNoteUpdate(BaseModel):
    content: str


class MissionNoteResponse(BaseModel):
    id: int
    mission_id: int
    user_id: int
    content: str
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True