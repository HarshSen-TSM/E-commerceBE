# schemas/cart_schema.py

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class CartItemBase(BaseModel):
    product_id: int
    quantity: int


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: float


class CartSummary(BaseModel):
    subtotal: float
    tax: float
    discount: float
    total: float


class CartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    items: List[CartItemRead]
    summary: CartSummary
