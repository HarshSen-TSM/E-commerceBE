# models/payment_model.py

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, nullable=False)

    razorpay_order_id = Column(String(100), index=True, nullable=False)
    razorpay_payment_id = Column(String(100), index=True, nullable=True)
    razorpay_signature = Column(String(255), nullable=True)

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR")

    status = Column(String(50), default="PENDING")  # PENDING / SUCCESS / FAILED
    method = Column(String(50), nullable=True)      # card / upi / netbanking...

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    order = relationship("Order", back_populates="payments")
