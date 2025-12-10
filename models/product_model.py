# models.py

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from database import Base

# --- existing User model stays as it is ---


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String, nullable=True)     # simple single image for now
    status = Column(String(50), default="active") # active / inactive / deleted
    stock = Column(Integer, default=0)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category", back_populates="products")
