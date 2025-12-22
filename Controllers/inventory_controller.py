from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.inventory_schema import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse
)
from Services.inventory_services import create_inventory_for_product
from Repositories.inventory_repository import get_by_product_id
from Utils.jwt_utils import get_current_user

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/", response_model=InventoryResponse)
def create_inventory(
    data: InventoryCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return create_inventory_for_product(
        db,
        data.product_id,
        data.total_stock
    )


@router.get("/{product_id}", response_model=InventoryResponse)
def get_inventory(
    product_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return get_by_product_id(db, product_id)


@router.put("/{product_id}", response_model=InventoryResponse)
def update_inventory(
    product_id: int,
    data: InventoryUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    inventory = get_by_product_id(db, product_id)

    diff = data.total_stock - inventory.total_stock
    inventory.total_stock = data.total_stock
    inventory.available_stock += diff

    db.commit()
    db.refresh(inventory)   # 🔥 REQUIRED

    return inventory
