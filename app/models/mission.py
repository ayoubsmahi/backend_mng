from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.mission_enums import MissionStatus, PaymentStatus


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)

    date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    location = Column(String, nullable=False)
    surface_ha = Column(Float, nullable=False)
    number_of_flights = Column(Integer, default=0)

    status = Column(Enum(MissionStatus), default=MissionStatus.PLANNED)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)

    # Legacy finance fields (kept for compatibility)
    revenue = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)

    # New mission finance fields
    price_per_ha = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    amount_paid = Column(Float, nullable=False, default=0)
    remaining_due = Column(Float, nullable=True)
    payment_method = Column(String, nullable=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    agriculture_type_id = Column(Integer, ForeignKey("agriculture_types.id"), nullable=False)
    operation_type_id = Column(Integer, ForeignKey("operation_types.id"), nullable=False)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_pilot_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("Client")
    agriculture_type = relationship("AgricultureType")
    operation_type = relationship("OperationType")
