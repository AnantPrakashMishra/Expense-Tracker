from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.goal import SavingsGoal, GoalContribution
from app.schemas.budget_goal import (
    SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalResponse,
    GoalContributionCreate, GoalContributionResponse
)

router = APIRouter(prefix="/goals", tags=["Savings Goals"])


def compute_goal_response(goal: SavingsGoal) -> SavingsGoalResponse:
    progress = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0.0
    remaining = max(0.0, goal.target_amount - goal.current_amount)
    return SavingsGoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        description=goal.description,
        is_completed=goal.is_completed,
        progress_percentage=round(min(progress, 100.0), 1),
        remaining_amount=round(remaining, 2),
        created_at=goal.created_at,
        contributions=[
            GoalContributionResponse.model_validate(c) for c in goal.contributions
        ],
    )


@router.get("", response_model=list[SavingsGoalResponse])
def get_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == current_user.id).all()
    return [compute_goal_response(g) for g in goals]


@router.post("", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    data: SavingsGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = SavingsGoal(
        user_id=current_user.id,
        name=data.name,
        target_amount=data.target_amount,
        current_amount=data.current_amount,
        target_date=data.target_date,
        description=data.description,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return compute_goal_response(goal)


@router.put("/{goal_id}", response_model=SavingsGoalResponse)
def update_goal(
    goal_id: int,
    data: SavingsGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return compute_goal_response(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()


@router.post("/{goal_id}/contributions", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
def add_contribution(
    goal_id: int,
    data: GoalContributionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    contribution = GoalContribution(
        goal_id=goal_id,
        user_id=current_user.id,
        amount=data.amount,
        date=data.date,
        note=data.note,
    )
    db.add(contribution)

    # Update goal current amount
    goal.current_amount = min(goal.current_amount + data.amount, goal.target_amount * 2)  # Allow small over
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True

    db.commit()
    db.refresh(goal)
    return compute_goal_response(goal)
