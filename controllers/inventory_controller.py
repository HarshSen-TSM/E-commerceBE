from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.inventory_schema import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
)
from services.inventory_services import create_inventory_for_product
from repositories.inventory_repository import get_by_product_id
from utils.jwt_utils import get_current_user
from utils.response_helper import success_response

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ---------- CREATE INVENTORY ----------
@router.post("/")
def create_inventory(
    data: InventoryCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    inventory = create_inventory_for_product(
        db,
        data.product_id,
        data.total_stock,
    )

    return success_response(
        message="Inventory created successfully",
        status_code=201,
        data=InventoryResponse.model_validate(
            inventory,
            from_attributes=True,  # 🔥 REQUIRED
        ),
    )


# ---------- GET INVENTORY ----------
@router.get("/{product_id}")
def get_inventory(
    product_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    inventory = get_by_product_id(db, product_id)

    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    return success_response(
        message="Inventory retrieved successfully",
        data=InventoryResponse.model_validate(
            inventory,
            from_attributes=True,  # 🔥 REQUIRED
        ),
    )


# ---------- UPDATE INVENTORY ----------
@router.put("/{product_id}")
def update_inventory(
    product_id: int,
    data: InventoryUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    inventory = get_by_product_id(db, product_id)

    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    # Adjust available stock correctly
    diff = data.total_stock - inventory.total_stock
    inventory.total_stock = data.total_stock
    inventory.available_stock += diff

    db.commit()
    db.refresh(inventory)

    return success_response(
        message="Inventory updated successfully",
        data=InventoryResponse.model_validate(
            inventory,
            from_attributes=True,  # 🔥 REQUIRED
        ),
    )
