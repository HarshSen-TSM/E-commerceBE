from typing import Generic, Optional, TypeVar
from pydantic import BaseModel
from pydantic import ConfigDict


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    message: str
    status_code: int
    data: Optional[T] = None
    error: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class InventoryResponse(BaseModel):
    product_id: int
    total_stock: int
    available_stock: int
    reserved_stock: int

    model_config = ConfigDict(from_attributes=True)




def success_response(
    message: str,
    data=None,
    status_code: int = 200,
):
    return APIResponse(
        message=message,
        status_code=status_code,
        data=data,
        error=None,
    )
