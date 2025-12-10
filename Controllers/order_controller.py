# Controllers/order_controller.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from models.user_model import User  # adjust to your actual path
from schemas.order_schema import OrderRead, OrderCreate
from Services.order_services import OrderService
from Controllers.user_controller import get_current_user  # reuse auth dep


router = APIRouter(prefix="/orders", tags=["orders"])

service = OrderService()


@router.post(
    "/",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_order_from_cart(
    body: OrderCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Turn current user's cart into an order and clear cart.
    """
    return service.create_order_from_cart(
        user_id=current_user.id,
        shipping_address=body.shipping_address,
        payment_method=body.payment_method,
    )


@router.get(
    "/",
    response_model=List[OrderRead],
)
def list_my_orders(
    current_user: User = Depends(get_current_user),
):
    return service.list_user_orders(current_user.id)


@router.get(
    "/{order_id}",
    response_model=OrderRead,
)
def get_my_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
):
    return service.get_order_for_user(order_id, current_user.id)


@router.patch(
    "/{order_id}/status",
    response_model=OrderRead,
)
def update_order_status(
    order_id: int,
    new_status: str,
    current_user: User = Depends(get_current_user),
):
    """
    Simple admin-only status update.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return service.update_status(order_id, new_status)
