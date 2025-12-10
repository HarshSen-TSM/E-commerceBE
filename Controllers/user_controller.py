# user_controller.py  (or app/api/v1/users.py)

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from schemas.user_schema import UserCreate, UserRead, UserLogin, Token
from Services.user_services import UserService
from Utils.jwt_utils import decode_access_token

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

    return UserRead.from_orm(user)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return service.register_user(user_in)


@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    service: UserService = Depends(get_user_service),
):
    access_token = service.login(login_data)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
def read_me(current_user: UserRead = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=list[UserRead])
def list_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
    current_user: UserRead = Depends(get_current_user),  # protect if you want
):
    return service.list_users(skip=skip, limit=limit)
