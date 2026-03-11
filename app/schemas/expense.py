from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    amount: float = Field(gt=0)
    description: Optional[str] = None
    date: date
    type: str = "Depenses"
    method: Optional[str] = None
    category_label: Optional[str] = None
    comment: Optional[str] = None
    account_source: Optional[str] = None
    category_id: Optional[int] = None
    mission_id: Optional[int] = None
    receipt_file_id: Optional[int] = None


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    date: Optional[date] = None
    type: Optional[str] = None
    method: Optional[str] = None
    category_label: Optional[str] = None
    comment: Optional[str] = None
    account_source: Optional[str] = None
    category_id: Optional[int] = None
    mission_id: Optional[int] = None
    receipt_file_id: Optional[int] = None


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    description: Optional[str]
    date: date
    type: str
    method: Optional[str]
    category_label: Optional[str]
    comment: Optional[str]
    account_source: Optional[str]
    category_id: Optional[int]
    mission_id: Optional[int]
    receipt_file_id: Optional[int]

    class Config:
        from_attributes = True
