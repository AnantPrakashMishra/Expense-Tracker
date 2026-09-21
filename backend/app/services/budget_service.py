from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.notification import Notification


def check_and_create_budget_notifications(db: Session, user_id: int, category_id: int, trans_date: date):
    """Check if spending is approaching or exceeding budget limits and create notifications."""
    budget = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.category_id == category_id,
        Budget.month == trans_date.month,
        Budget.year == trans_date.year,
    ).first()

    if not budget:
        return

    spent = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.category_id == category_id,
        Transaction.type == "expense",
        func.strftime("%m", Transaction.date) == f"{trans_date.month:02d}",
        func.strftime("%Y", Transaction.date) == str(trans_date.year),
    ).scalar() or 0.0

    percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0.0
    category_name = budget.category.name if budget.category else "Unknown"

    # Check if notification already exists for this threshold
    if percentage >= 100:
        existing = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type == "budget_exceeded",
            Notification.title.contains(category_name),
            func.strftime("%m", Notification.created_at) == f"{trans_date.month:02d}",
        ).first()
        if not existing:
            notif = Notification(
                user_id=user_id,
                type="budget_exceeded",
                title=f"Budget Exceeded: {category_name}",
                message=f"Your {category_name} budget of ₹{budget.amount:,.0f} has been exceeded. "
                        f"You've spent ₹{spent:,.0f} ({percentage:.0f}% of budget).",
            )
            db.add(notif)
            db.commit()
    elif percentage >= 70:
        existing = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type == "budget_warning",
            Notification.title.contains(category_name),
            func.strftime("%m", Notification.created_at) == f"{trans_date.month:02d}",
        ).first()
        if not existing:
            notif = Notification(
                user_id=user_id,
                type="budget_warning",
                title=f"Budget Alert: {category_name}",
                message=f"You've used {percentage:.0f}% of your {category_name} budget. "
                        f"₹{spent:,.0f} spent of ₹{budget.amount:,.0f}.",
            )
            db.add(notif)
            db.commit()
