import json
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.inventory_model import Inventory
from models.order_model import OrderItem
from repositories.inventory_repository import get_by_product_id
from utils.logger import logger
from utils.redis_client import redis_client   # ✅ your redis singleton


# ---------------------------------------------------------------------
# REDIS CONFIG
# ---------------------------------------------------------------------
INVENTORY_META_TTL = 60  # seconds
INVENTORY_META_KEY = "inventory:meta:{}"


# ---------------------------------------------------------------------
# INTERNAL: CACHE HELPERS (SAFE CACHE ONLY)
# ---------------------------------------------------------------------
def _get_inventory_meta(product_id: int):
    key = INVENTORY_META_KEY.format(product_id)
    data = redis_client.get(key)
    return json.loads(data) if data else None


def _set_inventory_meta(product_id: int):
    key = INVENTORY_META_KEY.format(product_id)
    redis_client.setex(
        key,
        INVENTORY_META_TTL,
        json.dumps({"product_id": product_id, "exists": True}),
    )


def _invalidate_inventory_meta(product_id: int):
    key = INVENTORY_META_KEY.format(product_id)
    redis_client.delete(key)


# ---------------------------------------------------------------------
# CREATE INVENTORY (ADMIN ONLY)
# ---------------------------------------------------------------------
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

    # cache inventory existence
    _set_inventory_meta(product_id)

    logger.info(
        "Inventory created | product_id=%s | stock=%s",
        product_id,
        stock,
    )
    return inventory


# ---------------------------------------------------------------------
# VALIDATE STOCK (NO CACHING OF QUANTITIES ❗)
# ---------------------------------------------------------------------
def validate_stock(db: Session, product_id: int, quantity: int):
    """
    Validates stock availability before order creation.
    Source of truth: DATABASE ONLY.
    """

    inventory = get_by_product_id(db, product_id)

    if not inventory:
        logger.warning(
            "Inventory not found | product_id=%s",
            product_id,
        )
        raise HTTPException(status_code=404, detail="Inventory not found")

    if inventory.available_stock < quantity:
        logger.warning(
            "Insufficient stock | product_id=%s | requested=%s | available=%s",
            product_id,
            quantity,
            inventory.available_stock,
        )
        raise HTTPException(status_code=400, detail="Insufficient stock")

    return True


# ---------------------------------------------------------------------
# RESERVE STOCK (ORDER CREATION PHASE)
# ---------------------------------------------------------------------
def reserve_stock(db: Session, product_id: int, quantity: int):
    """
    Moves stock from available -> reserved.
    Must be DB-atomic (no cache).
    """

    inventory = get_by_product_id(db, product_id)

    if not inventory:
        logger.warning("Inventory not found | product_id=%s", product_id)
        raise HTTPException(status_code=404, detail="Inventory not found")

    if inventory.available_stock < quantity:
        logger.warning(
            "Stock reservation failed | product_id=%s | requested=%s | available=%s",
            product_id,
            quantity,
            inventory.available_stock,
        )
        raise HTTPException(status_code=400, detail="Insufficient stock")

    inventory.available_stock -= quantity
    inventory.reserved_stock += quantity

    db.commit()

    logger.info(
        "Stock reserved | product_id=%s | quantity=%s",
        product_id,
        quantity,
    )

    return inventory


# ---------------------------------------------------------------------
# FINALIZE STOCK (PAYMENT SUCCESS)
# ---------------------------------------------------------------------
def finalize_stock(db: Session, order_id: int):
    """
    Deducts reserved stock permanently after successful payment.
    ORDER-LEVEL OPERATION.
    """

    items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .all()
    )

    if not items:
        logger.warning(
            "Finalize stock skipped | no items | order_id=%s",
            order_id,
        )
        return

    for item in items:
        inventory = get_by_product_id(db, item.product_id)

        if not inventory:
            logger.error(
                "Inventory missing during finalize | product_id=%s | order_id=%s",
                item.product_id,
                order_id,
            )
            continue

        inventory.reserved_stock -= item.quantity
        inventory.total_stock -= item.quantity

        logger.info(
            "Stock finalized | product_id=%s | quantity=%s | order_id=%s",
            item.product_id,
            item.quantity,
            order_id,
        )

    db.commit()


# ---------------------------------------------------------------------
# ROLLBACK STOCK (PAYMENT FAILURE / CANCELLATION)
# ---------------------------------------------------------------------
def rollback_stock(db: Session, order_id: int):
    """
    Returns reserved stock back to available stock.
    Idempotent at ORDER level using stock_rollback_done flag.
    
    Safety guarantees:
    1. Only runs once per order (idempotent via stock_rollback_done flag)
    2. Prevents negative reserved_stock (validation before update)
    3. Safe against missing inventories (logged, not fatal)
    4. Fully backward compatible with existing order status
    """

    from models.order_model import Order

    # Fetch order to check rollback state
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        logger.warning(
            "Rollback skipped | order not found | order_id=%s",
            order_id,
        )
        return

    # 🔒 IDEMPOTENCY GUARD: already rolled back?
    if order.stock_rollback_done:
        logger.info(
            "Rollback skipped | already done | order_id=%s",
            order_id,
        )
        return

    items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .all()
    )

    if not items:
        logger.warning(
            "Rollback skipped | no items | order_id=%s",
            order_id,
        )
        # Mark as done even if no items
        order.stock_rollback_done = True
        db.commit()
        return

    for item in items:
        inventory = get_by_product_id(db, item.product_id)

        if not inventory:
            logger.error(
                "Inventory missing during rollback | product_id=%s | order_id=%s",
                item.product_id,
                order_id,
            )
            continue

        # Safety check: prevent negative reserved_stock
        if inventory.reserved_stock < item.quantity:
            logger.warning(
                "Attempted negative rollback prevented | "
                "product_id=%s | order_id=%s | "
                "reserved=%s | attempt=%s",
                item.product_id,
                order_id,
                inventory.reserved_stock,
                item.quantity,
            )
            # Restore what we can
            if inventory.reserved_stock > 0:
                inventory.available_stock += inventory.reserved_stock
                inventory.reserved_stock = 0
        else:
            # Normal case: full rollback
            inventory.reserved_stock -= item.quantity
            inventory.available_stock += item.quantity

        logger.warning(
            "Stock rolled back | product_id=%s | quantity=%s | order_id=%s",
            item.product_id,
            item.quantity,
            order_id,
        )

    # Mark rollback as done (idempotency flag)
    order.stock_rollback_done = True

    db.commit()
