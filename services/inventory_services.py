from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.inventory_model import Inventory
from models.order_model import OrderItem
from repositories.inventory_repository import get_by_product_id
from utils.logger import logger


# 🔹 Create inventory entry (admin only)
def create_inventory_for_product(db: Session, product_id: int, stock: int):
    inventory = Inventory(
        product_id=product_id,
        total_stock=stock,
        available_stock=stock,
        reserved_stock=0,
    )
    db.add(inventory)
    db.commit()
    db.refresh(inventory)

    logger.info(f"Inventory created | product_id={product_id}, stock={stock}")
    return inventory


# 🔹 Validate stock before order creation
def validate_stock(db: Session, product_id: int, quantity: int):
    inventory = get_by_product_id(db, product_id)

    if not inventory or inventory.available_stock < quantity:
        logger.warning(f"Insufficient stock | product_id={product_id}")
        raise HTTPException(status_code=400, detail="Insufficient stock")

    return True


# 🔹 Reserve stock after order creation
def reserve_stock(db: Session, product_id: int, quantity: int):
    inventory = get_by_product_id(db, product_id)

    if not inventory or inventory.available_stock < quantity:
        logger.warning(f"Insufficient stock | product_id={product_id}")
        raise HTTPException(status_code=400, detail="Insufficient stock")

    inventory.available_stock -= quantity
    inventory.reserved_stock += quantity

    db.commit()

    logger.info(
        f"Stock reserved | product_id={product_id}, quantity={quantity}"
    )
    return inventory


# 🔹 Finalize stock after payment success (ORDER LEVEL)
def finalize_stock(db: Session, order_id: int):
    items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .all()
    )

    for item in items:
        inventory = get_by_product_id(db, item.product_id)

        inventory.reserved_stock -= item.quantity
        inventory.total_stock -= item.quantity

        logger.info(
            f"Stock finalized | product_id={item.product_id}, qty={item.quantity}"
        )

    db.commit()


# 🔹 Rollback stock on payment failure / order cancellation (ORDER LEVEL)
def rollback_stock(db: Session, order_id: int):
    items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .all()
    )

    if not items:
        logger.warning(f"[ROLLBACK] No items found | order_id={order_id}")
        return

    for item in items:
        inventory = get_by_product_id(db, item.product_id)

        inventory.reserved_stock -= item.quantity
        inventory.available_stock += item.quantity

        logger.warning(
            f"Stock rolled back | product_id={item.product_id}, qty={item.quantity}"
        )

    db.commit()
