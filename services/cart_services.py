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
from utils.caching_utils import get_or_set_cache
from utils.redis_client import redis_client


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

    # ------------------------------------------------------------------
    # GET CART (CACHED — SHORT TTL)
    # ------------------------------------------------------------------
    def get_cart_for_user(self, user_id: int) -> CartRead:
        cache_key = f"cart:{user_id}"

        def fetch_from_db():
            cart = self._get_or_create_cart(user_id)
            return self._build_cart_response(cart).model_dump()

        data = get_or_set_cache(
            key=cache_key,
            ttl=60,  # 🔴 SHORT TTL (1 minute)
            fetch_fn=fetch_from_db,
        )

        return CartRead.model_validate(data)

    # ------------------------------------------------------------------
    # ADD ITEM (INVALIDATE CACHE)
    # ------------------------------------------------------------------
    def add_item(self, user_id: int, data: CartItemCreate) -> CartRead:
        cart = self._get_or_create_cart(user_id)

        product = self.repo.get_product(data.product_id)
        if not product:
            logger.warning(f"Product not found: product_id={data.product_id}")
            raise HTTPException(status_code=404, detail="Product not found")

        if product.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Product not active (status={product.status})",
            )

        if product.stock is not None and data.quantity > product.stock:
            raise HTTPException(status_code=400, detail="Not enough stock")

        self.repo.add_item(cart, product, data.quantity)

        # 🔴 INVALIDATE CACHE
        redis_client.delete(f"cart:{user_id}")

        return self._build_cart_response(cart)

    # ------------------------------------------------------------------
    # UPDATE ITEM (INVALIDATE CACHE)
    # ------------------------------------------------------------------
    def update_item_quantity(
        self, user_id: int, item_id: int, data: CartItemUpdate
    ) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        item = self.repo.get_item_by_id(item_id, cart.id)

        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        product = item.product
        if product.stock is not None and data.quantity > product.stock:
            raise HTTPException(status_code=400, detail="Not enough stock")

        self.repo.update_item_quantity(item, data.quantity)

        # 🔴 INVALIDATE CACHE
        redis_client.delete(f"cart:{user_id}")

        return self._build_cart_response(cart)

    # ------------------------------------------------------------------
    # REMOVE ITEM (INVALIDATE CACHE)
    # ------------------------------------------------------------------
    def remove_item(self, user_id: int, item_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        item = self.repo.get_item_by_id(item_id, cart.id)

        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        self.repo.remove_item(item)

        # 🔴 INVALIDATE CACHE
        redis_client.delete(f"cart:{user_id}")

        return self._build_cart_response(cart)

    # ------------------------------------------------------------------
    # CLEAR CART (INVALIDATE CACHE)
    # ------------------------------------------------------------------
    def clear_cart(self, user_id: int) -> CartRead:
        cart = self._get_or_create_cart(user_id)
        self.repo.clear_cart(cart)

        # 🔴 INVALIDATE CACHE
        redis_client.delete(f"cart:{user_id}")

        self.db.refresh(cart)
        return self._build_cart_response(cart)
