# schemas/order_schema.py

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class OrderItemRead(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    user_id: int

    total_items: int
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    grand_total: Decimal

    status: str
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    items: List[OrderItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """
    Extra data when creating order from cart.
    You can extend later (for now just optional address + payment).
    """
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None
