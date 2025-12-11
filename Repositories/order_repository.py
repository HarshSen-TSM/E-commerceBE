# repositories/order_repository.py

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update

from database import SessionLocal
from models.order_model import Order, OrderItem


class OrderRepository:
    """
    Repository for Order related DB operations.
    - Uses SessionLocal() to create per-call sessions.
    - Eager-loads items to prevent DetachedInstanceError when returning objects.
    """

    def _get_db(self) -> Session:
        return SessionLocal()

    def create_order(
        self,
        user_id: int,
        shipping_address: Optional[str],
        payment_method: Optional[str],
        status: str = "PENDING",
        items: Optional[List[Dict[str, Any]]] = None,  # items: dicts with product_id, product_name, unit_price, quantity, total_price
    ) -> Order:
        db = self._get_db()
        try:
            order = Order(
                user_id=user_id,
                shipping_address=shipping_address,
                payment_method=payment_method,
                status=status,
            )
            db.add(order)
            db.flush()  # get order.id

            items = items or []
            for it in items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=it["product_id"],
                    product_name=it.get("product_name"),
                    unit_price=it["unit_price"],
                    quantity=it["quantity"],
                    total_price=it["total_price"],
                )
                db.add(order_item)

            # Commit and refresh; eager-load items before returning
            db.commit()
            db.refresh(order)
            # re-query with joinedload to ensure items are loaded and attached to session
            order = (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order.id)
                .first()
            )
            return order
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_order(self, order_id: int, user_id: Optional[int] = None) -> Optional[Order]:
        db = self._get_db()
        try:
            q = db.query(Order).options(joinedload(Order.items)).filter(Order.id == order_id)
            if user_id is not None:
                q = q.filter(Order.user_id == user_id)
            return q.first()
        finally:
            db.close()

    def list_user_orders(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Order]:
        db = self._get_db()
        try:
            return (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
        finally:
            db.close()

    def list_orders(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Order]:
        """
        Admin-style listing with optional filters like status, date range, user_id.
        """
        db = self._get_db()
        try:
            q = db.query(Order).options(joinedload(Order.items))
            filters = filters or {}
            if "status" in filters:
                q = q.filter(Order.status == filters["status"])
            if "user_id" in filters:
                q = q.filter(Order.user_id == filters["user_id"])
            if "min_date" in filters:
                q = q.filter(Order.created_at >= filters["min_date"])
            if "max_date" in filters:
                q = q.filter(Order.created_at <= filters["max_date"])

            return q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
        finally:
            db.close()

    def update_status(self, order_id: int, new_status: str) -> Optional[Order]:
        db = self._get_db()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
            order.status = new_status
            db.commit()
            db.refresh(order)
            # make sure items are loaded
            order = (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order_id)
                .first()
            )
            return order
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def attach_payment(
        self,
        order_id: int,
        transaction_id: str,
        payment_method: str,
        amount: float,
        payment_status: str,
    ) -> Optional[Order]:
        """
        Simple helper to attach payment info to an order.
        Assumes Order has fields: transaction_id, payment_method, payment_status, paid_at (optional).
        If your Order model differs, adapt field names accordingly.
        """
        db = self._get_db()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None

            # set payment fields if present on model
            if hasattr(order, "transaction_id"):
                order.transaction_id = transaction_id
            if hasattr(order, "payment_method"):
                order.payment_method = payment_method
            if hasattr(order, "payment_status"):
                order.payment_status = payment_status
            if hasattr(order, "amount_paid"):
                order.amount_paid = amount
            # Optionally update order status when payment is successful:
            # if payment_status == "PAID": order.status = "PAID"

            db.commit()
            db.refresh(order)
            order = (
                db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.id == order_id)
                .first()
            )
            return order
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
