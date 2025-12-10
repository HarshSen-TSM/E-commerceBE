# Controllers/cart_controller.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user_model import User
from schemas.cart_schema import CartRead, CartItemCreate, CartItemUpdate
from Services.cart_services import CartService
from Controllers.user_controller import get_current_user  # reuse your auth

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartRead)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    return service.get_cart_for_user(current_user.id)


@router.post("/items", response_model=CartRead)
def add_item_to_cart(
    item: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    return service.add_item(current_user.id, item)


@router.patch("/items/{item_id}", response_model=CartRead)
def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    return service.update_item_quantity(current_user.id, item_id, item_update)


@router.delete("/items/{item_id}", response_model=CartRead)
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    return service.remove_item(current_user.id, item_id)


@router.delete("/", response_model=CartRead)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CartService(db)
    return service.clear_cart(current_user.id)
