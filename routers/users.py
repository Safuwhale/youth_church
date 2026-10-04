from fastapi import APIRouter, Depends, status, HTTPException, Response, Cookie, Header, UploadFile, File
from sqlalchemy.orm import Session, selectinload
from schemas.user import (
    UserCreate, UserResponse, UserLogin, TokenResponse, UserUpdate, 
    UserDirectoryItem, UserRoleUpdate, PasswordChangeRequest,
)
from sqlalchemy import desc
from services.user_service import create_new_user
from database import get_db
from models import User, CellGroup, Service, AttendanceLog
from core.security import verify_password, create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM, COOKIE_SECURE, COOKIE_SAMESITE, CSRF_COOKIE_NAME, create_csrf_token, csrf_is_valid, get_password_hash
from jose import jwt, JWTError
from core.dependencies import get_current_user
from sqlalchemy import or_  
import os
import time
from datetime import datetime
import cloudinary
import cloudinary.utils
import pandas as pd
import io
from dotenv import load_dotenv
from schemas.tag import MemberTagsUpdate
from services.tag_service import replace_member_tags

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

@router.post("/admin-create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized.")
    return create_new_user(db=db, user_data=user)

@router.post("/admin-bulk")
def admin_bulk_create_users(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized.")
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Upload an Excel or CSV file.")

    try:
        contents = file.file.read()
        reader = pd.read_csv if file.filename.lower().endswith(".csv") else pd.read_excel
        dataframe = reader(io.BytesIO(contents))
        dataframe = dataframe.dropna(axis=1, how="all")
        normalized = {str(column).strip().lower(): column for column in dataframe.columns}
        name_column = normalized.get("member name") or normalized.get("name")
        phone_column = normalized.get("phone") or normalized.get("phone number")
        if not name_column:
            raw_dataframe = reader(io.BytesIO(contents), header=None)
            header_matches = raw_dataframe.apply(
                lambda row: row.astype(str).str.strip().str.lower().eq("member name").any(), axis=1
            )
            if not header_matches.any():
                raise HTTPException(status_code=400, detail="The sheet must contain a 'Member Name' or 'Name' column.")
            header_index = header_matches[header_matches].index[0]
            dataframe = raw_dataframe.iloc[header_index + 1:].copy()
            dataframe.columns = raw_dataframe.iloc[header_index]
            dataframe = dataframe.dropna(axis=1, how="all")
            normalized = {str(column).strip().lower(): column for column in dataframe.columns}
            name_column = normalized.get("member name") or normalized.get("name")
            phone_column = normalized.get("phone") or normalized.get("phone number")
        if not name_column:
            raise HTTPException(status_code=400, detail="The sheet must contain a 'Member Name' or 'Name' column.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the spreadsheet: {exc}") from exc

    results = {"created": [], "skipped": []}
    for row_number, row in dataframe.iterrows():
        raw_name = str(row.get(name_column, "")).strip()
        if not raw_name or raw_name.lower() == "nan":
            results["skipped"].append({"row": row_number + 2, "reason": "Member name is empty."})
            continue
        name_parts = raw_name.split()
        if len(name_parts) < 2:
            results["skipped"].append({"row": row_number + 2, "name": raw_name, "reason": "Both first and last name are required."})
            continue
        raw_phone = row.get(phone_column) if phone_column else None
        phone = None if pd.isna(raw_phone) else str(raw_phone).strip()
        if phone and phone.endswith(".0"):
            phone = phone[:-2]
        payload = UserCreate(first_name=name_parts[0], last_name=" ".join(name_parts[1:]), phone_number=phone or None)
        try:
            member = create_new_user(db=db, user_data=payload)
            results["created"].append({"row": row_number + 2, "name": raw_name, "serial_number": member.serial_number})
        except HTTPException as exc:
            results["skipped"].append({"row": row_number + 2, "name": raw_name, "reason": exc.detail})

    return {"filename": file.filename, "created_count": len(results["created"]), "skipped_count": len(results["skipped"]), **results}

@router.post("/login")
def login_user(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    """
    Authenticates a user, sets an httpOnly refresh cookie, and returns a short-lived access token.
    """
    user = db.query(User).filter(User.phone_number == credentials.phone_number, User.is_archived == False).first()

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
    token_data = {"sub": str(user.id), "role": user.role, "token_version": user.token_version}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # Set the Refresh Token as a secure, httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,             # Critical: JavaScript cannot read this
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=30 * 24 * 60 * 60  # 30 days in seconds
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=create_csrf_token(),
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=30 * 24 * 60 * 60,
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

    query = db.query(User).options(selectinload(User.tags)).filter(User.is_archived == False)
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
    last_7_services = db.query(Service).filter(Service.is_archived == False).order_by(desc(Service.service_date)).limit(7).all()
    last_7_services.reverse()
    service_ids = [s.id for s in last_7_services]
    
    #Fetch bulk attendance logs for fast streak calculation
    user_ids = [u.id for u in users]
    bulk_logs = db.query(AttendanceLog).filter(
        AttendanceLog.service_id.in_(service_ids),
        AttendanceLog.user_id.in_(user_ids),
        AttendanceLog.is_archived == False
    ).all()
    
    attended_lookup = {(log.user_id, log.service_id) for log in bulk_logs}
    
    #Fetch Cell Groups for mapping names
    cells = db.query(CellGroup).filter(CellGroup.is_archived == False).all()
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
        user_dict["tags"] = [tag.name for tag in u.tags if not tag.is_archived]
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

    user = db.query(User).filter(User.id == user_id, User.is_archived == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized.")
    user = db.query(User).filter(User.id == user_id, User.is_archived == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = False
    user.is_archived = True
    db.query(AttendanceLog).filter(AttendanceLog.user_id == user.id).update({"is_archived": True}, synchronize_session=False)
    db.commit()

@router.put("/{user_id}/tags", response_model=list[dict])
def update_member_tags(user_id: str, payload: MemberTagsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized.")
    return [{"id": tag.id, "name": tag.name} for tag in replace_member_tags(db, user_id, payload.tag_ids)]

@router.post("/refresh")
def refresh_access_token(
    response: Response,
    refresh_token: str = Cookie(None),
    csrf_token: str = Cookie(None),
    csrf_header: str | None = Header(None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db),
):
    """
    Reads the httpOnly refresh_token cookie and returns a new access_token if valid.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing. Please log in again.")
    if not csrf_is_valid(csrf_token, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")
        
    try:
        # Decode the refresh token cookie
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload.")
            
        # Verify user still exists and is not banned
        user = db.query(User).filter(User.id == user_id, User.is_archived == False).first()
        if not user or not user.is_active or user.is_archived:
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

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(
    response: Response,
    csrf_token: str = Cookie(None),
    csrf_header: str | None = Header(None, alias="X-CSRF-Token"),
):
    if not csrf_is_valid(csrf_token, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")
    response.delete_cookie("refresh_token", secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)
    response.delete_cookie(CSRF_COOKIE_NAME, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)

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