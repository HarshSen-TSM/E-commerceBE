from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.user_model import User
from schemas.order_schema import OrderCreate

from utils.mappers.order_mapper import (
    map_order_list,
    map_order_detail
)

from services.order_services import OrderService
from controllers.user_controller import get_current_user
from utils.response_helper import success_response
from database import get_db

router = APIRouter(prefix="/orders", tags=["orders"])


# ================= CREATE ORDER =================
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_order_from_cart(
    body: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)

    order = service.create_order_from_cart(
        user_id=current_user.id,
        shipping_address=body.shipping_address,
        payment_method=body.payment_method,
    )

    return success_response(
        message="Order created successfully",
        data=map_order_detail(order),   # ✅ FIXED
        status_code=201
    )


# ================= LIST MY ORDERS =================
@router.get("/")
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)

    orders = service.list_user_orders(current_user.id)

    return success_response(
        message="Orders retrieved successfully",
        data=map_order_list(orders)     # ✅ FIXED
    )


# ================= GET SINGLE ORDER =================
@router.get("/{order_id}")
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)

    order = service.get_order_for_user(order_id, current_user.id)

    return success_response(
        message="Order retrieved successfully",
        data=map_order_detail(order)    # ✅ FIXED
    )


# ================= UPDATE ORDER STATUS =================
@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    service = OrderService(db)
    order = service.update_status(order_id, new_status)

    return success_response(
        message="Order status updated successfully",
        data=map_order_detail(order)    # ✅ FIXED
    )
