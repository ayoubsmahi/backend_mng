from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.user import UserRole


class AccessRequestStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    requested_role = Column(Enum(UserRole), nullable=False)
    status = Column(
        Enum(AccessRequestStatus),
        nullable=False,
        default=AccessRequestStatus.PENDING,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
