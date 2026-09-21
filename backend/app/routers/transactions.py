from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import Optional
from datetime import date
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    PaginatedTransactions, CategoryInfo
)
from app.services.budget_service import check_and_create_budget_notifications
import math

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def build_transaction_response(t: Transaction) -> TransactionResponse:
    cat = None
    if t.category:
        cat = CategoryInfo(
            id=t.category.id,
            name=t.category.name,
            icon=t.category.icon,
            color=t.category.color,
            type=t.category.type,
        )
    return TransactionResponse(
        id=t.id,
        user_id=t.user_id,
        type=t.type,
        amount=t.amount,
        category_id=t.category_id,
        category=cat,
        description=t.description,
        date=t.date,
        payment_method=t.payment_method,
        notes=t.notes,
        is_recurring=t.is_recurring,
        recurring_id=t.recurring_id,
        created_at=t.created_at,
    )


@router.get("", response_model=PaginatedTransactions)
def get_transactions(
    type: Optional[str] = None,
    category_id: Optional[int] = None,
    payment_method: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    sort_by: str = "date",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if type:
        query = query.filter(Transaction.type == type)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.outerjoin(Category).filter(
            or_(
                func.lower(Transaction.description).like(search_lower),
                func.lower(Transaction.notes).like(search_lower),
                func.lower(Transaction.payment_method).like(search_lower),
                func.lower(Category.name).like(search_lower),
            )
        )

    total = query.count()

    # Sorting
    sort_col = getattr(Transaction, sort_by, Transaction.date)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col), desc(Transaction.created_at))
    else:
        query = query.order_by(asc(sort_col), desc(Transaction.created_at))

    # Pagination
    offset = (page - 1) * per_page
    transactions = query.offset(offset).limit(per_page).all()

    return PaginatedTransactions(
        items=[build_transaction_response(t) for t in transactions],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.category_id:
        cat = db.query(Category).filter(
            Category.id == data.category_id,
            Category.user_id == current_user.id
        ).first()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")

    transaction = Transaction(
        user_id=current_user.id,
        type=data.type,
        amount=data.amount,
        category_id=data.category_id,
        description=data.description,
        date=data.date,
        payment_method=data.payment_method,
        notes=data.notes,
        is_recurring=data.is_recurring,
        recurring_id=data.recurring_id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # Check budget alerts if it's an expense
    if data.type == "expense" and data.category_id:
        check_and_create_budget_notifications(db, current_user.id, data.category_id, data.date)

    return build_transaction_response(transaction)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return build_transaction_response(t)


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)

    # Re-check budget if category changed or amount changed
    if t.type == "expense" and t.category_id:
        check_and_create_budget_notifications(db, current_user.id, t.category_id, t.date)

    return build_transaction_response(t)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(t)
    db.commit()
