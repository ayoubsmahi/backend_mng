import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.password_reset import PasswordResetToken
from app.models.user import User

RESET_TOKEN_EXPIRY_MINUTES = 15


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, email: str):
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        return None, None

    # Invalidate previous unused tokens for this user.
    (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .update({"used_at": datetime.utcnow()}, synchronize_session=False)
    )

    raw_token = secrets.token_urlsafe(32)
    token_row = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    )
    db.add(token_row)
    db.commit()
    db.refresh(token_row)
    return user, raw_token


def reset_password_with_token(db: Session, token: str, new_password_hash: str) -> None:
    token_row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == _hash_token(token.strip()))
        .first()
    )

    if not token_row:
        raise HTTPException(status_code=404, detail="Invalid reset token")

    if token_row.used_at is not None:
        raise HTTPException(status_code=400, detail="Reset token already used")

    if token_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token expired")

    user = db.query(User).filter(User.id == token_row.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = new_password_hash
    token_row.used_at = datetime.utcnow()

    db.commit()
