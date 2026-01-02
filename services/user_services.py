# services.py  (or app/services/user_service.py)

from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from repositories.user_repository import UserRepository
from schemas.user_schema import UserCreate, UserRead, UserLogin, Token
from utils.jwt_utils import hash_password, verify_password, create_access_token


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def register_user(self, user_in: UserCreate) -> UserRead:
        existing = self.repo.get_by_email(user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed = hash_password(user_in.password)
        user = self.repo.create(user_in, hashed_password=hashed)
        return UserRead.from_orm(user)

    def authenticate_user(self, login_data: UserLogin):
        user = self.repo.get_by_email(login_data.email)
        if not user:
            return None
        if not verify_password(login_data.password, user.hashed_password):
            return None
        return user

    def login(self, login_data: UserLogin) -> Token:
        user = self.authenticate_user(login_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        access_token = create_access_token(
            data={"sub": user.email, "sub_id": user.id, "role": user.role}
        )
        return Token(access_token=access_token, token_type="bearer")

    def get_user(self, user_id: int) -> Optional[UserRead]:
        user = self.repo.get_by_id(user_id)
        if not user:
            return None
        return UserRead.from_orm(user)

    def list_users(self, skip: int = 0, limit: int = 100) -> List[UserRead]:
        users = self.repo.list_users(skip=skip, limit=limit)
        return [UserRead.from_orm(u) for u in users]
