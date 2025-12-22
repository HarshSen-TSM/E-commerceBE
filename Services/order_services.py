# services/order_services.py
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from models.order_model import Order, OrderItem
from models.cart_model import Cart
from models.product_model import Product
from models.inventory_model import Inventory   # ✅ IMPORTANT

ALLOWED_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "PAID",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED",
}


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OrderService:

    def _get_db(self) -> Session:
        return SessionLocal()

    # ---------- CREATE ORDER FROM CART ----------
    def create_order_from_cart(
        self,
        user_id: int,
        shipping_address: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Order:

        db = self._get_db()
        try:
            # Load cart with items
            cart = (
                db.query(Cart)
                .options(joinedload(Cart.items))
                .filter(Cart.user_id == user_id)
                .first()
            )

            if not cart:
                raise HTTPException(
                    status_code=400,
                    detail="Cart not found or empty",
                )

            valid_items = [item for item in cart.items if item.quantity and item.quantity > 0]

            if not valid_items:
                raise HTTPException(
                    status_code=400,
                    detail="Cart is empty or has no valid items to checkout",
                )

            order = Order(
                user_id=user_id,
                shipping_address=shipping_address,
                payment_method=payment_method,
                status="PENDING",
            )
            db.add(order)
            db.flush()  # get order.id

            subtotal = Decimal("0.00")
            total_items = 0
            discount = Decimal("0.00")

            # ---- PROCESS CART ITEMS ----
            for cart_item in valid_items:

                # Product (catalog only)
                product = (
                    db.query(Product)
                    .filter(Product.id == cart_item.product_id, Product.status == "active")
                    .first()
                )

                if not product:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Product {cart_item.product_id} not available",
                    )

                # Inventory (transactional)
                inventory = (
                    db.query(Inventory)
                    .filter(Inventory.product_id == product.id)
                    .with_for_update()
                    .first()
                )

                if not inventory:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Inventory not found for product '{product.name}'",
                    )

                if inventory.available_stock < cart_item.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient stock for product '{product.name}'",
                    )

                # ✅ RESERVE STOCK
                inventory.available_stock -= cart_item.quantity
                inventory.reserved_stock += cart_item.quantity

                unit_price = _quantize_money(Decimal(str(product.price)))
                line_total = _quantize_money(unit_price * Decimal(cart_item.quantity))

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

            # Totals
            tax = _quantize_money(subtotal * Decimal("0.18"))
            grand_total = _quantize_money(subtotal + tax - discount)

            order.total_items = total_items
            order.subtotal = _quantize_money(subtotal)
            order.tax = tax
            order.discount = _quantize_money(discount)
            order.grand_total = grand_total

            # Clear cart
            for item in valid_items:
                db.delete(item)

            db.commit()
            db.refresh(order)

            return (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order.id)
                .first()
            )

        except HTTPException:
            db.rollback()
            raise
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database error while creating order",
            )
        finally:
            db.close()

    # ---------- LIST USER ORDERS ----------
    def list_user_orders(self, user_id: int) -> List[Order]:
        db = self._get_db()
        try:
            return (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
                .all()
            )
        finally:
            db.close()

    # ---------- GET SINGLE ORDER ----------
    def get_order_for_user(self, order_id: int, user_id: int) -> Order:
        db = self._get_db()
        try:
            order = (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order_id, Order.user_id == user_id)
                .first()
            )
            if not order:
                raise HTTPException(404, "Order not found")
            return order
        finally:
            db.close()

    # ---------- UPDATE ORDER STATUS ----------
    def update_status(self, order_id: int, new_status: str) -> Order:
        if new_status not in ALLOWED_STATUSES:
            raise HTTPException(400, f"Invalid order status '{new_status}'")

        db = self._get_db()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(404, "Order not found")

            order.status = new_status
            db.commit()
            db.refresh(order)
            return order
        finally:
            db.close()

    # ---------- ATTACH PAYMENT ----------
    def attach_payment(
        self,
        order_id: int,
        transaction_id: str,
        payment_method: str,
        amount: Decimal,
        payment_status: str,
    ) -> Order:

        db = self._get_db()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(404, "Order not found")

            order.transaction_id = transaction_id
            order.payment_method = payment_method
            order.payment_status = payment_status
            order.amount_paid = _quantize_money(amount)

            if payment_status.upper() == "PAID":
                order.status = "PAID"

            db.commit()
            db.refresh(order)
            return order
        finally:
            db.close()
