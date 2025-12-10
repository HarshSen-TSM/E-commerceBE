# schemas.py  (or app/schemas/user.py)

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="The user's email address")
    full_name: Optional[str] = Field(None, description="The user's full name")
    address: Optional[str] = Field(None, description="The user's address")
    role: str = "user"
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plain password")


class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True 

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[EmailStr] = None
