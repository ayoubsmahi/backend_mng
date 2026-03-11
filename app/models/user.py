from sqlalchemy import Column, Integer, String, Enum
from app.db.base import Base
from enum import Enum as PyEnum


class UserRole(PyEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PILOT = "pilot"
    ACCOUNTANT = "accountant"
    INVESTOR = "investor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)