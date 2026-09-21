from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.subscription import Subscription
from app.models.category import Category
from app.schemas.recurring_sub import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def compute_costs(amount: float, billing_cycle: str):
    if billing_cycle == "monthly":
        monthly = amount
        yearly = amount * 12
    elif billing_cycle == "yearly":
        monthly = amount / 12
        yearly = amount
    elif billing_cycle == "weekly":
        monthly = amount * 4.33
        yearly = amount * 52
    else:
        monthly = amount
        yearly = amount * 12
    return round(monthly, 2), round(yearly, 2)


def build_subscription_response(s: Subscription) -> SubscriptionResponse:
    monthly, yearly = compute_costs(s.amount, s.billing_cycle)
    return SubscriptionResponse(
        id=s.id,
        user_id=s.user_id,
        name=s.name,
        amount=s.amount,
        billing_cycle=s.billing_cycle,
        next_billing_date=s.next_billing_date,
        category_id=s.category_id,
        category_name=s.category.name if s.category else None,
        description=s.description,
        is_active=s.is_active,
        monthly_cost=monthly,
        yearly_cost=yearly,
        created_at=s.created_at,
    )


@router.get("", response_model=list[SubscriptionResponse])
def get_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subs = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.name).all()
    return [build_subscription_response(s) for s in subs]


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    data: SubscriptionCreate,
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

    sub = Subscription(
        user_id=current_user.id,
        name=data.name,
        amount=data.amount,
        billing_cycle=data.billing_cycle,
        next_billing_date=data.next_billing_date,
        category_id=data.category_id,
        description=data.description,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return build_subscription_response(sub)


@router.put("/{sub_id}", response_model=SubscriptionResponse)
def update_subscription(
    sub_id: int,
    data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.user_id == current_user.id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(sub, field, value)
    db.commit()
    db.refresh(sub)
    return build_subscription_response(sub)


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.user_id == current_user.id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(sub)
    db.commit()
