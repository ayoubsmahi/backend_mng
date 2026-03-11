from sqlalchemy import Column, Integer, String
from app.db.base import Base


class OperationType(Base):
    __tablename__ = "operation_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)