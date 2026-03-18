from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.mission import Mission
from app.models.mission_enums import MissionStatus, PaymentStatus
from app.models.mission_note import MissionNote
from app.models.user import UserRole


def _compute_total_price(surface_ha, price_per_ha, provided_total):
    if surface_ha is not None and price_per_ha is not None:
        return round(float(surface_ha) * float(price_per_ha), 2)
    if provided_total is not None:
        return round(float(provided_total), 2)
    return None


def _compute_remaining_due(total_price, amount_paid):
    if total_price is None:
        return None
    paid = float(amount_paid or 0)
    remaining = float(total_price) - paid
    return round(remaining if remaining > 0 else 0.0, 2)


def _compute_payment_status(total_price, amount_paid):
    paid = float(amount_paid or 0)
    if total_price is None or total_price <= 0:
        return PaymentStatus.PAID if paid > 0 else PaymentStatus.UNPAID
    if paid <= 0:
        return PaymentStatus.UNPAID
    if paid >= total_price:
        return PaymentStatus.PAID
    return PaymentStatus.PARTIALLY_PAID


def _apply_finance(mission: Mission):
    mission.total_price = _compute_total_price(
        mission.surface_ha,
        mission.price_per_ha,
        mission.total_price,
    )
    mission.remaining_due = _compute_remaining_due(mission.total_price, mission.amount_paid)
    mission.payment_status = _compute_payment_status(mission.total_price, mission.amount_paid)
    if mission.total_price is not None:
        mission.revenue = mission.total_price


def create_mission(db: Session, data, current_user):
    assigned_pilot = data.assigned_pilot_id
    if current_user.role == UserRole.PILOT:
        assigned_pilot = current_user.id

    mission = Mission(
        date=data.date,
        start_date=data.start_date,
        end_date=data.end_date,
        location=data.location,
        surface_ha=data.surface_ha,
        number_of_flights=data.number_of_flights,
        client_id=data.client_id,
        agriculture_type_id=data.agriculture_type_id,
        operation_type_id=data.operation_type_id,
        assigned_pilot_id=assigned_pilot,
        created_by=current_user.id,
        revenue=data.revenue if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] else None,
        cost=data.cost if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] else None,
        price_per_ha=data.price_per_ha,
        total_price=data.total_price,
        amount_paid=float(data.amount_paid or 0),
        payment_method=data.payment_method,
    )

    _apply_finance(mission)

    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def get_missions(db: Session, current_user):
    if current_user.role == UserRole.PILOT:
        return db.query(Mission).filter(Mission.assigned_pilot_id == current_user.id).all()

    if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT, UserRole.INVESTOR]:
        return db.query(Mission).all()

    return []


def get_mission_or_none(db: Session, mission_id: int):
    return db.query(Mission).filter(Mission.id == mission_id).first()


def _can_operate_mission(mission: Mission, current_user):
    if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        return True
    if current_user.role == UserRole.PILOT and mission.assigned_pilot_id == current_user.id:
        return True
    return False


def update_mission_status(db: Session, mission_id: int, status, current_user):
    mission = get_mission_or_none(db, mission_id)
    if not mission:
        return None
    if not _can_operate_mission(mission, current_user):
        return None

    mission.status = status
    db.commit()
    db.refresh(mission)
    return mission


def update_mission_flights(db: Session, mission_id: int, flights: int, current_user):
    mission = get_mission_or_none(db, mission_id)
    if not mission:
        return None
    if not _can_operate_mission(mission, current_user):
        return None

    mission.number_of_flights = flights
    db.commit()
    db.refresh(mission)
    return mission


def update_mission_finance(db: Session, mission_id: int, data, current_user):
    mission = get_mission_or_none(db, mission_id)
    if not mission:
        return None

    mission.revenue = data.revenue
    mission.cost = data.cost
    db.commit()
    db.refresh(mission)
    return mission


def update_mission(db: Session, mission_id: int, data, current_user):
    mission = get_mission_or_none(db, mission_id)
    if not mission:
        return None
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        return None

    for field in [
        "date",
        "start_date",
        "end_date",
        "location",
        "surface_ha",
        "number_of_flights",
        "client_id",
        "agriculture_type_id",
        "operation_type_id",
        "assigned_pilot_id",
        "price_per_ha",
        "total_price",
        "amount_paid",
        "payment_method",
    ]:
        value = getattr(data, field, None)
        if value is not None:
            setattr(mission, field, value)

    _apply_finance(mission)
    db.commit()
    db.refresh(mission)
    return mission


def start_mission(db: Session, mission_id: int, data, current_user):
    mission = get_mission_or_none(db, mission_id)
    if not mission:
        return None
    if not _can_operate_mission(mission, current_user):
        return None

    if data.surface_ha is not None:
        mission.surface_ha = data.surface_ha
    if data.price_per_ha is not None:
        mission.price_per_ha = data.price_per_ha
    if data.total_price is not None:
        mission.total_price = data.total_price

    mission.status = MissionStatus.IN_PROGRESS
    _apply_finance(mission)
    db.commit()
    db.refresh(mission)
    return mission


def complete_mission(db: Session, mission_id: int, data, current_user):
    mission = get_mission_or_none(db, mission_id)
    if not mission:
        return None
    if not _can_operate_mission(mission, current_user):
        return None

    if data.surface_ha is not None:
        mission.surface_ha = data.surface_ha
    if data.amount_paid is not None:
        mission.amount_paid = float(data.amount_paid)
    if data.payment_method is not None:
        mission.payment_method = data.payment_method

    mission.status = MissionStatus.COMPLETED
    _apply_finance(mission)
    db.commit()
    db.refresh(mission)
    return mission


def delete_mission(db: Session, mission_id: int, current_user):
    mission = get_mission_or_none(db, mission_id)
    if not mission:
        return None

    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        return None

    db.query(MissionNote).filter(MissionNote.mission_id == mission_id).delete()
    db.query(Expense).filter(Expense.mission_id == mission_id).update({"mission_id": None})
    db.delete(mission)
    db.commit()
    return True
