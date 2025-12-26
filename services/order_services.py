from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from models.order_model import Order, OrderItem
from models.cart_model import Cart
from models.product_model import Product
from models.inventory_model import Inventory
from utils.logger import logger


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
    def __init__(self, db: Session):
        self.db = db

    # ---------- CREATE ORDER FROM CART ----------
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
            logger.warning("Cart not found or empty")
            raise HTTPException(400, "Cart not found or empty")

        valid_items = [item for item in cart.items if item.quantity and item.quantity > 0]

        if not valid_items:
            logger.warning("Cart has no valid items")
            raise HTTPException(400, "Cart is empty or has no valid items")

        order = Order(
            user_id=user_id,
            shipping_address=shipping_address,
            payment_method=payment_method,
            status="PENDING",
        )
        self.db.add(order)
        self.db.flush()

        subtotal = Decimal("0.00")
        total_items = 0
        discount = Decimal("0.00")

        for cart_item in valid_items:
            product = (
                self.db.query(Product)
                .filter(Product.id == cart_item.product_id, Product.status == "active")
                .first()
            )

            if not product:
                logger.warning(f"Product not available: product_id={cart_item.product_id}")
                raise HTTPException(400, "Product not available")

            inventory = (
                self.db.query(Inventory)
                .filter(Inventory.product_id == product.id)
                .with_for_update()
                .first()
            )

            if not inventory:
                logger.error(f"Inventory missing for product_id={product.id}")
                raise HTTPException(400, "Inventory not found")

            if inventory.available_stock < cart_item.quantity:
                logger.warning(f"Insufficient stock: product_id={product.id}")
                raise HTTPException(400, "Insufficient stock")

            inventory.available_stock -= cart_item.quantity
            inventory.reserved_stock += cart_item.quantity
            logger.info(
                f"Inventory reserved: product_id={product.id}, quantity={cart_item.quantity}"
            )

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

        tax = _quantize_money(subtotal * Decimal("0.18"))
        grand_total = _quantize_money(subtotal + tax - discount)

        order.total_items = total_items
        order.subtotal = _quantize_money(subtotal)
        order.tax = tax
        order.discount = _quantize_money(discount)
        order.grand_total = grand_total

        for item in valid_items:
            self.db.delete(item)

        self.db.commit()
        logger.info(f"Order created successfully: order_id={order.id}")
        self.db.refresh(order)

        return (
            self.db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order.id)
            .first()
        )

    # ---------- LIST USER ORDERS ----------
    def list_user_orders(self, user_id: int) -> List[Order]:
        return (
            self.db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    # ---------- GET SINGLE ORDER ----------
    def get_order_for_user(self, order_id: int, user_id: int) -> Order:
        order = (
            self.db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
            .first()
        )

        if not order:
            logger.warning(f"Order not found: order_id={order_id}")
            raise HTTPException(404, "Order not found")

        if order.user_id != user_id:
            logger.warning(f"Unauthorized access attempt: order_id={order_id}")
            raise HTTPException(403, "Not authorized to access this order")

        return order

    # ---------- UPDATE ORDER STATUS ----------
    def update_status(self, order_id: int, new_status: str) -> Order:
        if new_status not in ALLOWED_STATUSES:
            logger.warning(f"Invalid order status: {new_status}")
            raise HTTPException(400, f"Invalid order status '{new_status}'")

        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            logger.warning(f"Order not found for status update: order_id={order_id}")
            raise HTTPException(404, "Order not found")

        order.status = new_status
        self.db.commit()
        self.db.refresh(order)

        logger.info(f"Order status updated: order_id={order_id}, status={new_status}")
        return order

    # ---------- ATTACH PAYMENT ----------
    def attach_payment(
        self,
        order_id: int,
        transaction_id: str,
        payment_method: str,
        amount: Decimal,
        payment_status: str,
    ) -> Order:

        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            logger.warning(f"Order not found for payment: order_id={order_id}")
            raise HTTPException(404, "Order not found")

        order.transaction_id = transaction_id
        order.payment_method = payment_method
        order.payment_status = payment_status
        order.amount_paid = _quantize_money(amount)

        if payment_status.upper() == "PAID":
            order.status = "PAID"
            logger.info(f"Order marked as PAID: order_id={order_id}")

        self.db.commit()
        self.db.refresh(order)
        return order
