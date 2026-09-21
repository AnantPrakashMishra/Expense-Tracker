from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.seed import load_demo_data

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.post("/load")
def load_demo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Load 6 months of realistic demo data for the current user."""
    result = load_demo_data(db, current_user.id)
    return result
