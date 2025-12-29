from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, nullable=False)

    razorpay_order_id = Column(String(100), nullable=False)
    razorpay_payment_id = Column(String(100), nullable=False)
    razorpay_signature = Column(String(255), nullable=False)

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR")

    status = Column(String(50), nullable=False, default="PENDING")
    method = Column(String(50), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "razorpay_payment_id",
            name="uq_order_payment_idempotent",
        ),
    )

    order = relationship("Order", back_populates="payments")
