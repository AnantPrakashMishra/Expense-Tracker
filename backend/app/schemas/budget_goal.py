from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


class BudgetCreate(BaseModel):
    category_id: int
    amount: float
    month: int
    year: int

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Budget amount must be greater than 0")
        return v

    @field_validator("month")
    @classmethod
    def valid_month(cls, v):
        if not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        return v


class BudgetUpdate(BaseModel):
    amount: Optional[float] = None
    month: Optional[int] = None
    year: Optional[int] = None


class BudgetResponse(BaseModel):
    id: int
    user_id: int
    category_id: int
    category_name: str
    category_icon: str
    category_color: str
    amount: float
    month: int
    year: int
    spent: float = 0.0
    remaining: float = 0.0
    percentage: float = 0.0

    class Config:
        from_attributes = True


class SavingsGoalCreate(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    target_date: Optional[date] = None
    description: Optional[str] = None

    @field_validator("target_amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Target amount must be greater than 0")
        return v


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None


class GoalContributionCreate(BaseModel):
    amount: float
    date: date
    note: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Contribution amount must be greater than 0")
        return v


class GoalContributionResponse(BaseModel):
    id: int
    goal_id: int
    user_id: int
    amount: float
    date: date
    note: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class SavingsGoalResponse(BaseModel):
    id: int
    user_id: int
    name: str
    target_amount: float
    current_amount: float
    target_date: Optional[date]
    description: Optional[str]
    is_completed: bool
    progress_percentage: float = 0.0
    remaining_amount: float = 0.0
    created_at: Optional[datetime]
    contributions: list[GoalContributionResponse] = []

    class Config:
        from_attributes = True
