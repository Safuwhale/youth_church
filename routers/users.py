from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserResponse
from services.user_service import create_new_user
from database import get_db

router = APIRouter()

@router.post("/onboard", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def onboard_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new First-Timer or Member. 
    Automatically generates a unique Serial Number for check-ins.
    """
    return create_new_user(db=db, user_data=user)
