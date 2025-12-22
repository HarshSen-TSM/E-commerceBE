# models/order_model.py

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Numeric,
    DateTime,
)
from sqlalchemy.orm import relationship

from database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    total_items = Column(Integer, default=0)
    subtotal = Column(Numeric(10, 2), default=Decimal("0.00"))
    tax = Column(Numeric(10, 2), default=Decimal("0.00"))
    discount = Column(Numeric(10, 2), default=Decimal("0.00"))
    grand_total = Column(Numeric(10, 2), default=Decimal("0.00"))

    status = Column(String, default="PENDING")  # PENDING, PAID, SHIPPED, etc.

    shipping_address = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)  # e.g. "COD", "CARD"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = relationship("User")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payments = relationship("Payment", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String, nullable=False)

    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
