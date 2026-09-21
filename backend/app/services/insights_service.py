from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from calendar import month_name
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import SavingsGoal
from app.models.subscription import Subscription
from app.schemas.analytics import SmartInsights, Insight, HealthScore


def generate_insights(db: Session, user_id: int) -> SmartInsights:
    """Generate rule-based financial insights from actual transaction data."""
    insights = []
    today = date.today()
    current_month_start = today.replace(day=1)
    
    # Last month
    last_month_end = current_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    # Current month totals
    curr_income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "income",
        Transaction.date >= current_month_start,
        Transaction.date <= today,
    ).scalar() or 0.0

    curr_expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= current_month_start,
        Transaction.date <= today,
    ).scalar() or 0.0

    # Last month totals
    last_expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= last_month_start,
        Transaction.date <= last_month_end,
    ).scalar() or 0.0

    last_income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "income",
        Transaction.date >= last_month_start,
        Transaction.date <= last_month_end,
    ).scalar() or 0.0

    # Savings rate
    if curr_income > 0:
        savings = curr_income - curr_expense
        savings_rate = savings / curr_income * 100

        if savings_rate >= 30:
            insights.append(Insight(
                type="success",
                title="Excellent Savings Rate",
                message=f"Your savings rate is {savings_rate:.1f}% this month. That's excellent financial management!",
                icon="trending-up",
            ))
        elif savings_rate >= 20:
            insights.append(Insight(
                type="success",
                title="Good Savings Rate",
                message=f"Your savings rate is {savings_rate:.1f}% this month. Keep it up!",
                icon="trending-up",
            ))
        elif savings_rate >= 10:
            insights.append(Insight(
                type="info",
                title="Moderate Savings Rate",
                message=f"Your savings rate is {savings_rate:.1f}%. Try to aim for 20%+ for financial health.",
                icon="info",
            ))
        else:
            insights.append(Insight(
                type="warning",
                title="Low Savings Rate",
                message=f"Your savings rate is only {savings_rate:.1f}%. Consider reducing discretionary spending.",
                icon="alert-triangle",
            ))

    # Expense comparison with last month
    if last_expense > 0 and curr_expense > 0:
        change = ((curr_expense - last_expense) / last_expense) * 100
        if change > 0:
            insights.append(Insight(
                type="warning" if change > 10 else "info",
                title="Expenses Increased",
                message=f"Your expenses increased by {change:.1f}% compared to last month "
                        f"(₹{curr_expense:,.0f} vs ₹{last_expense:,.0f}).",
                icon="trending-up",
            ))
        else:
            insights.append(Insight(
                type="success",
                title="Expenses Decreased",
                message=f"Your expenses decreased by {abs(change):.1f}% compared to last month. Great work!",
                icon="trending-down",
            ))

    # Highest spending category this month
    top_category = db.query(
        func.sum(Transaction.amount).label("total"),
    ).join(Transaction.category).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= current_month_start,
        Transaction.date <= today,
    ).group_by(Transaction.category_id).order_by(func.sum(Transaction.amount).desc()).first()

    if top_category:
        from app.models.category import Category
        top_cat_row = db.query(
            func.sum(Transaction.amount).label("total"),
            Transaction.category_id,
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.date >= current_month_start,
            Transaction.date <= today,
        ).group_by(Transaction.category_id).order_by(func.sum(Transaction.amount).desc()).first()

        if top_cat_row and top_cat_row.category_id:
            cat = db.query(Category).filter(Category.id == top_cat_row.category_id).first()
            if cat:
                insights.append(Insight(
                    type="info",
                    title="Highest Spending Category",
                    message=f"{cat.name} is your highest spending category this month with ₹{top_cat_row.total:,.0f}.",
                    icon="pie-chart",
                ))

    # Budget usage alerts
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == today.month,
        Budget.year == today.year,
    ).all()

    for budget in budgets:
        spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.type == "expense",
            func.strftime("%m", Transaction.date) == f"{today.month:02d}",
            func.strftime("%Y", Transaction.date) == str(today.year),
        ).scalar() or 0.0

        pct = (spent / budget.amount * 100) if budget.amount > 0 else 0
        cat_name = budget.category.name if budget.category else "Unknown"

        if pct > 100:
            insights.append(Insight(
                type="warning",
                title=f"{cat_name} Budget Exceeded",
                message=f"You have exceeded your {cat_name} budget. Spent ₹{spent:,.0f} of ₹{budget.amount:,.0f} ({pct:.0f}%).",
                icon="alert-circle",
            ))
        elif pct >= 85:
            insights.append(Insight(
                type="warning",
                title=f"{cat_name} Budget Almost Full",
                message=f"You have used {pct:.0f}% of your {cat_name} budget this month.",
                icon="alert-triangle",
            ))

    # Subscription spending
    active_subs = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True,
    ).all()

    if active_subs:
        total_monthly_subs = sum(
            s.amount if s.billing_cycle == "monthly" else
            s.amount / 12 if s.billing_cycle == "yearly" else
            s.amount * 4.33
            for s in active_subs
        )
        insights.append(Insight(
            type="info",
            title="Subscription Expenses",
            message=f"You have {len(active_subs)} active subscriptions costing ₹{total_monthly_subs:,.0f}/month "
                    f"(₹{total_monthly_subs * 12:,.0f}/year).",
            icon="credit-card",
        ))

    if not insights:
        insights.append(Insight(
            type="info",
            title="Start Tracking",
            message="Add more transactions to get personalized financial insights.",
            icon="bar-chart-2",
        ))

    return SmartInsights(
        insights=insights,
        generated_at=str(today),
    )


