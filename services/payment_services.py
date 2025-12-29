# Services/payment_services.py

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from utils.razorpay_client import razorpay_client
from utils.payment_config import RAZORPAY_KEY_ID
from utils.logger import logger

from models.order_model import Order
from models.payment_model import Payment

from schemas.payment_schema import (
    PaymentSessionCreate,
    PaymentSessionResponse,
    PaymentVerifyRequest,
    PaymentRead,
)


class PaymentService:
    def _get_db(self) -> Session:
        return SessionLocal()

    # --------------------------------------------------
    # 1) Create Razorpay payment session (IDEMPOTENT)
    # --------------------------------------------------
    def create_payment_session(
        self, user_id: int, data: PaymentSessionCreate
    ) -> PaymentSessionResponse:
        db = self._get_db()
        try:
            logger.info(
                f"Creating payment session | user_id={user_id}, order_id={data.order_id}"
            )

            # Fetch order with ownership check
            order: Order | None = (
                db.query(Order)
                .filter(Order.id == data.order_id, Order.user_id == user_id)
                .first()
            )

            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found for this user",
                )

            # 🚫 Block if order already paid
            if order.status == "PAID":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order already paid",
                )

            # 🔁 IDEMPOTENT SESSION: reuse existing PENDING payment
            existing_payment = (
                db.query(Payment)
                .filter(
                    Payment.order_id == order.id,
                    Payment.user_id == user_id,
                    Payment.status == "PENDING",
                )
                .first()
            )

            if existing_payment:
                logger.info(
                    f"[IDEMPOTENT SESSION] Reusing existing payment session | "
                    f"user_id={user_id}, order_id={order.id}, "
                    f"razorpay_order_id={existing_payment.razorpay_order_id}"
                )

                return PaymentSessionResponse(
                    razorpay_order_id=existing_payment.razorpay_order_id,
                    amount=int(Decimal(order.grand_total) * 100),
                    currency="INR",
                    key_id=RAZORPAY_KEY_ID,
                    order_id=order.id,
                )

            # Validate payable amount
            if not order.grand_total:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order has no payable amount",
                )

            amount_paise = int(Decimal(order.grand_total) * 100)

            # Create Razorpay order
            razorpay_order = razorpay_client.order.create(
                {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": f"order_{order.id}",
                    "payment_capture": 1,
                }
            )

            rp_order_id = razorpay_order["id"]

            # Create local Payment record
            payment = Payment(
                order_id=order.id,
                user_id=user_id,
                razorpay_order_id=rp_order_id,
                amount=order.grand_total,
                currency="INR",
                status="PENDING",
            )

            db.add(payment)
            db.commit()
            db.refresh(payment)

            logger.info(
                f"Payment session created | payment_id={payment.id}, "
                f"razorpay_order_id={rp_order_id}"
            )

            return PaymentSessionResponse(
                razorpay_order_id=rp_order_id,
                amount=amount_paise,
                currency="INR",
                key_id=RAZORPAY_KEY_ID,
                order_id=order.id,
            )

        finally:
            db.close()

    # --------------------------------------------------
    # 2) Verify & capture payment (IDEMPOTENT & RACE-SAFE)
    # --------------------------------------------------
    def verify_and_capture_payment(
        self, user_id: int, data: PaymentVerifyRequest
    ) -> PaymentRead:
        db = self._get_db()

        try:
            # Fetch payment session with ownership check
            payment: Payment | None = (
                db.query(Payment)
                .filter(
                    Payment.order_id == data.order_id,
                    Payment.user_id == user_id,
                    Payment.razorpay_order_id == data.razorpay_order_id,
                )
                .first()
            )

            if not payment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payment session not found",
                )

            # 🔁 IDEMPOTENCY GUARD
            if payment.status == "SUCCESS":
                logger.info(
                    f"[IDEMPOTENT VERIFY] Payment already SUCCESS | "
                    f"user_id={user_id}, order_id={payment.order_id}"
                )
                return {
                    "id": payment.id,
                    "order_id": payment.order_id,
                    "user_id": payment.user_id,
                    "status": payment.status,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                }

            # Verify Razorpay signature
            try:
                razorpay_client.utility.verify_payment_signature(
                    {
                        "razorpay_order_id": data.razorpay_order_id,
                        "razorpay_payment_id": data.razorpay_payment_id,
                        "razorpay_signature": data.razorpay_signature,
                    }
                )
            except Exception:
                payment.status = "FAILED"
                db.commit()

                logger.error(
                    f"[PAYMENT FAILED] Signature verification failed | "
                    f"user_id={user_id}, order_id={payment.order_id}"
                )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Signature verification failed",
                )

            # Mark SUCCESS (race-safe)
            try:
                payment.razorpay_payment_id = data.razorpay_payment_id
                payment.razorpay_signature = data.razorpay_signature
                payment.status = "SUCCESS"

                order = (
                    db.query(Order)
                    .filter(Order.id == payment.order_id)
                    .first()
                )

                if order and order.status != "PAID":
                    order.status = "PAID"

                db.commit()
                db.refresh(payment)

                logger.info(
                    f"[PAYMENT SUCCESS] user_id={user_id}, "
                    f"order_id={payment.order_id}, "
                    f"payment_id={payment.razorpay_payment_id}"
                )

                return {
                    "id": payment.id,
                    "order_id": payment.order_id,
                    "user_id": payment.user_id,
                    "status": payment.status,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                }

            except IntegrityError:
                # Race-condition handler (DB unique constraint)
                db.rollback()

                existing = (
                    db.query(Payment)
                    .filter(
                        Payment.order_id == data.order_id,
                        Payment.razorpay_payment_id == data.razorpay_payment_id,
                    )
                    .first()
                )

                logger.warning(
                    f"[RACE HANDLED] Duplicate verify attempt | "
                    f"user_id={user_id}, order_id={data.order_id}"
                )

                return {
                    "id": existing.id,
                    "order_id": existing.order_id,
                    "user_id": existing.user_id,
                    "status": existing.status,
                    "amount": float(existing.amount),
                    "currency": existing.currency,
                }

        finally:
            db.close()
