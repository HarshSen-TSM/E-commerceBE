# Repositories/product_repository.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.product_model import Product
from schemas.product_schema import ProductCreate, ProductUpdate


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(
        Product.id == product_id,
        Product.status != "deleted",
    ).first()


def list_products(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[Product]:
    query = db.query(Product).filter(Product.status != "deleted")

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like)))

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    return query.offset(skip).limit(limit).all()


def create_product(db: Session, product_in: ProductCreate) -> Product:
    db_obj = Product(**product_in.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_product(db: Session, db_obj: Product, product_in: ProductUpdate) -> Product:
    data = product_in.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def soft_delete_product(db: Session, db_obj: Product) -> Product:
    db_obj.status = "deleted"
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
