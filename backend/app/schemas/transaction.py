from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


class TransactionCreate(BaseModel):
    type: str
    amount: float
    category_id: Optional[int] = None
    description: str
    date: date
    payment_method: str = "cash"
    notes: Optional[str] = None
    is_recurring: bool = False
    recurring_id: Optional[int] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v):
        valid = ["cash", "upi", "debit_card", "credit_card", "bank_transfer", "other"]
        if v not in valid:
            raise ValueError(f"Payment method must be one of {valid}")
        return v


class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    date: Optional[date] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class CategoryInfo(BaseModel):
    id: int
    name: str
    icon: str
    color: str
    type: str

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    type: str
    amount: float
    category_id: Optional[int]
    category: Optional[CategoryInfo]
    description: str
    date: date
    payment_method: str
    notes: Optional[str]
    is_recurring: bool
    recurring_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class TransactionFilter(BaseModel):
    type: Optional[str] = None
    category_id: Optional[int] = None
    payment_method: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search: Optional[str] = None
    page: int = 1
    per_page: int = 20
    sort_by: str = "date"
    sort_order: str = "desc"


class PaginatedTransactions(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
