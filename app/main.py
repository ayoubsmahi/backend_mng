from datetime import datetime
import os
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agriculture_types import AgricultureType
from app.models.expense_category import ExpenseCategory
from app.models.operation_types import OperationType
from app.models.user import User, UserRole
from app.routers import auth, client, expense, file, mission, mission_note
from app.routers import agriculture_type, operation_type, expense_category

import app.models.access_request
import app.models.agriculture_types
import app.models.client
import app.models.expense
import app.models.expense_category
import app.models.file
import app.models.invite
import app.models.mission
import app.models.mission_note
import app.models.operation_types
import app.models.password_reset
import app.models.user

app = FastAPI()

cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8080,"
    "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8080",
)
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def create_admin():
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "")

    if not admin_email or not admin_password:
        raise RuntimeError("Missing ADMIN_EMAIL / ADMIN_PASSWORD environment variables.")

    if len(admin_password) < 12:
        raise RuntimeError("ADMIN_PASSWORD must be at least 12 characters.")

    db = SessionLocal()
    if not db.query(User).filter(User.email == admin_email).first():
        admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role=UserRole.SUPER_ADMIN,
        )
        db.add(admin)
        db.commit()

    legacy_email = "admin@test.com"
    if admin_email != legacy_email:
        legacy_admin = db.query(User).filter(User.email == legacy_email).first()
        if legacy_admin:
            legacy_admin.email = (
                f"disabled_{legacy_admin.id}_{int(datetime.utcnow().timestamp())}" "@deleted.local"
            )
            legacy_admin.hashed_password = hash_password(secrets.token_urlsafe(24))
            db.commit()
    db.close()


@app.on_event("startup")
def seed_system_data():
    db = SessionLocal()

    if db.query(AgricultureType).count() == 0:
        agriculture_values = [
            "Blé",
            "Orge",
            "Légumineuses",
            "Agrumes",
            "Oliviers",
            "Légumes",
            "Amandier",
            "Palmier dattier",
        ]
        for name in agriculture_values:
            db.add(AgricultureType(name=name))

    if db.query(OperationType).count() == 0:
        operation_values = [
            "Épandage",
            "Traitement phytosanitaire",
            "Engrais liquides",
            "Herbicides",
            "Fongicides",
            "Pulvérisation",
        ]
        for name in operation_values:
            db.add(OperationType(name=name))

    if db.query(ExpenseCategory).count() == 0:
        category_values = [
            "Salaires",
            "Gasoil (Auto)",
            "Maintenance du Drone",
            "Entretien du véhicule",
            "Générateur",
            "Frais divers",
        ]
        for name in category_values:
            db.add(ExpenseCategory(name=name))

    db.commit()
    db.close()


app.include_router(auth.router)
app.include_router(client.router)
app.include_router(mission.router)
app.include_router(file.router)
app.include_router(mission_note.router)
app.include_router(expense.router)
app.include_router(agriculture_type.router)
app.include_router(operation_type.router)
app.include_router(expense_category.router)


@app.get("/")
def root():
    return {"message": "Drone Backend Running 🚀"}
