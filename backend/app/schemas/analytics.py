from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class AnalyticsSummary(BaseModel):
    total_income: float
    total_expense: float
    net_savings: float
    savings_rate: float
    transaction_count: int
    avg_daily_expense: float


class CategorySpending(BaseModel):
    category_id: Optional[int]
    category_name: str
    category_icon: str
    category_color: str
    amount: float
    percentage: float
    transaction_count: int


class MonthlyData(BaseModel):
    month: int
    year: int
    month_name: str
    income: float
    expense: float
    savings: float


class DailySpending(BaseModel):
    date: date
    amount: float
    transaction_count: int


class CashFlowData(BaseModel):
    period: str
    income: float
    expense: float
    net: float


class PaymentMethodData(BaseModel):
    method: str
    amount: float
    percentage: float
    count: int


class HealthScore(BaseModel):
    score: int
    rating: str
    savings_rate_score: int
    budget_adherence_score: int
    expense_ratio_score: int
    goal_progress_score: int
    recurring_burden_score: int
    positive_factors: List[str]
    attention_factors: List[str]
    disclaimer: str


class Insight(BaseModel):
    type: str  # info/warning/success/tip
    title: str
    message: str
    icon: str


class SmartInsights(BaseModel):
    insights: List[Insight]
    generated_at: str
