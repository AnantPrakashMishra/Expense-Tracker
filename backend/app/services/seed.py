from sqlalchemy.orm import Session
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import random
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import SavingsGoal, GoalContribution
from app.models.recurring import RecurringTransaction
from app.models.subscription import Subscription
from app.models.notification import Notification
from app.auth.auth import get_password_hash
from app.models.user import User


# Default categories for each new user
DEFAULT_CATEGORIES = [
    # Expense categories
    {"name": "Food & Dining", "type": "expense", "icon": "utensils", "color": "#f97316"},
    {"name": "Transport", "type": "expense", "icon": "car", "color": "#3b82f6"},
    {"name": "Shopping", "type": "expense", "icon": "shopping-bag", "color": "#ec4899"},
    {"name": "Entertainment", "type": "expense", "icon": "film", "color": "#a855f7"},
    {"name": "Education", "type": "expense", "icon": "book-open", "color": "#06b6d4"},
    {"name": "Health", "type": "expense", "icon": "heart", "color": "#ef4444"},
    {"name": "Bills & Utilities", "type": "expense", "icon": "zap", "color": "#f59e0b"},
    {"name": "Rent", "type": "expense", "icon": "home", "color": "#8b5cf6"},
    {"name": "Travel", "type": "expense", "icon": "map-pin", "color": "#10b981"},
    {"name": "Subscriptions", "type": "expense", "icon": "credit-card", "color": "#6366f1"},
    {"name": "Groceries", "type": "expense", "icon": "shopping-cart", "color": "#84cc16"},
    {"name": "Personal Care", "type": "expense", "icon": "user", "color": "#f43f5e"},
    {"name": "Other", "type": "expense", "icon": "more-horizontal", "color": "#6b7280"},
    # Income categories
    {"name": "Salary", "type": "income", "icon": "briefcase", "color": "#22c55e"},
    {"name": "Freelance", "type": "income", "icon": "laptop", "color": "#14b8a6"},
    {"name": "Investment", "type": "income", "icon": "trending-up", "color": "#f59e0b"},
    {"name": "Gift", "type": "income", "icon": "gift", "color": "#ec4899"},
    {"name": "Other Income", "type": "income", "icon": "plus-circle", "color": "#84cc16"},
]


def create_default_categories(db: Session, user_id: int):
    """Create default categories for a new user."""
    for cat_data in DEFAULT_CATEGORIES:
        cat = Category(
            user_id=user_id,
            name=cat_data["name"],
            type=cat_data["type"],
            icon=cat_data["icon"],
            color=cat_data["color"],
            is_default=True,
        )
        db.add(cat)
    db.commit()


