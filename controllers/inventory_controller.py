from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.inventory_schema import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse
)
from services.inventory_services import create_inventory_for_product
from repositories.inventory_repository import get_by_product_id
from utils.jwt_utils import get_current_user
from utils.response_helper import success_response

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/")
def create_inventory(
    data: InventoryCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    result = create_inventory_for_product(
        db,
        data.product_id,
        data.total_stock
    )
    return success_response(
        message="Inventory created successfully",
        data=InventoryResponse.model_validate(result).model_dump(),
        status_code=201
    )


@router.get("/{product_id}")
def get_inventory(
    product_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    inventory = get_by_product_id(db, product_id)
    return success_response(
        message="Inventory retrieved successfully",
        data=InventoryResponse.model_validate(inventory).model_dump()
    )


@router.put("/{product_id}")
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

    return success_response(
        message="Inventory updated successfully",
        data=InventoryResponse.model_validate(inventory).model_dump()
    )
