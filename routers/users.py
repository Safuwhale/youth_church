from fastapi import APIRouter, Depends, status, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from schemas.user import (
    UserCreate, UserResponse, UserLogin, TokenResponse, UserUpdate, 
    UserDirectoryItem, UserRoleUpdate, PasswordChangeRequest,
    PhoneLookupRequest, NameVerifyRequest, ClaimProfileRequest
)
from sqlalchemy import desc
from services.user_service import create_new_user
from database import get_db
from models import User, CellGroup, Service, AttendanceLog
from core.security import verify_password, create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM, COOKIE_SECURE, get_password_hash
from jose import jwt, JWTError
from core.dependencies import get_current_user
from sqlalchemy import or_  
import os
import time
from datetime import datetime
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

    users = query.order_by(User.created_at.desc()).all()
    
    #Fetch last 7 services
    last_7_services = db.query(Service).order_by(desc(Service.service_date)).limit(7).all()
    last_7_services.reverse()
    service_ids = [s.id for s in last_7_services]
    
    #Fetch bulk attendance logs for fast streak calculation
    user_ids = [u.id for u in users]
    bulk_logs = db.query(AttendanceLog).filter(
        AttendanceLog.service_id.in_(service_ids),
        AttendanceLog.user_id.in_(user_ids)
    ).all()
    
    attended_lookup = {(log.user_id, log.service_id) for log in bulk_logs}
    
    #Fetch Cell Groups for mapping names
    cells = db.query(CellGroup).all()
    cell_map = {c.id: c.name for c in cells}

    # 4. Compile the rich payload
    enriched_users = []
    for u in users:
        history_array = []
        for svc in last_7_services:
            if (u.id, svc.id) in attended_lookup:
                history_array.append("attended")
            else:
                history_array.append("absent")
        
        while len(history_array) < 7:
            history_array.insert(0, "no_service")
            
        user_dict = u.__dict__.copy()
        user_dict["attendance_history"] = history_array
        user_dict["cell_group_name"] = cell_map.get(u.cell_group_id, "Unassigned")
        enriched_users.append(user_dict)
        
    return enriched_users


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
        "verification_token": create_access_token(data={"sub": str(user.id), "role": user.role})
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
    current_user.dob = payload.dob
    current_user.location_zone = payload.location_zone
    current_user.whatsapp_number = payload.whatsapp_number
    current_user.contact_person_name = payload.contact_person_name
    current_user.contact_person_relation = payload.contact_person_relation
    current_user.contact_person_phone = payload.contact_person_phone
    if payload.profile_photo_url:
        current_user.profile_photo_url = payload.profile_photo_url
        
    current_user.is_claimed = True
    db.commit()
    return {"message": "Account successfully claimed. You may now log in."}


# --- CLOUDINARY UPLOAD SIGNATURE ---

@router.get("/generate-upload-signature")
def generate_upload_signature(identifier: str = "new_user"):
    """
    Returns a secure signature to the React frontend to allow direct image uploads.
    """
    # Create the timestamped file name (e.g., user_0810000000_20260715_120737)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"user_{identifier}_{timestamp_str}"
    
    timestamp = int(time.time())
    folder = "horyc_profiles"
    
    params_to_sign = {
        "timestamp": timestamp,
        "folder": folder,
        "public_id": unique_filename
    }
    
    signature = cloudinary.utils.api_sign_request(params_to_sign, os.getenv("CLOUDINARY_API_SECRET"))
    
    return {
        "timestamp": timestamp,
        "signature": signature,
        "folder": folder,
        "public_id": unique_filename,
        "api_key": os.getenv("CLOUDINARY_API_KEY"),
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME")
    }

from pydantic import BaseModel
class PhotoUpdate(BaseModel):
    profile_photo_url: str    
@router.patch("/{user_id}/photo")
def update_user_photo(user_id: str, payload: PhotoUpdate, db: Session = Depends(get_db)):
    """
    Updates a user's profile photo. 
    Used immediately after a new user registers and uploads their photo to Cloudinary.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    user.profile_photo_url = payload.profile_photo_url
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Profile photo updated successfully.", 
        "profile_photo_url": user.profile_photo_url
    }