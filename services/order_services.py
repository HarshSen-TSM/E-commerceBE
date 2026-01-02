from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from models.order_model import Order, OrderItem
from models.cart_model import Cart
from models.product_model import Product
from models.inventory_model import Inventory
from utils.logger import logger
from utils.caching_utils import get_or_set_cache
from utils.redis_client import redis_client


ALLOWED_STATUSES = {
    "PENDING",
    "PAID",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED",
    "EXPIRED",
}


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # INTERNAL: ROLLBACK INVENTORY FOR ORDER
    # ------------------------------------------------------------------
    def _rollback_inventory(self, order: Order) -> None:
        if order.status not in {"PENDING", "CANCELLED", "EXPIRED"}:
            return

        for item in order.items:
            inventory = (
                self.db.query(Inventory)
                .filter(Inventory.product_id == item.product_id)
                .with_for_update()
                .first()
            )

            if inventory:
                inventory.available_stock += item.quantity
                inventory.reserved_stock -= item.quantity

                logger.info(
                    f"Inventory rolled back: product_id={item.product_id}, "
                    f"quantity={item.quantity}"
                )

    # ------------------------------------------------------------------
    # CREATE ORDER FROM CART (RESERVES INVENTORY)
    # ------------------------------------------------------------------
    def create_order_from_cart(
        self,
        user_id: int,
        shipping_address: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Order:

        cart = (
            self.db.query(Cart)
            .options(joinedload(Cart.items))
            .filter(Cart.user_id == user_id)
            .first()
        )

        if not cart:
            raise HTTPException(400, "Cart not found or empty")

        valid_items = [i for i in cart.items if i.quantity and i.quantity > 0]
        if not valid_items:
            raise HTTPException(400, "Cart is empty or has no valid items")

        order = Order(
            user_id=user_id,
            shipping_address=shipping_address,
            payment_method=payment_method,
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        self.db.add(order)
        self.db.flush()

        subtotal = Decimal("0.00")
        total_items = 0

        for cart_item in valid_items:
            product = (
                self.db.query(Product)
                .filter(Product.id == cart_item.product_id, Product.status == "active")
                .first()
            )

            if not product:
                raise HTTPException(400, "Product not available")

            inventory = (
                self.db.query(Inventory)
                .filter(Inventory.product_id == product.id)
                .with_for_update()
                .first()
            )

            if inventory.available_stock < cart_item.quantity:
                raise HTTPException(400, "Insufficient stock")

            inventory.available_stock -= cart_item.quantity
            inventory.reserved_stock += cart_item.quantity

            unit_price = _quantize_money(Decimal(str(product.price)))
            line_total = _quantize_money(unit_price * Decimal(cart_item.quantity))

            subtotal += line_total
            total_items += cart_item.quantity

            self.db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=cart_item.quantity,
                    total_price=line_total,
                )
            )

        order.total_items = total_items
        order.subtotal = subtotal
        order.tax = _quantize_money(subtotal * Decimal("0.18"))
        order.discount = Decimal("0.00")
        order.grand_total = _quantize_money(order.subtotal + order.tax)

        for item in valid_items:
            self.db.delete(item)

        self.db.commit()
        self.db.refresh(order)

        # 🔴 INVALIDATE ORDER LIST CACHE
        redis_client.delete(f"user_orders:{user_id}")

        return order

    # ------------------------------------------------------------------
    # LIST USER ORDERS (CACHED)
    # ------------------------------------------------------------------
    def list_user_orders(self, user_id: int) -> List[Order]:
        cache_key = f"user_orders:{user_id}"

        def fetch_from_db():
            orders = (
                self.db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
                .all()
            )
            return [order.to_dict() for order in orders]

        data = get_or_set_cache(
            key=cache_key,
            ttl=180,  # 🔴 SHORT TTL
            fetch_fn=fetch_from_db,
        )

        return [
            Order(**order_dict) for order_dict in data
        ]

    # ------------------------------------------------------------------
    # UPDATE ORDER STATUS (ROLLBACK + INVALIDATE CACHE)
    # ------------------------------------------------------------------
    def update_status(self, order_id: int, new_status: str) -> Order:
        order = (
            self.db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
            .first()
        )

        if not order:
            raise HTTPException(404, "Order not found")

        if new_status in {"CANCELLED", "EXPIRED"}:
            self._rollback_inventory(order)

        order.status = new_status
        self.db.commit()
        self.db.refresh(order)

        # 🔴 INVALIDATE ORDER LIST CACHE
        redis_client.delete(f"user_orders:{order.user_id}")

        return order

    # ------------------------------------------------------------------
    # ATTACH PAYMENT (FINALIZE / ROLLBACK + INVALIDATE CACHE)
    # ------------------------------------------------------------------
    def attach_payment(
        self,
        order_id: int,
        transaction_id: str,
        payment_method: str,
        amount: Decimal,
        payment_status: str,
    ) -> Order:

        order = (
            self.db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
            .first()
        )

        if not order:
            raise HTTPException(404, "Order not found")

        order.transaction_id = transaction_id
        order.payment_method = payment_method
        order.payment_status = payment_status
        order.amount_paid = _quantize_money(amount)

        if payment_status.upper() == "PAID":
            order.status = "PAID"
        else:
            self._rollback_inventory(order)
            order.status = "CANCELLED"

        self.db.commit()
        self.db.refresh(order)

        # 🔴 INVALIDATE ORDER LIST CACHE
        redis_client.delete(f"user_orders:{order.user_id}")

        return order
