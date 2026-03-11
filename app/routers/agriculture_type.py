from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.agriculture_types import AgricultureType

router = APIRouter(prefix="/agriculture-types", tags=["Master Data"])


@router.get("/", response_model=List[str])
def list_agriculture_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = db.query(AgricultureType).order_by(AgricultureType.name.asc()).all()
    return [row.name for row in rows]
