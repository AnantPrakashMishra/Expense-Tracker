from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False)  # income / expense
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    frequency = Column(String(20), nullable=False)  # daily/weekly/monthly/yearly
    start_date = Column(Date, nullable=False)
    next_occurrence = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    payment_method = Column(String(50), default="other")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="recurring_transactions")
    category = relationship("Category", back_populates="recurring_transactions")
    transactions = relationship("Transaction", back_populates="recurring")