def compute_health_score(db: Session, user_id: int) -> HealthScore:
    """Compute a 0-100 financial health score from multiple factors."""
    today = date.today()
    current_month_start = today.replace(day=1)
    last_month_end = current_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    # --- Factor 1: Savings Rate (0-30 points) ---
    income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "income",
        Transaction.date >= current_month_start,
        Transaction.date <= today,
    ).scalar() or 0.0

    expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= current_month_start,
        Transaction.date <= today,
    ).scalar() or 0.0

    savings_rate = ((income - expense) / income * 100) if income > 0 else 0
    if savings_rate >= 30:
        savings_score = 30
    elif savings_rate >= 20:
        savings_score = 25
    elif savings_rate >= 10:
        savings_score = 15
    elif savings_rate > 0:
        savings_score = 8
    else:
        savings_score = 0

    # --- Factor 2: Budget Adherence (0-25 points) ---
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == today.month,
        Budget.year == today.year,
    ).all()

    budget_score = 20  # default if no budgets
    if budgets:
        total_budgets = len(budgets)
        within_budget = 0
        for b in budgets:
            spent = db.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == b.category_id,
                Transaction.type == "expense",
                func.strftime("%m", Transaction.date) == f"{today.month:02d}",
                func.strftime("%Y", Transaction.date) == str(today.year),
            ).scalar() or 0.0
            if spent <= b.amount:
                within_budget += 1

        adherence_rate = within_budget / total_budgets
        budget_score = int(25 * adherence_rate)

    # --- Factor 3: Expense/Income Ratio (0-20 points) ---
    if income > 0:
        expense_ratio = expense / income
        if expense_ratio <= 0.5:
            expense_ratio_score = 20
        elif expense_ratio <= 0.7:
            expense_ratio_score = 15
        elif expense_ratio <= 0.9:
            expense_ratio_score = 8
        else:
            expense_ratio_score = 0
    else:
        expense_ratio_score = 10

    # --- Factor 4: Goals Progress (0-15 points) ---
    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).all()
    if goals:
        avg_progress = sum(
            min(g.current_amount / g.target_amount, 1.0) for g in goals if g.target_amount > 0
        ) / len(goals)
        goal_score = int(15 * avg_progress)
    else:
        goal_score = 8

    # --- Factor 5: Subscription Burden (0-10 points) ---
    subs = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True,
    ).all()
    sub_monthly = sum(
        s.amount if s.billing_cycle == "monthly" else
        s.amount / 12 if s.billing_cycle == "yearly" else
        s.amount * 4.33
        for s in subs
    )

    if income > 0:
        sub_ratio = sub_monthly / income
        if sub_ratio <= 0.05:
            recurring_score = 10
        elif sub_ratio <= 0.10:
            recurring_score = 7
        elif sub_ratio <= 0.20:
            recurring_score = 4
        else:
            recurring_score = 1
    else:
        recurring_score = 5

    total_score = savings_score + budget_score + expense_ratio_score + goal_score + recurring_score

    # Rating
    if total_score >= 80:
        rating = "Excellent"
    elif total_score >= 65:
        rating = "Good"
    elif total_score >= 50:
        rating = "Fair"
    elif total_score >= 30:
        rating = "Needs Improvement"
    else:
        rating = "Critical"

    # Positive and attention factors
    positive_factors = []
    attention_factors = []

    if savings_score >= 20:
        positive_factors.append("Good savings rate")
    else:
        attention_factors.append("Low savings rate — aim for 20%+")

    if budget_score >= 18:
        positive_factors.append("Most budgets under control")
    elif budgets:
        attention_factors.append("Some budgets exceeded this month")

    if expense_ratio_score >= 15:
        positive_factors.append("Healthy income to expense ratio")
    else:
        attention_factors.append("High expense to income ratio")

    if goal_score >= 10:
        positive_factors.append("Good progress on savings goals")
    elif goals:
        attention_factors.append("Low savings goal progress")

    if recurring_score >= 7:
        positive_factors.append("Subscriptions are manageable")
    else:
        attention_factors.append("High subscription spending")

    return HealthScore(
        score=total_score,
        rating=rating,
        savings_rate_score=savings_score,
        budget_adherence_score=budget_score,
        expense_ratio_score=expense_ratio_score,
        goal_progress_score=goal_score,
        recurring_burden_score=recurring_score,
        positive_factors=positive_factors,
        attention_factors=attention_factors,
        disclaimer="This score is an educational metric for the SpendWise application and is not professional financial advice.",
    )
