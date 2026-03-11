from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.user import UserRole
from app.schemas.mission import (
    MissionCompleteUpdate,
    MissionCreate,
    MissionFinanceUpdate,
    MissionFlightsUpdate,
    MissionResponse,
    MissionStartUpdate,
    MissionStatusUpdate,
    MissionUpdate,
)
from app.services.mission_service import (
    complete_mission,
    create_mission,
    get_missions,
    start_mission,
    update_mission,
    update_mission_finance,
    update_mission_flights,
    update_mission_status,
)

router = APIRouter(prefix="/missions", tags=["Missions"])


@router.post("/", response_model=MissionResponse)
def create_new_mission(
    mission_data: MissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    return create_mission(db, mission_data, current_user)


@router.get("/", response_model=List[MissionResponse])
def list_missions(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
            UserRole.ACCOUNTANT,
            UserRole.INVESTOR,
        )
    ),
):
    return get_missions(db, current_user)


@router.patch("/{mission_id}", response_model=MissionResponse)
def patch_mission(
    mission_id: int,
    data: MissionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    mission = update_mission(db, mission_id, data, current_user)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.patch("/{mission_id}/start", response_model=MissionResponse)
def start_mission_endpoint(
    mission_id: int,
    data: MissionStartUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PILOT)
    ),
):
    mission = start_mission(db, mission_id, data, current_user)
    if not mission:
        raise HTTPException(status_code=403, detail="Not allowed or mission not found")
    return mission


@router.patch("/{mission_id}/complete", response_model=MissionResponse)
def complete_mission_endpoint(
    mission_id: int,
    data: MissionCompleteUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PILOT)
    ),
):
    mission = complete_mission(db, mission_id, data, current_user)
    if not mission:
        raise HTTPException(status_code=403, detail="Not allowed or mission not found")
    return mission


@router.patch("/{mission_id}/status", response_model=MissionResponse)
def change_status(
    mission_id: int,
    data: MissionStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    mission = update_mission_status(db, mission_id, data.status, current_user)
    if not mission:
        raise HTTPException(status_code=403, detail="Not allowed")
    return mission


@router.patch("/{mission_id}/flights", response_model=MissionResponse)
def change_flights(
    mission_id: int,
    data: MissionFlightsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    mission = update_mission_flights(db, mission_id, data.number_of_flights, current_user)
    if not mission:
        raise HTTPException(status_code=403, detail="Not allowed")
    return mission


@router.patch("/{mission_id}/finance", response_model=MissionResponse)
def change_finance(
    mission_id: int,
    data: MissionFinanceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
        )
    ),
):
    mission = update_mission_finance(db, mission_id, data, current_user)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission
