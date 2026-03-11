from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, validator

from app.models.access_request import AccessRequestStatus
from app.models.user import UserRole


class AccessRequestCreate(BaseModel):
    email: str
    role: UserRole

    @validator("email")
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email")
        return email


class AccessRequestAction(BaseModel):
    notes: Optional[str] = None


class AccessRequestResponse(BaseModel):
    id: int
    email: str
    requested_role: UserRole
    status: AccessRequestStatus
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class AccessRequestListResponse(BaseModel):
    items: List[AccessRequestResponse]
    total: int
