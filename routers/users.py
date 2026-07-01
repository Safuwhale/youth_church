from fastapi import APIRouter, Depends, status, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserResponse, UserLogin, TokenResponse, UserUpdate, UserDirectoryItem, UserRoleUpdate
from services.user_service import create_new_user
from database import get_db
from models import User
from core.security import verify_password, create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from core.dependencies import get_current_user
from sqlalchemy import or_  

router = APIRouter()

@router.post("/onboard", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def onboard_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new First-Timer or Member. 
    Automatically generates a unique Serial Number for check-ins.
    """
    return create_new_user(db=db, user_data=user)

@router.post("/login")
def login_user(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    """
    Authenticates a user, sets an httpOnly refresh cookie, and returns a short-lived access token.
    """
    user = db.query(User).filter(User.phone_number == credentials.phone_number).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    # Generate BOTH tokens
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # The Magic: Set the Refresh Token as a secure, httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,             # Critical: JavaScript cannot read this
        secure=True,               # Change to True in production (requires HTTPS)
        samesite="lax",            # CSRF protection
        max_age=30 * 24 * 60 * 60  # 30 days in seconds
    )

    # Return the access token and user profile to React
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

@router.put("/me", response_model=UserResponse)
def update_profile(
    update_data: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Updates the logged-in user's profile.
    """
    # Map update_data fields to current_user model fields
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Handle password update if present
    if "new_password" in update_dict:
        current_user.hashed_password = get_password_hash(update_dict.pop("new_password"))
        
    for key, value in update_dict.items():
        setattr(current_user, key, value)
        
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/search")
def search_users(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["usher", "hod"]:
        raise HTTPException(status_code=403)
    return db.query(User).filter(
        or_(User.first_name.ilike(f"%{q}%"), User.last_name.ilike(f"%{q}%"), User.serial_number.ilike(f"%{q}%"))
    ).limit(10).all()


@router.get("/directory", response_model=list[UserDirectoryItem])
def list_directory_users(
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized.")

    query = db.query(User)
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search),
                User.last_name.ilike(search),
                User.phone_number.ilike(search),
                User.serial_number.ilike(search),
                User.role.ilike(search),
            )
        )

    return query.order_by(User.created_at.desc()).all()


@router.patch("/{user_id}/role", response_model=UserDirectoryItem)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


###########delete later
from core.security import get_password_hash # Ensure this is imported!

@router.post("/seed-usher")
def create_test_usher(db: Session = Depends(get_db)):
    """
    Temporary endpoint to quickly create a test Usher profile.
    DELETE THIS BEFORE GOING TO PRODUCTION!
    """
    # Check if our test usher already exists
    existing_usher = db.query(User).filter(User.phone_number == "08011110000").first()
    
    if existing_usher:
        return {
            "message": "Usher already exists!", 
            "login_phone": "08011110000", 
            "login_password": "password123"
        }
        
    # Create the test usher
    new_usher = User(
        first_name="Test",
        last_name="Usher",
        phone_number="08011110000",
        hashed_password=get_password_hash("password123"), # Assumes you have this hashing utility
        serial_number="HORYC-999",
        role="usher",
        is_active=True
    )
    
    db.add(new_usher)
    db.commit()
    
    return {
        "message": "Test Usher successfully created!",
        "login_phone": "08011110000",
        "login_password": "password123"
    }
@router.post("/refresh")
def refresh_access_token(response: Response, refresh_token: str = Cookie(None), db: Session = Depends(get_db)):
    """
    Reads the httpOnly refresh_token cookie and returns a new access_token if valid.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing. Please log in again.")
        
    try:
        # Decode the refresh token cookie
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload.")
            
        # Verify user still exists and is not banned
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User account is inactive.")

        # Generate a fresh, short-lived Access Token
        new_access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
        
        return {
            "access_token": new_access_token, 
            "token_type": "bearer"
        }
        
    except JWTError:
        # If the token is expired or tampered with, clear the cookie and force a login
        response.delete_cookie("refresh_token")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")