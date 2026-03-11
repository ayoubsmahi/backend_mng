from datetime import datetime
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.access_request import AccessRequestStatus
from app.models.user import User, UserRole
from app.models.invite import Invite
from app.core.security import (
    verify_password,
    create_access_token,
    hash_password,
)
from app.core.dependencies import (
    get_current_user,
    require_roles,
    get_db,
)
from app.schemas.access_request import (
    AccessRequestAction,
    AccessRequestCreate,
    AccessRequestListResponse,
)
from app.services.access_request_service import (
    approve_access_request,
    create_access_request,
    get_access_request_or_404,
    list_access_requests,
    reject_access_request,
)
from app.services.invite_service import create_invite
from app.services.password_reset_service import (
    create_password_reset_token,
    reset_password_with_token,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
_RATE_LIMIT_BUCKETS = defaultdict(deque)
_RATE_LIMIT_LOCK = Lock()


class InviteRequest(BaseModel):
    email: str
    role: UserRole


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class DeleteAccountRequest(BaseModel):
    password: str


def _enforce_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    now = time.time()
    with _RATE_LIMIT_LOCK:
        bucket = _RATE_LIMIT_BUCKETS[key]
        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )
        bucket.append(now)



@router.post("/request-access", status_code=201)
def request_access(
    request_data: AccessRequestCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(
        key=f"request_access:{client_ip}:{request_data.email.strip().lower()}",
        max_requests=3,
        window_seconds=600,
    )

    access_request, status_code, message = create_access_request(
        db=db,
        email=request_data.email,
        role=request_data.role,
    )
    response.status_code = status_code
    return {
        "message": message,
        "request_id": access_request.id if access_request else None,
    }


@router.get("/access-requests", response_model=AccessRequestListResponse)
def get_access_requests(
    status: Optional[AccessRequestStatus] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_admin=Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    items, total = list_access_requests(
        db=db,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total}


@router.post("/access-requests/{request_id}/approve")
def approve_request(
    request_id: int,
    payload: AccessRequestAction,
    current_admin=Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    access_request = get_access_request_or_404(db, request_id)
    invite = approve_access_request(
        db=db,
        access_request=access_request,
        admin_id=current_admin.id,
        notes=payload.notes,
    )
    return {
        "message": "Request approved",
        "request_id": access_request.id,
        "invite": {
            "email": invite.email,
            "role": invite.role,
            "token": invite.token,
        },
    }


@router.post("/access-requests/{request_id}/reject")
def reject_request(
    request_id: int,
    payload: AccessRequestAction,
    current_admin=Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    access_request = get_access_request_or_404(db, request_id)
    reject_access_request(
        db=db,
        access_request=access_request,
        admin_id=current_admin.id,
        notes=payload.notes,
    )
    return {
        "message": "Request rejected",
        "request_id": access_request.id,
    }


@router.post("/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(
        key=f"login:{client_ip}:{form_data.username.strip().lower()}",
        max_requests=10,
        window_seconds=300,
    )

    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }


@router.post("/invite")
def invite_user(
    invite_data: InviteRequest,
    current_admin=Depends(
        require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    ),
    db: Session = Depends(get_db),
):
    invite = create_invite(
        db=db,
        email=invite_data.email,
        role=invite_data.role,
        admin_id=current_admin.id,
    )

    return {
        "message": "Invite created",
        "email": invite.email,
        "role": invite.role,
        "token": invite.token,
    }


@router.post("/accept-invite")
def accept_invite(
    request: AcceptInviteRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    client_ip = http_request.client.host if http_request.client else "unknown"
    _enforce_rate_limit(
        key=f"accept_invite:{client_ip}:{request.token.strip()}",
        max_requests=10,
        window_seconds=3600,
    )

    invite = (
        db.query(Invite)
        .filter(Invite.token == request.token)
        .first()
    )

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite token")

    if not invite.is_active or invite.used_at is not None:
        raise HTTPException(status_code=400, detail="Invite already used or inactive")

    # Create user
    user = User(
        email=invite.email,
        hashed_password=hash_password(request.password),
        role=invite.role,
    )

    db.add(user)

    # Mark invite as used
    invite.used_at = datetime.utcnow()
    invite.is_active = False

    db.commit()

    return {"message": "Account created successfully"}


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    client_ip = http_request.client.host if http_request.client else "unknown"
    _enforce_rate_limit(
        key=f"forgot_password:{client_ip}:{request.email.strip().lower()}",
        max_requests=3,
        window_seconds=900,
    )

    create_password_reset_token(db=db, email=request.email)

    return {
        "message": "Si cet email existe, un token de réinitialisation a été généré.",
    }


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    client_ip = http_request.client.host if http_request.client else "unknown"
    _enforce_rate_limit(
        key=f"reset_password:{client_ip}:{request.token.strip()}",
        max_requests=10,
        window_seconds=3600,
    )

    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")

    reset_password_with_token(
        db=db,
        token=request.token,
        new_password_hash=hash_password(request.password),
    )
    return {"message": "Mot de passe réinitialisé avec succès"}


@router.delete("/me")
def delete_my_account(
    request: DeleteAccountRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    timestamp = int(datetime.utcnow().timestamp())
    current_user.email = f"deleted_{current_user.id}_{timestamp}@deleted.local"
    current_user.hashed_password = hash_password(secrets.token_urlsafe(24))

    db.commit()

    return {"message": "Account deleted successfully"}
