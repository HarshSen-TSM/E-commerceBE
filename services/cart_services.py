# Services/cart_services.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from repositories.cart_repository import CartRepository
from schemas.cart_schema import (
    CartItemCreate,
    CartItemUpdate,
    CartRead,
    CartItemRead,
    CartSummary,
)
from models.cart_model import Cart
from utils.logger import logger


class CartService:
    TAX_RATE = 0.0
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

    # ---------- GET CART ----------
    def get_cart_for_user(self, user_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        return self._build_cart_response(cart)

    # ---------- ADD ITEM ----------
    def add_item(self, user_id: int, data: CartItemCreate) -> CartRead:
        cart = self._get_or_create_cart(user_id)

        product = self.repo.get_product(data.product_id)
        if not product:
            logger.warning(f"Product not found: product_id={data.product_id}")
            raise HTTPException(status_code=404, detail="Product not found")

        if product.status != "active":
            logger.warning(f"Inactive product: product_id={data.product_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Product not active (status={product.status})",
            )

        if product.stock is not None and data.quantity > product.stock:
            logger.warning(f"Insufficient stock: product_id={data.product_id}")
            raise HTTPException(status_code=400, detail="Not enough stock")

        self.repo.add_item(cart, product, data.quantity)

        logger.info(
            f"Item added to cart: product_id={data.product_id}, quantity={data.quantity}"
        )

        return self._build_cart_response(cart)

    # ---------- UPDATE ITEM ----------
    def update_item_quantity(
        self, user_id: int, item_id: int, data: CartItemUpdate
    ) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        item = self.repo.get_item_by_id(item_id, cart.id)

        if not item:
            logger.warning(f"Cart item not found: item_id={item_id}")
            raise HTTPException(status_code=404, detail="Cart item not found")

        product = item.product
        if product.stock is not None and data.quantity > product.stock:
            logger.warning(f"Insufficient stock: product_id={product.id}")
            raise HTTPException(status_code=400, detail="Not enough stock")

        self.repo.update_item_quantity(item, data.quantity)

        logger.info(
            f"Cart item quantity updated: item_id={item_id}, quantity={data.quantity}"
        )

        return self._build_cart_response(cart)

    # ---------- REMOVE ITEM ----------
    def remove_item(self, user_id: int, item_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        item = self.repo.get_item_by_id(item_id, cart.id)

        if not item:
            logger.warning(f"Cart item not found for removal: item_id={item_id}")
            raise HTTPException(status_code=404, detail="Cart item not found")

        self.repo.remove_item(item)

        logger.info(f"Cart item removed: item_id={item_id}")

        return self._build_cart_response(cart)

    # ---------- CLEAR CART ----------
    def clear_cart(self, user_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        self.repo.clear_cart(cart)

        logger.info("Cart cleared")

        self.db.refresh(cart)
        return self._build_cart_response(cart)
