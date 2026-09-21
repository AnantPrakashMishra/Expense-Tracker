from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


class RecurringCreate(BaseModel):
    name: str
    amount: float
    type: str
    category_id: Optional[int] = None
    frequency: str
    start_date: date
    payment_method: str = "other"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")
        return v

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v):
        if v not in ["daily", "weekly", "monthly", "yearly"]:
            raise ValueError("Frequency must be daily/weekly/monthly/yearly")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class RecurringUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None
    frequency: Optional[str] = None
    next_occurrence: Optional[date] = None
    is_active: Optional[bool] = None
    payment_method: Optional[str] = None


class RecurringResponse(BaseModel):
    id: int
    user_id: int
    name: str
    amount: float
    type: str
    category_id: Optional[int]
    category_name: Optional[str]
    category_icon: Optional[str]
    frequency: str
    start_date: date
    next_occurrence: Optional[date]
    is_active: bool
    payment_method: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    name: str
    amount: float
    billing_cycle: str
    next_billing_date: Optional[date] = None
    category_id: Optional[int] = None
    description: Optional[str] = None

    @field_validator("billing_cycle")
    @classmethod
    def validate_billing_cycle(cls, v):
        if v not in ["weekly", "monthly", "yearly"]:
            raise ValueError("Billing cycle must be weekly/monthly/yearly")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    billing_cycle: Optional[str] = None
    next_billing_date: Optional[date] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    amount: float
    billing_cycle: str
    next_billing_date: Optional[date]
    category_id: Optional[int]
    category_name: Optional[str]
    description: Optional[str]
    is_active: bool
    monthly_cost: float = 0.0
    yearly_cost: float = 0.0
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True
