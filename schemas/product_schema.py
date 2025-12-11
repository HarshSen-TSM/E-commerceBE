# Schemas/product_schema.py

from typing import Optional
from pydantic import BaseModel, Field


# ---------- Category ----------

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryRead(CategoryBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Product ----------

VALID_PRODUCT_STATUSES = ["active", "inactive", "deleted"]


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    status: str = Field("active", pattern=r"^(active|inactive|deleted)$")
    stock: int = 0
    category_id: Optional[int] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(active|inactive|deleted)$")
    stock: Optional[int] = None
    category_id: Optional[int] = None


class ProductRead(ProductBase):
    id: int

    class Config:
        from_attributes = True
