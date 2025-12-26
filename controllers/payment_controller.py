# Controllers/payment_controller.py

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer

from services.payment_services import PaymentService
from schemas.payment_schema import (
    PaymentSessionCreate,
    PaymentSessionResponse,
    PaymentVerifyRequest,
    PaymentRead,
)
from utils.jwt_utils import decode_access_token  # or your security.py
from schemas.user_schema import TokenData
from utils.response_helper import success_response

router = APIRouter(prefix="/payments", tags=["Payments"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")  # adjust if different
service = PaymentService()


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    token_data: TokenData | None = decode_access_token(token)
    if not token_data or not token_data.user_id:
        # adapt to your TokenData
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return token_data.user_id


@router.post("/create-session", status_code=status.HTTP_201_CREATED)
def create_payment_session(
    payload: PaymentSessionCreate,
    current_user_id: int = Depends(get_current_user_id),
):
    session = service.create_payment_session(current_user_id, payload)
    return success_response(
        message="Payment session created successfully",
        data=session.model_dump(),
        status_code=201
    )


@router.post("/verify", status_code=status.HTTP_200_OK)
def verify_payment(
    payload: PaymentVerifyRequest,
    current_user_id: int = Depends(get_current_user_id),
):
    payment = service.verify_and_capture_payment(current_user_id, payload)
    return success_response(
        message="Payment verified successfully",
        data=PaymentRead.model_validate(payment).model_dump()
    )
