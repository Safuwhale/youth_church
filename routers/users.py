from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserResponse, UserLogin, TokenResponse
from services.user_service import create_new_user
from database import get_db
from models import User
from core.security import verify_password, create_access_token
from core.dependencies import get_current_user

router = APIRouter()

@router.post("/onboard", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def onboard_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new First-Timer or Member. 
    Automatically generates a unique Serial Number for check-ins.
    """
    return create_new_user(db=db, user_data=user)

@router.post("/login", response_model=TokenResponse)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates a user and returns a JWT token.
    For first-time logins, the password is the user's Serial Number.
    """
    # 1. Find user by phone number
    user = db.query(User).filter(User.phone_number == credentials.phone_number).first()
    
    # 2. Verify existence and password
    # We use a generic error message for both wrong phone and wrong password (security best practice)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )
        
    # 3. Check if they are active (not soft-deleted)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    # 4. Generate the JWT token
    # We store the user ID and their Role inside the token for easy RBAC (Role-Based Access Control)
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(data=token_data)

    # 5. Return the token AND the user profile so the React frontend can build the UI immediately
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
    
@router.get("/me", response_model=UserResponse)
def get_member_dashboard(current_user: User = Depends(get_current_user)):
    """
    Member Portal Endpoint.
    The React app calls this using the user's JWT token. 
    It returns their profile, which the app uses to generate their QR code on the screen.
    """
    return current_user