# models.py  (or app/models/user.py)

from sqlalchemy import Column, Integer, String, Boolean 
from sqlalchemy.orm import relationship

from database import Base  # your existing Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")  # e.g., 'user', 'admin'
    name = Column(String, nullable=True)
    address = Column(String, nullable=True)

    cart = relationship("Cart", uselist=False, back_populates="user")