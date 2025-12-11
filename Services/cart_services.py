# Services/cart_services.py

from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from Repositories.cart_repository import CartRepository
from schemas.cart_schema import (
    CartItemCreate,
    CartItemUpdate,
    CartRead,
    CartItemRead,
    CartSummary,
)
from models.cart_model import Cart


class CartService:
    TAX_RATE = 0.0    # change if you want
    DISCOUNT_RATE = 0.0

    def __init__(self, db: Session):
        self.db = db
        self.repo = CartRepository(db)

    def _get_or_create_cart(self, user_id: int) -> Cart:
        cart = self.repo.get_cart_by_user_id(user_id)
        if not cart:
            cart = self.repo.create_cart_for_user(user_id)
        return cart

    def _build_cart_response(self, cart: Cart) -> CartRead:
        subtotal = sum(item.unit_price * item.quantity for item in cart.items)
        tax = subtotal * self.TAX_RATE
        discount = subtotal * self.DISCOUNT_RATE
        total = subtotal + tax - discount

        items_read = [
            CartItemRead.model_validate(item, from_attributes=True)
            for item in cart.items
        ]

        summary = CartSummary(
            subtotal=subtotal,
            tax=tax,
            discount=discount,
            total=total,
        )

        return CartRead(
            id=cart.id,
            items=items_read,
            summary=summary,
        )

    def get_cart_for_user(self, user_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        return self._build_cart_response(cart)

    def add_item(self, user_id: int, data: CartItemCreate) -> CartRead:
        cart = self._get_or_create_cart(user_id)

        product = self.repo.get_product(data.product_id)
        # More specific errors help clients and debugging:
        if not product:
            # product id does not exist in the DB
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        if product.status != "active":
            # product exists but isn't available for sale
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product not active (status={product.status})",
            )


        # basic stock check
        if product.stock is not None and data.quantity > product.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough stock",
            )

        self.repo.add_item(cart, product, data.quantity)
        # (you could also reduce stock here if you want)
        return self._build_cart_response(cart)

    def update_item_quantity(
        self, user_id: int, item_id: int, data: CartItemUpdate
    ) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        item = self.repo.get_item_by_id(item_id, cart.id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found",
            )

        product = item.product
        if product.stock is not None and data.quantity > product.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough stock",
            )

        self.repo.update_item_quantity(item, data.quantity)
        return self._build_cart_response(cart)

    def remove_item(self, user_id: int, item_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        item = self.repo.get_item_by_id(item_id, cart.id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found",
            )
        self.repo.remove_item(item)
        return self._build_cart_response(cart)

    def clear_cart(self, user_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        self.repo.clear_cart(cart)
        self.db.refresh(cart)
        return self._build_cart_response(cart)
