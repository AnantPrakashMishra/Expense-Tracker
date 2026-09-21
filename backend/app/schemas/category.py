from pydantic import BaseModel, field_validator
from typing import Optional


class CategoryCreate(BaseModel):
    name: str
    type: str
    icon: str = "tag"
    color: str = "#6366f1"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Category name cannot be empty")
        return v.strip()


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: str
    icon: str
    color: str
    is_default: bool

    class Config:
        from_attributes = True
