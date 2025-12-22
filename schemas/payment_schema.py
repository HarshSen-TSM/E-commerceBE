# schemas/payment_schema.py

from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class PaymentSessionCreate(BaseModel):
    order_id: int = Field(..., description="Local order ID for which we are paying")


class PaymentSessionResponse(BaseModel):
    razorpay_order_id: str
    amount: int          # in paise
    currency: str
    key_id: str          # frontend uses this
    order_id: int


class PaymentVerifyRequest(BaseModel):
    order_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentRead(BaseModel):
    id: int
    order_id: int
    user_id: int
    status: str
    amount: Decimal
    currency: str

    class Config:
        from_attributes = True
