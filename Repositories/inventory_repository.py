from sqlalchemy.orm import Session
from models.inventory_model  import Inventory

def get_by_product_id(db: Session, product_id: int):
    return db.query(Inventory).filter(Inventory.product_id == product_id).first()

def create_inventory(db: Session, inventory: Inventory):
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    return inventory

def update_inventory(db: Session):
    db.commit()
