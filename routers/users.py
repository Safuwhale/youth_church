from fastapi import APIRouter, Depends, status, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from schemas.user import (
    UserCreate, UserResponse, UserLogin, TokenResponse, UserUpdate, 
    UserDirectoryItem, UserRoleUpdate, PasswordChangeRequest,
    PhoneLookupRequest, NameVerifyRequest, ClaimProfileRequest
)
from services.user_service import create_new_user
from database import get_db
from models import User
from core.security import verify_password, create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM, COOKIE_SECURE, get_password_hash
from jose import jwt, JWTError
from core.dependencies import get_current_user
from sqlalchemy import or_  
import os
import time
import cloudinary
import cloudinary.utils
from dotenv import load_dotenv
from thefuzz import fuzz

load_dotenv()

# --- CLOUDINARY CONFIGURATION ---
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

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

    # Set the Refresh Token as a secure, httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,             # Critical: JavaScript cannot read this
        secure=COOKIE_SECURE,
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


@router.post("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")

    if len(payload.new_password.strip()) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password is too short.")

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    db.refresh(current_user)
    return {"message": "Password updated successfully."}

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
    
    # --- NEW ONBOARDING ENDPOINTS ---

@router.post("/lookup")
def lookup_member_phone(payload: PhoneLookupRequest, db: Session = Depends(get_db)):
    """
    Step 1 of Onboarding: Checks if phone exists and returns a masked name.
    """
    user = db.query(User).filter(User.phone_number == payload.phone_number).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Phone number not found in our directory.")
        
    if user.is_claimed:
        raise HTTPException(status_code=400, detail="This account has already been claimed. Please log in.")
        
    # Create a masked name: "Nandom Fyamya" -> "N***** F*****"
    def mask_word(word):
        if not word or len(word) <= 1: return word
        return word[0] + ("*" * (len(word) - 1))
        
    masked_first = mask_word(user.first_name)
    masked_last = mask_word(user.last_name)
    masked_full = f"{masked_first} {masked_last}"
    
    return {"masked_name": masked_full}


@router.post("/verify-name")
def verify_member_name(payload: NameVerifyRequest, db: Session = Depends(get_db)):
    """
    Step 2 of Onboarding: Fuzzy matches the typed name against the database name.
    """
    user = db.query(User).filter(User.phone_number == payload.phone_number).first()
    if not user or user.is_claimed:
        raise HTTPException(status_code=400, detail="Invalid request.")

    db_name = f"{user.first_name} {user.middle_name or ''} {user.last_name}".strip()
    match_score = fuzz.token_set_ratio(payload.typed_name.lower(), db_name.lower())
    
    if match_score < 80:
        raise HTTPException(status_code=400, detail="Name does not match our records. Please try again or contact support.")
        
    return {
        "message": "Verification Successful",
        "serial_number": user.serial_number,
        # Issue a temporary verification token so the next step is secure
        "verification_token": create_access_token(data={"sub": str(user.id), "scope": "claim_profile"}) 
    }


@router.put("/claim")
def claim_user_profile(
    payload: ClaimProfileRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user) 
):
    """
    Step 3 of Onboarding: Updates missing data and locks the account.
    """
    if current_user.phone_number != payload.phone_number:
        raise HTTPException(status_code=403, detail="Token mismatch.")
        
    if current_user.is_claimed:
        raise HTTPException(status_code=400, detail="Account already claimed.")
        
    current_user.email = payload.email
    current_user.sex = payload.sex
    current_user.contact_person_phone = payload.contact_person_phone
    if payload.profile_photo_url:
        current_user.profile_photo_url = payload.profile_photo_url
        
    current_user.is_claimed = True
    db.commit()
    return {"message": "Account successfully claimed. You may now log in."}


# --- CLOUDINARY UPLOAD SIGNATURE ---

@router.get("/generate-upload-signature")
def generate_upload_signature():
    """
    Returns a secure signature to the React frontend to allow direct image uploads.
    """
    timestamp = int(time.time())
    folder = "horyc_profiles"
    
    params_to_sign = {
        "timestamp": timestamp,
        "folder": folder
    }
    
    signature = cloudinary.utils.api_sign_request(params_to_sign, os.getenv("CLOUDINARY_API_SECRET"))
    
    return {
        "timestamp": timestamp,
        "signature": signature,
        "folder": folder,
        "api_key": os.getenv("CLOUDINARY_API_KEY"),
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME")
    }