from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.models.mission_enums import MissionStatus, PaymentStatus


class MissionCreate(BaseModel):
    date: date
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: str
    surface_ha: float
    number_of_flights: Optional[int] = 0
    client_id: int
    agriculture_type_id: int
    operation_type_id: int
    assigned_pilot_id: Optional[int] = None
    revenue: Optional[float] = None
    cost: Optional[float] = None
    price_per_ha: Optional[float] = None
    total_price: Optional[float] = None
    amount_paid: Optional[float] = 0
    payment_method: Optional[str] = None


class MissionResponse(BaseModel):
    id: int
    date: date
    start_date: Optional[date]
    end_date: Optional[date]
    location: str
    surface_ha: float
    number_of_flights: int
    status: MissionStatus
    payment_status: PaymentStatus
    client_id: int
    agriculture_type_id: int
    operation_type_id: int
    assigned_pilot_id: Optional[int]
    revenue: Optional[float]
    cost: Optional[float]
    price_per_ha: Optional[float]
    total_price: Optional[float]
    amount_paid: float
    remaining_due: Optional[float]
    payment_method: Optional[str]

    class Config:
        from_attributes = True


class MissionStatusUpdate(BaseModel):
    status: MissionStatus


class MissionFlightsUpdate(BaseModel):
    number_of_flights: int


class MissionFinanceUpdate(BaseModel):
    revenue: Optional[float] = None
    cost: Optional[float] = None


class MissionStartUpdate(BaseModel):
    surface_ha: Optional[float] = None
    price_per_ha: Optional[float] = None
    total_price: Optional[float] = None


class MissionCompleteUpdate(BaseModel):
    surface_ha: Optional[float] = None
    amount_paid: Optional[float] = None
    payment_method: Optional[str] = None


class MissionUpdate(BaseModel):
    date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    surface_ha: Optional[float] = None
    number_of_flights: Optional[int] = None
    client_id: Optional[int] = None
    agriculture_type_id: Optional[int] = None
    operation_type_id: Optional[int] = None
    assigned_pilot_id: Optional[int] = None
    price_per_ha: Optional[float] = None
    total_price: Optional[float] = None
    amount_paid: Optional[float] = None
    payment_method: Optional[str] = None
