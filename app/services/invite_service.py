import secrets
from sqlalchemy.orm import Session
from app.models.invite import Invite
from app.models.user import UserRole


def generate_invite_token():
    return secrets.token_urlsafe(32)


def create_invite(db: Session, email: str, role: UserRole, admin_id: int):
    token = generate_invite_token()

    invite = Invite(
        email=email,
        role=role,
        token=token,
        created_by=admin_id,
        is_active=True,
    )

    db.add(invite)
    db.commit()
    db.refresh(invite)

    return invite
