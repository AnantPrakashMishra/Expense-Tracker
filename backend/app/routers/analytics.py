from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List
from datetime import date, timedelta
from calendar import month_name
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget
from app.models.goal import SavingsGoal
from app.models.subscription import Subscription
from app.schemas.analytics import (
    AnalyticsSummary, CategorySpending, MonthlyData,
    DailySpending, CashFlowData, PaymentMethodData,
    HealthScore, SmartInsights, Insight
)
from app.services.insights_service import generate_insights, compute_health_score

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_date_range(period: str, start_date: Optional[date], end_date: Optional[date]):
    today = date.today()
    if start_date and end_date:
        return start_date, end_date
    if period == "7d":
        return today - timedelta(days=7), today
    elif period == "30d":
        return today - timedelta(days=30), today
    elif period == "this_month":
        return today.replace(day=1), today
    elif period == "last_month":
        first_of_this = today.replace(day=1)
        last_month_end = first_of_this - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    elif period == "3m":
        return today - timedelta(days=90), today
    elif period == "this_year":
        return today.replace(month=1, day=1), today
    else:  # default last 30 days
        return today - timedelta(days=30), today


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    period: str = "this_month",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s, e = get_date_range(period, start_date, end_date)
    
    income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "income",
        Transaction.date >= s,
        Transaction.date <= e,
    ).scalar() or 0.0

    expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        Transaction.date >= s,
        Transaction.date <= e,
    ).scalar() or 0.0

    count = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= s,
        Transaction.date <= e,
    ).scalar() or 0

    savings = income - expense
    savings_rate = (savings / income * 100) if income > 0 else 0.0
    days = max((e - s).days + 1, 1)
    avg_daily = expense / days

    return AnalyticsSummary(
        total_income=round(income, 2),
        total_expense=round(expense, 2),
        net_savings=round(savings, 2),
        savings_rate=round(savings_rate, 1),
        transaction_count=count,
        avg_daily_expense=round(avg_daily, 2),
    )


@router.get("/categories", response_model=List[CategorySpending])
def get_category_spending(
    period: str = "this_month",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type: str = "expense",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s, e = get_date_range(period, start_date, end_date)
    
    rows = db.query(
        Category.id,
        Category.name,
        Category.icon,
        Category.color,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == type,
        Transaction.date >= s,
        Transaction.date <= e,
    ).group_by(Category.id).order_by(func.sum(Transaction.amount).desc()).all()

    total_sum = sum(r.total for r in rows)
    return [
        CategorySpending(
            category_id=r.id,
            category_name=r.name,
            category_icon=r.icon,
            category_color=r.color,
            amount=round(r.total, 2),
            percentage=round(r.total / total_sum * 100, 1) if total_sum > 0 else 0,
            transaction_count=r.count,
        )
        for r in rows
    ]


@router.get("/monthly", response_model=List[MonthlyData])
def get_monthly_data(
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    result = []
    for i in range(months - 1, -1, -1):
        if today.month - i <= 0:
            m = today.month - i + 12
            y = today.year - 1
        else:
            m = today.month - i
            y = today.year

        income = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "income",
            func.strftime("%m", Transaction.date) == f"{m:02d}",
            func.strftime("%Y", Transaction.date) == str(y),
        ).scalar() or 0.0

        expense = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
            func.strftime("%m", Transaction.date) == f"{m:02d}",
            func.strftime("%Y", Transaction.date) == str(y),
        ).scalar() or 0.0

        result.append(MonthlyData(
            month=m,
            year=y,
            month_name=month_name[m][:3],
            income=round(income, 2),
            expense=round(expense, 2),
            savings=round(income - expense, 2),
        ))

    return result


@router.get("/daily", response_model=List[DailySpending])
def get_daily_spending(
    period: str = "this_month",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s, e = get_date_range(period, start_date, end_date)

    rows = db.query(
        Transaction.date,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        Transaction.date >= s,
        Transaction.date <= e,
    ).group_by(Transaction.date).order_by(Transaction.date).all()

    # Fill in missing days with 0
    all_dates = {}
    current = s
    while current <= e:
        all_dates[current] = DailySpending(date=current, amount=0.0, transaction_count=0)
        current += timedelta(days=1)

    for r in rows:
        all_dates[r.date] = DailySpending(
            date=r.date,
            amount=round(r.total, 2),
            transaction_count=r.count,
        )

    return list(all_dates.values())


@router.get("/payment-methods", response_model=List[PaymentMethodData])
def get_payment_method_spending(
    period: str = "this_month",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s, e = get_date_range(period, start_date, end_date)

    rows = db.query(
        Transaction.payment_method,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        Transaction.date >= s,
        Transaction.date <= e,
    ).group_by(Transaction.payment_method).order_by(func.sum(Transaction.amount).desc()).all()

    total_sum = sum(r.total for r in rows)
    return [
        PaymentMethodData(
            method=r.payment_method,
            amount=round(r.total, 2),
            percentage=round(r.total / total_sum * 100, 1) if total_sum > 0 else 0,
            count=r.count,
        )
        for r in rows
    ]


@router.get("/cashflow", response_model=List[CashFlowData])
def get_cashflow(
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = []
    today = date.today()
    for i in range(months - 1, -1, -1):
        if today.month - i <= 0:
            m = today.month - i + 12
            y = today.year - 1
        else:
            m = today.month - i
            y = today.year

        income = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "income",
            func.strftime("%m", Transaction.date) == f"{m:02d}",
            func.strftime("%Y", Transaction.date) == str(y),
        ).scalar() or 0.0

        expense = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
            func.strftime("%m", Transaction.date) == f"{m:02d}",
            func.strftime("%Y", Transaction.date) == str(y),
        ).scalar() or 0.0

        data.append(CashFlowData(
            period=f"{month_name[m][:3]} {y}",
            income=round(income, 2),
            expense=round(expense, 2),
            net=round(income - expense, 2),
        ))

    return data


@router.get("/insights", response_model=SmartInsights)
def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_insights(db, current_user.id)


@router.get("/health-score", response_model=HealthScore)
def get_health_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return compute_health_score(db, current_user.id)


@router.get("/calendar")
def get_calendar_data(
    month: int,
    year: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(
        Transaction.date,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        func.strftime("%m", Transaction.date) == f"{month:02d}",
        func.strftime("%Y", Transaction.date) == str(year),
    ).group_by(Transaction.date).all()

    return {
        str(r.date): {
            "amount": round(r.total, 2),
            "count": r.count,
        }
        for r in rows
    }


@router.get("/heatmap")
def get_heatmap_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns last 365 days of daily spending for heatmap."""
    end = date.today()
    start = end - timedelta(days=364)

    rows = db.query(
        Transaction.date,
        func.sum(Transaction.amount).label("total"),
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        Transaction.date >= start,
        Transaction.date <= end,
    ).group_by(Transaction.date).all()

    data = {str(r.date): round(r.total, 2) for r in rows}
    return data
