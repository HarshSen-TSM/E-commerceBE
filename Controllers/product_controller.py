# Controllers/product_controller.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from Services.product_services import ProductService
from schemas.product_schema import ProductCreate, ProductUpdate, ProductRead
from schemas.user_schema import UserRead

# Reuse your existing auth dependency
from Controllers.user_controller import get_current_user  # adjust import if needed

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

@router.get("/", response_model=List[ProductRead])
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
    return service.list_products(
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
    )


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    return service.get_product(product_id)


# ----- Admin endpoints (protected) -----

@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_admin: UserRead = Depends(get_current_admin_user),
):
    service = ProductService(db)
    return service.create_product(product_in)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_admin: UserRead = Depends(get_current_admin_user),
):
    service = ProductService(db)
    return service.update_product(product_id, product_in)


@router.delete("/{product_id}", response_model=ProductRead)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: UserRead = Depends(get_current_admin_user),
):
    service = ProductService(db)
    return service.delete_product(product_id)
