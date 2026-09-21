from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.recurring import RecurringTransaction
from app.models.category import Category
from app.schemas.recurring_sub import RecurringCreate, RecurringUpdate, RecurringResponse

router = APIRouter(prefix="/recurring", tags=["Recurring Transactions"])


def compute_next_occurrence(frequency: str, from_date: date) -> date:
    if frequency == "daily":
        return from_date + timedelta(days=1)
    elif frequency == "weekly":
        return from_date + timedelta(weeks=1)
    elif frequency == "monthly":
        return from_date + relativedelta(months=1)
    elif frequency == "yearly":
        return from_date + relativedelta(years=1)
    return from_date


def build_recurring_response(r: RecurringTransaction) -> RecurringResponse:
    return RecurringResponse(
        id=r.id,
        user_id=r.user_id,
        name=r.name,
        amount=r.amount,
        type=r.type,
        category_id=r.category_id,
        category_name=r.category.name if r.category else None,
        category_icon=r.category.icon if r.category else None,
        frequency=r.frequency,
        start_date=r.start_date,
        next_occurrence=r.next_occurrence,
        is_active=r.is_active,
        payment_method=r.payment_method,
        created_at=r.created_at,
    )


@router.get("", response_model=list[RecurringResponse])
def get_recurring(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recurring = db.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == current_user.id
    ).order_by(RecurringTransaction.next_occurrence).all()
    return [build_recurring_response(r) for r in recurring]


@router.post("", response_model=RecurringResponse, status_code=status.HTTP_201_CREATED)
def create_recurring(
    data: RecurringCreate,
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

    next_occ = compute_next_occurrence(data.frequency, data.start_date)
    recurring = RecurringTransaction(
        user_id=current_user.id,
        name=data.name,
        amount=data.amount,
        type=data.type,
        category_id=data.category_id,
        frequency=data.frequency,
        start_date=data.start_date,
        next_occurrence=next_occ,
        payment_method=data.payment_method,
    )
    db.add(recurring)
    db.commit()
    db.refresh(recurring)
    return build_recurring_response(recurring)


@router.put("/{recurring_id}", response_model=RecurringResponse)
def update_recurring(
    recurring_id: int,
    data: RecurringUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recurring = db.query(RecurringTransaction).filter(
        RecurringTransaction.id == recurring_id,
        RecurringTransaction.user_id == current_user.id
    ).first()
    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(recurring, field, value)
    db.commit()
    db.refresh(recurring)
    return build_recurring_response(recurring)


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(
    recurring_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recurring = db.query(RecurringTransaction).filter(
        RecurringTransaction.id == recurring_id,
        RecurringTransaction.user_id == current_user.id
    ).first()
    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    db.delete(recurring)
    db.commit()
