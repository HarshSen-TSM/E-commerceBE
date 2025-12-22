from pydantic import BaseModel

class InventoryBase(BaseModel):
    product_id: int
    total_stock: int

class InventoryCreate(InventoryBase):
    pass

class InventoryUpdate(BaseModel):
    total_stock: int

class InventoryResponse(BaseModel):
    product_id: int
    total_stock: int
    available_stock: int
    reserved_stock: int

    class Config:
        orm_mode = True
        form_attributes = True
