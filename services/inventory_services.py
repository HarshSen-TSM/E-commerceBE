from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.inventory_model import Inventory
from repositories.inventory_repository import get_by_product_id
from utils.logger import logger

# 🔹 Create inventory entry (admin only)
def create_inventory_for_product(db: Session, product_id: int, stock: int):
    inventory = Inventory(
        product_id=product_id,
        total_stock=stock,
        available_stock=stock,
        reserved_stock=0
    )
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    logger.info(f"Inventory created for product {product_id}, stock {stock}")
    return inventory


# 🔹 Validate stock before order/payment
def validate_stock(db: Session, product_id: int, quantity: int):
    inventory = get_by_product_id(db, product_id)

    if not inventory or inventory.available_stock < quantity: 
        logger.warning(f"Insufficient stock for product {product_id}")
        raise HTTPException(status_code=400, detail="Insufficient stock")

    return True


# 🔹 Reserve stock after order creation
def reserve_stock(db: Session, product_id: int, quantity: int):
    inventory = get_by_product_id(db, product_id)

    if logger.warning(f"Insufficient stock for product {product_id}"):
        raise HTTPException(status_code=400, detail="Insufficient stock")

    inventory.available_stock -= quantity
    inventory.reserved_stock += quantity
    logger.info(f"Inventory reserved for product {product_id}, quantity {quantity}")
    inventory.reserved_stock += quantity

    db.commit()
    return inventory


# 🔹 Deduct stock permanently after payment success
def finalize_stock(db: Session, product_id: int, quantity: int):
    inventory = get_by_product_id(db, product_id)

    logger.info(f"Inventory finalized for product {product_id}, quantity {quantity}")
    inventory.reserved_stock -= quantity
    inventory.total_stock -= quantity

    db.commit()
    return inventory


# 🔹 Rollback stock (payment failed / order cancelled)
def rollback_stock(db: Session, product_id: int, quantity: int):
    inventory = get_by_product_id(db, product_id)
    logger.warning(f"Inventory rolled back for product {product_id}, quantity {quantity}")

    inventory.reserved_stock -= quantity
    inventory.available_stock += quantity

    db.commit()
    return inventory
