from datetime import datetime
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.access_request import AccessRequest, AccessRequestStatus
from app.models.invite import Invite
from app.models.user import User
from app.services.invite_service import create_invite


def create_access_request(
    db: Session,
    email: str,
    role,
) -> Tuple[Optional[AccessRequest], int, str]:
    normalized_email = email.strip().lower()

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        return (
            None,
            200,
            "Ce compte existe déjà. Connectez-vous ou utilisez 'Mot de passe oublié'.",
        )

    latest_request = (
        db.query(AccessRequest)
        .filter(
            AccessRequest.email == normalized_email,
        )
        .order_by(AccessRequest.created_at.desc())
        .first()
    )

    if latest_request:
        if latest_request.status == AccessRequestStatus.PENDING:
            return (
                latest_request,
                200,
                "Demande déjà envoyée. Elle est en attente de validation.",
            )

        if latest_request.status == AccessRequestStatus.APPROVED:
            active_invite = (
                db.query(Invite)
                .filter(
                    Invite.email == normalized_email,
                    Invite.is_active.is_(True),
                    Invite.used_at.is_(None),
                )
                .order_by(Invite.created_at.desc())
                .first()
            )
            if active_invite:
                return (
                    latest_request,
                    200,
                    "Demande acceptée. Vous recevrez votre token d'invitation sous peu.",
                )
            return (
                latest_request,
                200,
                "Demande déjà acceptée.",
            )

        if latest_request.status == AccessRequestStatus.REJECTED:
            return (
                latest_request,
                200,
                "Votre demande a été rejetée. Veuillez contacter l'administrateur.",
            )

    access_request = AccessRequest(
        email=normalized_email,
        requested_role=role,
        status=AccessRequestStatus.PENDING,
    )
    db.add(access_request)
    db.commit()
    db.refresh(access_request)
    return access_request, 201, "Demande envoyée."


def list_access_requests(
    db: Session,
    status: Optional[AccessRequestStatus],
    limit: int,
    offset: int,
) -> Tuple[list[AccessRequest], int]:
    query = db.query(AccessRequest)

    if status is not None:
        query = query.filter(AccessRequest.status == status)

    total = query.count()
    items = (
        query.order_by(AccessRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_access_request_or_404(db: Session, request_id: int) -> AccessRequest:
    access_request = (
        db.query(AccessRequest)
        .filter(AccessRequest.id == request_id)
        .first()
    )
    if not access_request:
        raise HTTPException(status_code=404, detail="Access request not found")
    return access_request


def approve_access_request(
    db: Session,
    access_request: AccessRequest,
    admin_id: int,
    notes: Optional[str] = None,
):
    if access_request.status != AccessRequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="Request already processed")

    invite = create_invite(
        db=db,
        email=access_request.email,
        role=access_request.requested_role,
        admin_id=admin_id,
    )

    access_request.status = AccessRequestStatus.APPROVED
    access_request.reviewed_at = datetime.utcnow()
    access_request.reviewed_by = admin_id
    access_request.notes = notes

    db.commit()
    db.refresh(access_request)
    return invite


def reject_access_request(
    db: Session,
    access_request: AccessRequest,
    admin_id: int,
    notes: Optional[str] = None,
) -> AccessRequest:
    if access_request.status != AccessRequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="Request already processed")

    access_request.status = AccessRequestStatus.REJECTED
    access_request.reviewed_at = datetime.utcnow()
    access_request.reviewed_by = admin_id
    access_request.notes = notes

    db.commit()
    db.refresh(access_request)
    return access_request
