from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    message: str
    status_code: int
    data: Optional[T] = None
    error: Optional[str] = None
