from sqlalchemy import Column, Integer, Float, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from app.db.base import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)

    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)

    # Transaction model extensions
    type = Column(String, nullable=False, default="Depenses")  # Depenses | Revenu
    method = Column(String, nullable=True)  # Cash | Virement | Carte...
    category_label = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    account_source = Column(String, nullable=True)

    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=True)
    receipt_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
