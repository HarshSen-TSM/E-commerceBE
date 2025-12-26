# Controllers/cart_controller.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user_model import User
from schemas.cart_schema import CartRead, CartItemCreate, CartItemUpdate
from services.cart_services import CartService
from controllers.user_controller import get_current_user  # reuse your auth
from utils.response_helper import success_response

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/")
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    cart = service.get_cart_for_user(current_user.id)
    return success_response(
        message="Cart retrieved successfully",
        data=cart.model_dump()
    )


@router.post("/items")
def add_item_to_cart(
    item: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    cart = service.add_item(current_user.id, item)
    return success_response(
        message="Item added to cart successfully",
        data=cart.model_dump(),
        status_code=201
    )


@router.patch("/items/{item_id}")
def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    cart = service.update_item_quantity(current_user.id, item_id, item_update)
    return success_response(
        message="Cart item updated successfully",
        data=cart.model_dump()
    )


@router.delete("/items/{item_id}")
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    service.remove_item(current_user.id, item_id)
    return success_response(
        message="Item removed from cart successfully",
        data=None,
        status_code=204
    )


@router.delete("/")
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    service.clear_cart(current_user.id)
    return success_response(
        message="Cart cleared successfully",
        data=None,
        status_code=204
    )
