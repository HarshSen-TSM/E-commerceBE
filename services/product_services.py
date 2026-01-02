# Services/product_services.py

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.product_model import Product
from schemas.product_schema import (
    ProductCreate,
    ProductUpdate,
    ProductRead,
    VALID_PRODUCT_STATUSES,
)
from repositories import product_repository
from utils.caching_utils import get_or_set_cache
from utils.redis_client import redis_client


class ProductService:
    # Allowed product statuses
    ALLOWED_STATUSES = {"active", "inactive", "deleted"}

    @staticmethod
    def _validate_status(status_value: Optional[str]) -> None:
        """Validate that status is one of the allowed values."""
        if status_value is not None and status_value not in ProductService.ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status '{status_value}'. "
                    f"Allowed values: {', '.join(sorted(ProductService.ALLOWED_STATUSES))}"
                ),
            )

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # PUBLIC LISTING (CACHED)
    # ------------------------------------------------------------------
    def list_products(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> List[ProductRead]:

        # Build deterministic cache key (filters + pagination)
        cache_key = (
            "product:list:"
            f"skip={skip}:"
            f"limit={limit}:"
            f"search={search or 'none'}:"
            f"category={category_id or 'none'}:"
            f"min={min_price or 'none'}:"
            f"max={max_price or 'none'}"
        )

        def fetch_from_db():
            products = product_repository.list_products(
                self.db,
                skip=skip,
                limit=limit,
                search=search,
                category_id=category_id,
                min_price=min_price,
                max_price=max_price,
            )
            # Serialize for Redis
            return [ProductRead.model_validate(p).model_dump() for p in products]

        data = get_or_set_cache(
            key=cache_key,
            ttl=300,  # 5 minutes
            fetch_fn=fetch_from_db,
        )

        return [ProductRead.model_validate(p) for p in data]

    # ------------------------------------------------------------------
    # PRODUCT DETAIL (CACHED)
    # ------------------------------------------------------------------
    def get_product(self, product_id: int) -> ProductRead:
        cache_key = f"product:{product_id}"

        def fetch_from_db():
            product = product_repository.get_product(self.db, product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found",
                )
            return ProductRead.model_validate(product).model_dump()

        data = get_or_set_cache(
            key=cache_key,
            ttl=300,
            fetch_fn=fetch_from_db,
        )

        return ProductRead.model_validate(data)

    # ------------------------------------------------------------------
    # ADMIN OPERATIONS (NO CACHE, ONLY INVALIDATION)
    # ------------------------------------------------------------------
    def create_product(self, product_in: ProductCreate) -> ProductRead:
        self._validate_status(product_in.status)

        product = product_repository.create_product(self.db, product_in)

        # Invalidate all product list caches
        redis_client.delete_pattern("product:list:*")

        return ProductRead.model_validate(product)

    def update_product(self, product_id: int, product_in: ProductUpdate) -> ProductRead:
        self._validate_status(product_in.status)

        product = product_repository.get_product(self.db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        product = product_repository.update_product(self.db, product, product_in)

        # Invalidate caches
        redis_client.delete(f"product:{product_id}")
        redis_client.delete_pattern("product:list:*")

        return ProductRead.model_validate(product)

    def delete_product(self, product_id: int) -> ProductRead:
        product = product_repository.get_product(self.db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        product = product_repository.soft_delete_product(self.db, product)

        # Invalidate caches
        redis_client.delete(f"product:{product_id}")
        redis_client.delete_pattern("product:list:*")

        return ProductRead.model_validate(product)
