from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from app.db.base import Base
from app.models.user import UserRole

class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    role = Column(Enum(UserRole), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)

    is_active = Column(Boolean, default=True)
    used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())