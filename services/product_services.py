# Services/product_services.py

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.product_model import Product
from schemas.product_schema import ProductCreate, ProductUpdate, ProductRead, VALID_PRODUCT_STATUSES
from repositories import product_repository


class ProductService:
    # Allowed product statuses
    ALLOWED_STATUSES = {"active", "inactive", "deleted"}
    
    @staticmethod
    def _validate_status(status_value: Optional[str]) -> None:
        """Validate that status is one of the allowed values. Raises HTTPException if invalid."""
        if status_value is not None and status_value not in ProductService.ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{status_value}'. Allowed values: {', '.join(sorted(ProductService.ALLOWED_STATUSES))}"
            )
    def __init__(self, db: Session):
        self.db = db

    # ----- Public listing -----
    def list_products(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> List[ProductRead]:
        products = product_repository.list_products(
            self.db,
            skip=skip,
            limit=limit,
            search=search,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
        )
        return [ProductRead.model_validate(p) for p in products]

    def get_product(self, product_id: int) -> ProductRead:
        product = product_repository.get_product(self.db, product_id)
        if not product:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return ProductRead.model_validate(product)

    # ----- Admin operations -----
    def create_product(self, product_in: ProductCreate) -> ProductRead:
        self._validate_status(product_in.status)
        product = product_repository.create_product(self.db, product_in)
        return ProductRead.model_validate(product)

    def update_product(self, product_id: int, product_in: ProductUpdate) -> ProductRead:
        self._validate_status(product_in.status)
        product = product_repository.get_product(self.db, product_id)
        if not product:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        product = product_repository.update_product(self.db, product, product_in)
        return ProductRead.model_validate(product)

    def delete_product(self, product_id: int) -> ProductRead:
        product = product_repository.get_product(self.db, product_id)
        if not product:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        product = product_repository.soft_delete_product(self.db, product)
        return ProductRead.model_validate(product)
