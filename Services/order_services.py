# services/order_services.py

from decimal import Decimal
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.order_model import Order, OrderItem
from models.cart_model import Cart, CartItem
from models.product_model import Product


ALLOWED_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "PAID",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED",
}


class OrderService:
    # ---------- helpers ----------

    def _get_db(self) -> Session:
        return SessionLocal()

    # ---------- core: create from cart ----------

    def create_order_from_cart(
        self,
        user_id: int,
        shipping_address: str | None = None,
        payment_method: str | None = None,
    ) -> Order:
        db = self._get_db()
        try:
            cart: Cart | None = (
                db.query(Cart).filter(Cart.user_id == user_id).first()
            )
            if not cart or not cart.items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cart is empty",
                )

            # calculate totals and check stock
            subtotal = Decimal("0.00")
            total_items = 0
            discount = Decimal("0.00")  # plug in coupons later

            order = Order(
                user_id=user_id,
                shipping_address=shipping_address,
                payment_method=payment_method,
                status="PENDING",
            )
            db.add(order)
            db.flush()  # to get order.id

            for cart_item in cart.items:
                product: Product | None = (
                    db.query(Product)
                    .filter(
                        Product.id == cart_item.product_id,
                        Product.status == "active",
                    )
                    .first()
                )
                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product {cart_item.product_id} not available",
                    )

                # basic stock check
                if (
                    product.stock is not None
                    and cart_item.quantity > product.stock
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for {product.name}",
                    )

                unit_price = Decimal(str(product.price))
                line_total = unit_price * cart_item.quantity

                subtotal += line_total
                total_items += cart_item.quantity

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=cart_item.quantity,
                    total_price=line_total,
                )
                db.add(order_item)

                # reduce stock
                if product.stock is not None:
                    product.stock -= cart_item.quantity

            # simple tax calculation (e.g., 18%)
            tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
            grand_total = subtotal + tax - discount

            order.total_items = total_items
            order.subtotal = subtotal
            order.tax = tax
            order.discount = discount
            order.grand_total = grand_total

            # clear cart items
            for item in list(cart.items):
                db.delete(item)

            db.commit()
            db.refresh(order)
            return order
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ---------- fetch order(s) for user ----------

    def list_user_orders(self, user_id: int) -> List[Order]:
        db = self._get_db()
        try:
            return (
                db.query(Order)
                .filter(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
                .all()
            )
        finally:
            db.close()

    def get_order_for_user(self, order_id: int, user_id: int) -> Order:
        db = self._get_db()
        try:
            order = (
                db.query(Order)
                .filter(
                    Order.id == order_id,
                    Order.user_id == user_id,
                )
                .first()
            )
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found",
                )
            return order
        finally:
            db.close()

    # ---------- admin status update ----------

    def update_status(self, order_id: int, new_status: str) -> Order:
        if new_status not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid order status",
            )

        db = self._get_db()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found",
                )

            # keep transitions simple for now, you can harden later
            order.status = new_status
            db.commit()
            db.refresh(order)
            return order
        finally:
            db.close()
