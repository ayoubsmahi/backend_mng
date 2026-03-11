from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, require_roles
from app.models.user import UserRole
from app.models.mission import Mission
from app.models.mission_note import MissionNote
from app.schemas.mission_note import (
    MissionNoteCreate,
    MissionNoteUpdate,
    MissionNoteResponse,
)

router = APIRouter(prefix="/missions/{mission_id}/notes", tags=["Mission Notes"])

@router.post("/", response_model=MissionNoteResponse)
def create_note(
    mission_id: int,
    data: MissionNoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    if current_user.role == UserRole.PILOT:
        if mission.assigned_pilot_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not allowed")

    note = MissionNote(
        mission_id=mission_id,
        user_id=current_user.id,
        content=data.content,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return note

@router.get("/", response_model=List[MissionNoteResponse])
def list_notes(
    mission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    return db.query(MissionNote).filter(
        MissionNote.mission_id == mission_id
    ).all()


@router.patch("/{note_id}", response_model=MissionNoteResponse)
def update_note(
    mission_id: int,
    note_id: int,
    data: MissionNoteUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.PILOT,
        )
    ),
):
    note = db.query(MissionNote).filter(MissionNote.id == note_id).first()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if current_user.role == UserRole.PILOT:
        if note.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not allowed")

    note.content = data.content
    db.commit()
    db.refresh(note)

    return note

