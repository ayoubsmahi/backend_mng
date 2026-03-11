from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import decode_token
from app.models.user import UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == payload.get("sub")).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def require_roles(*allowed_roles):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker