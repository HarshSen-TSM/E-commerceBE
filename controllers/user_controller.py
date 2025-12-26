# user_controller.py  (or app/api/v1/users.py)

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from schemas.user_schema import UserCreate, UserRead, UserLogin, Token
from services.user_services import UserService
from utils.jwt_utils import decode_access_token
from utils.response_helper import success_response
from utils.request_context import get_current_user ,set_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# tokenUrl should match your login endpoint path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserRead:
    token_data = decode_access_token(token)
    if token_data is None or token_data.email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    service = UserService(db)
    user = service.repo.get_by_email(token_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    set_current_user(user) 
    return UserRead.from_orm(user)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service),
):
    user = service.register_user(user_in)
    return success_response(
        message="User registered successfully",
        data=user.model_dump(),
        status_code=201
    )


@router.post("/login")
def login(
    login_data: UserLogin,
    service: UserService = Depends(get_user_service),
):
    token = service.login(login_data)
    return success_response(
        message="Login successful",
        data=token
    )


@router.get("/me")
def read_me(current_user: UserRead = Depends(get_current_user)):
    return success_response(
        message="Current user profile retrieved successfully",
        data=current_user.model_dump()
    )


@router.get("/")
def list_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
    current_user: UserRead = Depends(get_current_user),  # protect if you want
):
    users = service.list_users(skip=skip, limit=limit)
    return success_response(
        message="Users retrieved successfully",
        data=[user.model_dump() for user in users]
    )
