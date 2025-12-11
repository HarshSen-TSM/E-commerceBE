# services/order_services.py
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

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


def _quantize_money(value: Decimal) -> Decimal:
    """Quantize monetary Decimal to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OrderService:
    """
    Service layer for Orders with defensive checks:
    - Filters out cart items with quantity <= 0
    - Eager-loads cart.items to avoid DetachedInstanceError
    - Uses optional row-level locking for product reads (with_for_update)
    - Consistent Decimal handling for monetary values
    """

    def _get_db(self) -> Session:
        return SessionLocal()

    # ---------- core: create from cart ----------
    def create_order_from_cart(
        self,
        user_id: int,
        shipping_address: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Order:
        """
        Turn the user's cart into an Order.
        Key behavior changes:
        - Items with quantity <= 0 are ignored and removed from cart.
        - If no valid items remain, return 400 "Cart is empty or has no valid items".
        - Returns the created Order with items eagerly loaded.
        """
        db = self._get_db()
        try:
            # Eager-load items to ensure they are available while the session is open
            cart: Optional[Cart] = (
                db.query(Cart)
                .options(joinedload(Cart.items))
                .filter(Cart.user_id == user_id)
                .first()
            )

            # Defensive refresh if items appear empty due to session weirdness
            if cart is not None and not getattr(cart, "items", []):
                try:
                    db.refresh(cart)
                except Exception:
                    pass  # ignore; will be treated as empty below

            if not cart:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cart not found or empty",
                )

            # FILTER OUT invalid items (quantity <= 0)
            valid_items = [it for it in getattr(cart, "items", []) if getattr(it, "quantity", 0) and int(it.quantity) > 0]

            # Optionally remove zero-quantity items from cart to keep DB clean
            zero_qty_items = [it for it in getattr(cart, "items", []) if not (getattr(it, "quantity", 0) and int(it.quantity) > 0)]
            for bad in zero_qty_items:
                try:
                    db.delete(bad)
                except Exception:
                    # ignore; we'll still proceed with removal at commit
                    pass

            # If no valid items remain, treat as empty
            if not valid_items:
                db.commit()  # commit removal of zero-qty items if any
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cart is empty or has no valid items to checkout",
                )

            subtotal = Decimal("0.00")
            total_items = 0
            discount = Decimal("0.00")  # placeholder for coupons/promos

            order = Order(
                user_id=user_id,
                shipping_address=shipping_address,
                payment_method=payment_method,
                status="PENDING",
            )
            db.add(order)
            db.flush()  # populate order.id for order_items

            # Process each valid cart item
            for cart_item in list(valid_items):
                # Lock product row when possible to avoid race conditions
                product_query = db.query(Product).filter(
                    Product.id == cart_item.product_id, Product.status == "active"
                )
                try:
                    product = product_query.with_for_update().first()
                except AttributeError:
                    product = product_query.first()

                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product {cart_item.product_id} not available or inactive",
                    )

                # Basic stock check
                if product.stock is not None and cart_item.quantity > product.stock:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for product '{product.name}' (requested {cart_item.quantity}, available {product.stock})",
                    )

                # Normalize price to Decimal
                try:
                    unit_price = Decimal(str(product.price))
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Invalid price stored for product {product.id}",
                    )

                unit_price = _quantize_money(unit_price)
                line_total = _quantize_money(unit_price * Decimal(cart_item.quantity))

                subtotal += line_total
                total_items += int(cart_item.quantity)

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=cart_item.quantity,
                    total_price=line_total,
                )
                db.add(order_item)

                # Decrement stock if tracked
                if product.stock is not None:
                    product.stock = product.stock - cart_item.quantity

            # Tax and grand total
            tax = _quantize_money(subtotal * Decimal("0.18"))
            grand_total = _quantize_money(subtotal + tax - discount)

            order.total_items = total_items
            order.subtotal = _quantize_money(subtotal)
            order.tax = tax
            order.discount = _quantize_money(discount)
            order.grand_total = grand_total

            # Remove processed items from cart (we already removed zero-qty ones earlier)
            for item in list(valid_items):
                try:
                    db.delete(item)
                except Exception:
                    pass

            db.commit()
            db.refresh(order)

            # Eager-load items before returning to avoid DetachedInstanceError
            order = (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order.id)
                .first()
            )
            return order
        except HTTPException:
            db.rollback()
            raise
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while creating order",
            )
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
                .options(joinedload(Order.items))
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
                .options(joinedload(Order.items))
                .filter(Order.id == order_id, Order.user_id == user_id)
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
                detail=f"Invalid order status '{new_status}'",
            )

        db = self._get_db()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found",
                )

            order.status = new_status
            db.commit()
            db.refresh(order)

            order = (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order_id)
                .first()
            )
            return order
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while updating order status",
            )
        finally:
            db.close()

    # ---------- attach payment ----------
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found",
                )

            if hasattr(order, "transaction_id"):
                order.transaction_id = transaction_id
            if hasattr(order, "payment_method"):
                order.payment_method = payment_method
            if hasattr(order, "payment_status"):
                order.payment_status = payment_status
            if hasattr(order, "amount_paid"):
                try:
                    order.amount_paid = _quantize_money(Decimal(str(amount)))
                except Exception:
                    order.amount_paid = None

            if payment_status and payment_status.upper() == "PAID":
                order.status = "PAID"
                if hasattr(order, "paid_at"):
                    from datetime import datetime

                    order.paid_at = datetime.utcnow()

            db.commit()
            db.refresh(order)

            order = (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order_id)
                .first()
            )
            return order
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while attaching payment",
            )
        finally:
            db.close()
