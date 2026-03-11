from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.expense import Expense
from app.models.file import File
from app.models.mission import Mission
from app.models.user import UserRole
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("/", response_model=ExpenseResponse)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.ACCOUNTANT,
            UserRole.PILOT,
        )
    ),
):
    if data.mission_id:
        mission = db.query(Mission).filter(Mission.id == data.mission_id).first()
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")

    if data.receipt_file_id:
        receipt = db.query(File).filter(File.id == data.receipt_file_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt file not found")

    expense = Expense(
        amount=data.amount,
        description=data.description,
        date=data.date,
        type=data.type,
        method=data.method,
        category_label=data.category_label,
        comment=data.comment,
        account_source=data.account_source,
        category_id=data.category_id,
        mission_id=data.mission_id,
        receipt_file_id=data.receipt_file_id,
        created_by=current_user.id,
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.ACCOUNTANT,
            UserRole.PILOT,
        )
    ),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if data.mission_id is not None:
        mission = db.query(Mission).filter(Mission.id == data.mission_id).first()
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")

    if data.receipt_file_id is not None:
        receipt = db.query(File).filter(File.id == data.receipt_file_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt file not found")

    for field in [
        "amount",
        "description",
        "date",
        "type",
        "method",
        "category_label",
        "comment",
        "account_source",
        "category_id",
        "mission_id",
        "receipt_file_id",
    ]:
        value = getattr(data, field)
        if value is not None:
            setattr(expense, field, value)

    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.ACCOUNTANT,
        )
    ),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted"}


@router.get("/", response_model=List[ExpenseResponse])
def list_expenses(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    type: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    missing_receipt: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.ACCOUNTANT,
            UserRole.INVESTOR,
            UserRole.PILOT,
        )
    ),
):
    query = db.query(Expense)

    if start_date is not None:
        query = query.filter(Expense.date >= start_date)
    if end_date is not None:
        query = query.filter(Expense.date <= end_date)
    if type is not None:
        query = query.filter(Expense.type == type)
    if category is not None:
        query = query.filter(Expense.category_label == category)
    if missing_receipt is True:
        query = query.filter(Expense.type != "Revenu").filter(Expense.receipt_file_id.is_(None))
    if missing_receipt is False:
        query = query.filter(Expense.receipt_file_id.is_not(None))

    return query.order_by(Expense.date.desc(), Expense.id.desc()).all()
