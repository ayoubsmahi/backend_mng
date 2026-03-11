from sqlalchemy.orm import Session
from app.models.client import Client


def create_client(db: Session, name: str, address: str):
    client = Client(name=name, address=address)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_all_clients(db: Session):
    return db.query(Client).all()