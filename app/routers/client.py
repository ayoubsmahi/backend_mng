from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.schemas.client import ClientCreate, ClientResponse
from app.services.client_service import create_client, get_all_clients
from app.core.dependencies import get_db, require_roles
from app.models.user import UserRole

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", response_model=ClientResponse)
def create_new_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db),
    current_user = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    return create_client(db, client_data.name, client_data.address)


@router.get("/", response_model=List[ClientResponse])
def list_clients(
    db: Session = Depends(get_db),
    current_user = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    return get_all_clients(db)