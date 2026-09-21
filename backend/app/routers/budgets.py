from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budget_goal import BudgetCreate, BudgetUpdate, BudgetResponse

router = APIRouter(prefix="/budgets", tags=["Budgets"])


def compute_budget_response(budget: Budget, db: Session) -> BudgetResponse:
    today = date.today()
    # Get actual spending for that budget's month/year in that category
    spent = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == budget.user_id,
        Transaction.category_id == budget.category_id,
        Transaction.type == "expense",
        func.strftime("%m", Transaction.date) == f"{budget.month:02d}",
        func.strftime("%Y", Transaction.date) == str(budget.year),
    ).scalar() or 0.0

    remaining = max(0.0, budget.amount - spent)
    percentage = min((spent / budget.amount * 100) if budget.amount > 0 else 0.0, 999.0)

    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        category_name=budget.category.name if budget.category else "Unknown",
        category_icon=budget.category.icon if budget.category else "tag",
        category_color=budget.category.color if budget.category else "#6366f1",
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        spent=round(spent, 2),
        remaining=round(remaining, 2),
        percentage=round(percentage, 1),
    )


@router.get("", response_model=list[BudgetResponse])
def get_budgets(
    month: int = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Budget).filter(Budget.user_id == current_user.id)
    if month:
        query = query.filter(Budget.month == month)
    if year:
        query = query.filter(Budget.year == year)
    budgets = query.all()
    return [compute_budget_response(b, db) for b in budgets]


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(
        Category.id == data.category_id,
        Category.user_id == current_user.id
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check duplicate
    existing = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.category_id == data.category_id,
        Budget.month == data.month,
        Budget.year == data.year,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget already exists for this category and month"
        )

    budget = Budget(
        user_id=current_user.id,
        category_id=data.category_id,
        amount=data.amount,
        month=data.month,
        year=data.year,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return compute_budget_response(budget, db)


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return compute_budget_response(budget, db)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()
