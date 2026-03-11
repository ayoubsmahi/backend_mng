from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class MissionNote(Base):
    __tablename__ = "mission_notes"

    id = Column(Integer, primary_key=True, index=True)

    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())