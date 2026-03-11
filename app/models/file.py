from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)

    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)

    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())