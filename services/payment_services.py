# Services/payment_services.py

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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

    # 1) Create Razorpay order session from local Order
    def create_payment_session(
        self, user_id: int, data: PaymentSessionCreate
    ) -> PaymentSessionResponse:
        db = self._get_db()
        try:
            logger.info(f"Creating payment session for user {user_id}, order {data.order_id}")
            
            order: Order | None = (
                db.query(Order)
                .filter(Order.id == data.order_id, Order.user_id == user_id)
                .first()
            )
            if not order:
                logger.error(f"Order {data.order_id} not found for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found for this user",
                )

            # you can decide what to pay: here we use grand_total
            if not order.grand_total:
                logger.error(f"Order {data.order_id} has no payable amount")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order has no payable amount",
                )

            amount_paise = int(Decimal(order.grand_total) * 100)
            logger.info(f"Order total: ₹{order.grand_total} ({amount_paise} paise)")

            razorpay_order = razorpay_client.order.create(
                {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": f"order_{order.id}",
                    "payment_capture": 1,
                }
            )

            rp_order_id = razorpay_order["id"]
            logger.info(f"Razorpay order created: {rp_order_id}")

            # create local Payment record
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
            logger.info(f"Payment record created with id {payment.id}")

            return PaymentSessionResponse(
                razorpay_order_id=rp_order_id,
                amount=amount_paise,
                currency="INR",
                key_id=RAZORPAY_KEY_ID,
                order_id=order.id,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error creating payment session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment session creation failed"
            )
        finally:
            db.close()

    # 2) Verify payment signature after frontend checkout success
    def verify_and_capture_payment(
        self, user_id: int, data: PaymentVerifyRequest
    ) -> PaymentRead:
        db = self._get_db()
        try:
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

            # verify signature
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
                logger.error(f"Payment signature verification failed, order {data.order_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Signature verification failed",
                )

            # Signature valid -> mark payment success
            payment.razorpay_payment_id = data.razorpay_payment_id
            payment.razorpay_signature = data.razorpay_signature
            payment.status = "SUCCESS"
            logger.info(f"Payment marked as SUCCESS, order {data.order_id}")

            # update order status too
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                # if your Order has payment_status, update that too
                if hasattr(order, "payment_status"):
                    order.payment_status = "PAID"
                order.status = "PAID"
                logger.info(f"Order marked as PAID, order {data.order_id}")

            db.commit()
            db.refresh(payment)

            return {
                "id": payment.id,
                "order_id": payment.order_id,
                "user_id": payment.user_id,
                "status": payment.status,
                "amount": float(payment.amount),
                "currency": payment.currency,
            }
        finally:
            db.close()
