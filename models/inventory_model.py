from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)

    total_stock = Column(Integer, nullable=False, default=0)
    available_stock = Column(Integer, nullable=False, default=0)
    reserved_stock = Column(Integer, nullable=False, default=0)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
