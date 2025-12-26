# Controllers/product_controller.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from services.product_services import ProductService
from schemas.product_schema import ProductCreate, ProductUpdate, ProductRead
from schemas.user_schema import UserRead
from utils.response_helper import success_response

# Reuse your existing auth dependency
from controllers.user_controller import get_current_user  # adjust import if needed

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# ----- helper: admin check -----

def get_current_admin_user(
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    if current_user.role not in ("admin", "staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


# ----- Public / user-facing endpoints -----

@router.get("/")
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    products = service.list_products(
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
    )
    return success_response(
        message="Products retrieved successfully",
        data=[ProductRead.model_validate(p).model_dump() for p in products]
    )


@router.get("/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    product = service.get_product(product_id)
    return success_response(
        message="Product retrieved successfully",
        data=product.model_dump()
    )


# ----- Admin endpoints (protected) -----

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_admin: UserRead = Depends(get_current_admin_user),
):
    service = ProductService(db)
    product = service.create_product(product_in)
    return success_response(
        message="Product created successfully",
        data=product.model_dump(),
        status_code=201
    )


@router.put("/{product_id}")
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_admin: UserRead = Depends(get_current_admin_user),
):
    service = ProductService(db)
    product = service.update_product(product_id, product_in)
    return success_response(
        message="Product updated successfully",
        data=product.model_dump()
    )


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: UserRead = Depends(get_current_admin_user),
):
    service = ProductService(db)
    service.delete_product(product_id)
    return success_response(
        message="Product deleted successfully",
        data=None,
        status_code=204
    )