def load_demo_data(db: Session, user_id: int):
    """Generate 6 months of realistic demo data for presentation."""
    today = date.today()

    # Get categories for this user
    cats = {c.name: c for c in db.query(Category).filter(Category.user_id == user_id).all()}

    def cat(name):
        return cats.get(name)

    # Clear existing data
    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.query(Budget).filter(Budget.user_id == user_id).delete()
    db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).delete()
    db.query(RecurringTransaction).filter(RecurringTransaction.user_id == user_id).delete()
    db.query(Subscription).filter(Subscription.user_id == user_id).delete()
    db.query(Notification).filter(Notification.user_id == user_id).delete()
    db.commit()

    transactions = []

    # Generate 6 months of transactions
    for months_back in range(5, -1, -1):
        ref_date = today - relativedelta(months=months_back)
        year = ref_date.year
        month = ref_date.month

        # Monthly salary
        salary_date = date(year, month, 1)
        transactions.append(Transaction(
            user_id=user_id,
            type="income",
            amount=random.uniform(45000, 55000),
            category_id=cat("Salary").id if cat("Salary") else None,
            description="Monthly Salary",
            date=salary_date,
            payment_method="bank_transfer",
        ))

        # Rent on 1st
        if cat("Rent"):
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=12000,
                category_id=cat("Rent").id,
                description="Monthly Rent",
                date=date(year, month, 1),
                payment_method="bank_transfer",
            ))

        # Food expenses (10-15 per month)
        food_descriptions = [
            "Zomato Order", "Swiggy", "Restaurant Dinner", "Cafe Coffee Day",
            "Starbucks", "McDonald's", "Domino's Pizza", "Lunch at office",
            "Grocery store", "Evening snacks", "Breakfast", "Canteen"
        ]
        for _ in range(random.randint(10, 15)):
            day = random.randint(1, 28)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(random.uniform(80, 800), 0),
                category_id=cat("Food & Dining").id if cat("Food & Dining") else None,
                description=random.choice(food_descriptions),
                date=date(year, month, day),
                payment_method=random.choice(["upi", "cash", "credit_card"]),
            ))

        # Transport (5-8 per month)
        transport_desc = ["Uber ride", "Ola Cab", "Metro Card", "Petrol", "Auto Rickshaw", "Bus Pass"]
        for _ in range(random.randint(5, 8)):
            day = random.randint(1, 28)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(random.uniform(50, 500), 0),
                category_id=cat("Transport").id if cat("Transport") else None,
                description=random.choice(transport_desc),
                date=date(year, month, day),
                payment_method=random.choice(["upi", "cash"]),
            ))

        # Shopping (3-5 per month)
        shopping_desc = ["Amazon Order", "Flipkart", "Myntra", "Clothes", "Electronics", "Books", "Home Decor"]
        for _ in range(random.randint(3, 5)):
            day = random.randint(1, 28)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(random.uniform(200, 3000), 0),
                category_id=cat("Shopping").id if cat("Shopping") else None,
                description=random.choice(shopping_desc),
                date=date(year, month, day),
                payment_method=random.choice(["credit_card", "upi", "debit_card"]),
            ))

        # Entertainment (2-4 per month)
        entertainment_desc = ["Movie Tickets", "BookMyShow", "Gaming", "Netflix Gift Card", "Concert Tickets"]
        for _ in range(random.randint(2, 4)):
            day = random.randint(1, 28)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(random.uniform(100, 800), 0),
                category_id=cat("Entertainment").id if cat("Entertainment") else None,
                description=random.choice(entertainment_desc),
                date=date(year, month, day),
                payment_method=random.choice(["upi", "credit_card"]),
            ))

        # Bills (fixed monthly)
        bills = [
            ("Electricity Bill", random.uniform(800, 1500)),
            ("Internet Bill", 799),
            ("Mobile Recharge", 299),
        ]
        for desc, amount in bills:
            day = random.randint(3, 7)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(amount, 0),
                category_id=cat("Bills & Utilities").id if cat("Bills & Utilities") else None,
                description=desc,
                date=date(year, month, day),
                payment_method=random.choice(["upi", "bank_transfer"]),
            ))

        # Health (1-2 per month)
        health_desc = ["Medical consultation", "Pharmacy", "Gym membership", "Vitamins", "Health checkup"]
        for _ in range(random.randint(1, 2)):
            day = random.randint(1, 28)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(random.uniform(200, 1500), 0),
                category_id=cat("Health").id if cat("Health") else None,
                description=random.choice(health_desc),
                date=date(year, month, day),
                payment_method=random.choice(["upi", "cash", "debit_card"]),
            ))

        # Education (1 per month sometimes)
        if random.random() > 0.4:
            day = random.randint(1, 28)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(random.uniform(500, 3000), 0),
                category_id=cat("Education").id if cat("Education") else None,
                description=random.choice(["Udemy Course", "Books", "Online class", "College fees", "Workshop"]),
                date=date(year, month, day),
                payment_method=random.choice(["upi", "credit_card"]),
            ))

        # Subscriptions (fixed monthly)
        sub_transactions = [
            ("Netflix Subscription", 649),
            ("Spotify Premium", 119),
            ("Google Drive Storage", 130),
        ]
        for desc, amount in sub_transactions:
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=amount,
                category_id=cat("Subscriptions").id if cat("Subscriptions") else None,
                description=desc,
                date=date(year, month, random.randint(5, 10)),
                payment_method="credit_card",
            ))

        # Groceries (4-6 per month)
        grocery_desc = ["BigBasket Order", "DMart", "Local Kirana", "Vegetables", "Fruits", "Weekly groceries"]
        for _ in range(random.randint(4, 6)):
            day = random.randint(1, 28)
            transactions.append(Transaction(
                user_id=user_id,
                type="expense",
                amount=round(random.uniform(300, 1500), 0),
                category_id=cat("Groceries").id if cat("Groceries") else None,
                description=random.choice(grocery_desc),
                date=date(year, month, day),
                payment_method=random.choice(["upi", "cash"]),
            ))

        # Occasional extra income
        if random.random() > 0.5:
            transactions.append(Transaction(
                user_id=user_id,
                type="income",
                amount=round(random.uniform(3000, 15000), 0),
                category_id=cat("Freelance").id if cat("Freelance") else None,
                description="Freelance project payment",
                date=date(year, month, random.randint(15, 28)),
                payment_method="bank_transfer",
            ))

    # Batch add all transactions
    for t in transactions:
        db.add(t)
    db.commit()

    # --- Create Budgets for current month ---
    budget_data = [
        ("Food & Dining", 8000),
        ("Transport", 3000),
        ("Shopping", 5000),
        ("Entertainment", 2000),
        ("Bills & Utilities", 3500),
        ("Health", 2000),
        ("Groceries", 6000),
        ("Education", 3000),
        ("Subscriptions", 1500),
    ]

    for cat_name, amount in budget_data:
        c = cat(cat_name)
        if c:
            existing = db.query(Budget).filter(
                Budget.user_id == user_id,
                Budget.category_id == c.id,
                Budget.month == today.month,
                Budget.year == today.year,
            ).first()
            if not existing:
                db.add(Budget(
                    user_id=user_id,
                    category_id=c.id,
                    amount=amount,
                    month=today.month,
                    year=today.year,
                ))
    db.commit()

    # --- Create Savings Goals ---
    goals_data = [
        {"name": "Emergency Fund", "target": 150000, "current": 42000, "desc": "6 months of expenses saved"},
        {"name": "New Laptop", "target": 80000, "current": 35000, "desc": "MacBook Pro for work"},
        {"name": "Vacation - Goa", "target": 35000, "current": 12000, "desc": "Beach holiday with friends"},
        {"name": "Bike", "target": 120000, "current": 25000, "desc": "Royal Enfield Classic 350"},
    ]

    for g in goals_data:
        goal = SavingsGoal(
            user_id=user_id,
            name=g["name"],
            target_amount=g["target"],
            current_amount=g["current"],
            target_date=today + relativedelta(months=random.randint(3, 12)),
            description=g["desc"],
        )
        db.add(goal)
    db.commit()

    # Add contributions to goals
    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).all()
    for goal in goals:
        for i in range(random.randint(2, 5)):
            contrib_date = today - relativedelta(months=i)
            contrib = GoalContribution(
                goal_id=goal.id,
                user_id=user_id,
                amount=round(random.uniform(2000, 8000), 0),
                date=contrib_date.replace(day=random.randint(1, 28)),
                note="Monthly contribution",
            )
            db.add(contrib)
    db.commit()

    # --- Create Recurring Transactions ---
    recurring_data = [
        {"name": "Salary Credit", "amount": 50000, "type": "income", "cat": "Salary", "freq": "monthly"},
        {"name": "Rent Payment", "amount": 12000, "type": "expense", "cat": "Rent", "freq": "monthly"},
        {"name": "Internet Bill", "amount": 799, "type": "expense", "cat": "Bills & Utilities", "freq": "monthly"},
        {"name": "Electricity Bill", "amount": 1200, "type": "expense", "cat": "Bills & Utilities", "freq": "monthly"},
        {"name": "Gym Membership", "amount": 1500, "type": "expense", "cat": "Health", "freq": "monthly"},
    ]

    for r in recurring_data:
        c = cat(r["cat"])
        next_occ = today.replace(day=1) + relativedelta(months=1)
        db.add(RecurringTransaction(
            user_id=user_id,
            name=r["name"],
            amount=r["amount"],
            type=r["type"],
            category_id=c.id if c else None,
            frequency=r["freq"],
            start_date=today - relativedelta(months=5),
            next_occurrence=next_occ,
        ))
    db.commit()

    # --- Create Subscriptions ---
    subscriptions_data = [
        {"name": "Netflix", "amount": 649, "cycle": "monthly", "cat": "Subscriptions"},
        {"name": "Spotify Premium", "amount": 119, "cycle": "monthly", "cat": "Subscriptions"},
        {"name": "Google Drive (200GB)", "amount": 130, "cycle": "monthly", "cat": "Subscriptions"},
        {"name": "Amazon Prime", "amount": 1499, "cycle": "yearly", "cat": "Subscriptions"},
        {"name": "GitHub Pro", "amount": 744, "cycle": "yearly", "cat": "Subscriptions"},
    ]

    for s in subscriptions_data:
        c = cat(s["cat"])
        db.add(Subscription(
            user_id=user_id,
            name=s["name"],
            amount=s["amount"],
            billing_cycle=s["cycle"],
            next_billing_date=today + relativedelta(months=1),
            category_id=c.id if c else None,
        ))
    db.commit()

    # --- Create some notifications ---
    notifs = [
        Notification(
            user_id=user_id,
            type="budget_warning",
            title="Food & Dining Budget Alert",
            message="You've used 78% of your Food & Dining budget this month.",
        ),
        Notification(
            user_id=user_id,
            type="goal_milestone",
            title="Goal Milestone: Emergency Fund",
            message="You've saved 28% towards your Emergency Fund goal. Keep it up!",
        ),
        Notification(
            user_id=user_id,
            type="recurring",
            title="Upcoming: Rent Payment",
            message="Your rent payment of ₹12,000 is due in 5 days.",
        ),
    ]
    for n in notifs:
        db.add(n)
    db.commit()

    return {"message": "Demo data loaded successfully", "transactions": len(transactions)}
