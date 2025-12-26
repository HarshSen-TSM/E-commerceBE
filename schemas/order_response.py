from pydantic import BaseModel
from typing import List
from datetime import datetime
from decimal import Decimal


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    total_items: int
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    grand_total: Decimal
    status: str
    shipping_address: str | None
    payment_method: str | None
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True
