import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, UploadFile
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.orm import Session

from app.core.r2_storage import (
    build_r2_key,
    delete_r2_object,
    normalize_db_path_to_r2_key,
    r2_enabled,
    stream_r2_object,
    upload_bytes_to_r2,
)
from app.core.dependencies import get_current_user, get_db
from app.models.expense import Expense
from app.models.file import File
from app.models.mission import Mission
from app.models.user import UserRole
from app.schemas.file import FileResponse

router = APIRouter(prefix="/files", tags=["Files"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
ALLOWED_ENTITY_TYPES = ["mission", "expense", "finance", "bank", "authority"]


def _ensure_entity_access(entity_type: str, entity_id: int, db: Session, current_user) -> int:
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="Invalid entity type")

    if entity_type == "mission":
        mission = db.query(Mission).filter(Mission.id == entity_id).first()
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")

        if current_user.role == UserRole.PILOT and mission.assigned_pilot_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not allowed")

        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PILOT]:
            raise HTTPException(status_code=403, detail="Not allowed")
        return entity_id

    if entity_type == "expense":
        expense = db.query(Expense).filter(Expense.id == entity_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if current_user.role not in [
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.ACCOUNTANT,
            UserRole.PILOT,
            UserRole.INVESTOR,
        ]:
            raise HTTPException(status_code=403, detail="Not allowed")
        return entity_id

    if entity_type in ["finance", "bank", "authority"]:
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ACCOUNTANT]:
            raise HTTPException(status_code=403, detail="Not allowed")
        return 0

    return entity_id


@router.post("/upload", response_model=FileResponse)
def upload_file(
    entity_type: str,
    entity_id: int = 0,
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    normalized_entity_id = _ensure_entity_access(entity_type, entity_id, db, current_user)

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path: str
    file_size: int

    if r2_enabled():
        content = file.file.read()
        file_size = len(content)
        key = build_r2_key(entity_type, normalized_entity_id, unique_filename)
        upload_bytes_to_r2(key=key, content=content, content_type=file.content_type)
        file_path = f"r2:{key}"
    else:
        entity_path = os.path.join(UPLOAD_DIR, entity_type, str(normalized_entity_id))
        os.makedirs(entity_path, exist_ok=True)

        file_path = os.path.join(entity_path, unique_filename)
        content = file.file.read()
        file_size = len(content)
        with open(file_path, "wb") as buffer:
            buffer.write(content)

    new_file = File(
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        entity_type=entity_type,
        entity_id=normalized_entity_id,
        uploaded_by=current_user.id,
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file


@router.get("/{file_id}")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    _ensure_entity_access(file.entity_type, file.entity_id, db, current_user)

    if r2_enabled() and file.file_path and file.file_path.startswith("r2:"):
        key = normalize_db_path_to_r2_key(file.file_path)
        return stream_r2_object(key=key, download_name=file.file_name, content_type=file.mime_type)

    if not os.path.exists(file.file_path):
        # Happens on ephemeral disks after deploy/restart/scale when uploads were stored locally.
        raise HTTPException(status_code=404, detail="File content missing on server storage")

    return FastAPIFileResponse(path=file.file_path, filename=file.file_name)


@router.get("/", response_model=List[FileResponse])
def list_files(
    entity_type: str,
    entity_id: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    normalized_entity_id = _ensure_entity_access(entity_type, entity_id, db, current_user)

    query = db.query(File).filter(File.entity_type == entity_type)
    if entity_type in ["mission", "expense"]:
        query = query.filter(File.entity_id == normalized_entity_id)

    return query.order_by(File.created_at.desc(), File.id.desc()).all()


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    _ensure_entity_access(file.entity_type, file.entity_id, db, current_user)

    if r2_enabled() and file.file_path and file.file_path.startswith("r2:"):
        key = normalize_db_path_to_r2_key(file.file_path)
        delete_r2_object(key=key)
    else:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)

    db.delete(file)
    db.commit()
    return {"message": "File deleted successfully"}
