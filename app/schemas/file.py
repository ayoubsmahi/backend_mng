from datetime import datetime

from pydantic import BaseModel


class FileResponse(BaseModel):
    id: int
    file_name: str
    entity_type: str
    entity_id: int
    file_size: int
    mime_type: str
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True
