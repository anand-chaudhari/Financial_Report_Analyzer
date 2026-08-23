from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper."""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized pagination response wrapper."""
    items: List[T] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0
