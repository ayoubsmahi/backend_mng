from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.expense_category import ExpenseCategory

router = APIRouter(prefix="/expense-categories", tags=["Master Data"])


@router.get("/", response_model=List[str])
def list_expense_categories(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = db.query(ExpenseCategory).order_by(ExpenseCategory.name.asc()).all()
    return [row.name for row in rows]
