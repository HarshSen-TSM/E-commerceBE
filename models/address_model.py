from sqlalchemy import Column, Integer, String, Boolean
from database import Base   

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pin_code = Column(String, nullable=False)
    type = Column(String, nullable=False)  # e.g., 'home', 'work'
    is_primary = Column(Boolean, default=False)