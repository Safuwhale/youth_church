from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models import User
from schemas.user import UserCreate
from core.security import get_password_hash  # Import the new hashing function

def generate_serial_number(db: Session) -> str:
    """Generates a sequential serial number in the format HORYC-001."""
    prefix = "HORYC-"
    
    # Query the database for the most recently created user
    last_user = db.query(User).filter(User.serial_number.like(f"{prefix}%")).order_by(User.created_at.desc()).first()
    
    if not last_user:
        # If the database is empty, this is user #1
        return f"{prefix}001"
    
    try:
        # Extract the integer part: split "HORYC-005" at the "-" and take the "005"
        last_number = int(last_user.serial_number.split("-")[1])
        new_number = last_number + 1
    except (IndexError, ValueError):
        # Failsafe in case a manually edited database entry breaks the format
        new_number = 1
        
    # Format the new number with leading zeros (e.g., 1 becomes 001, 10 becomes 010)
    return f"{prefix}{new_number:03d}"

def create_new_user(db: Session, user_data: UserCreate):
    # 1. Check if phone number already exists
    existing_user = db.query(User).filter(User.phone_number == user_data.phone_number).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A user with this phone number already exists."
        )

    # 2. Generate sequential serial number
    new_serial = generate_serial_number(db)
    
    # 3. Hash the serial number to serve as the default password
    hashed_default_pwd = get_password_hash(new_serial)

    # 4. Build the database object
    db_user = User(
        serial_number=new_serial,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number,
        whatsapp_number=user_data.whatsapp_number,
        dob=user_data.dob,
        location_zone=user_data.location_zone,
        contact_person_name=user_data.contact_person_name,
        contact_person_relation=user_data.contact_person_relation,
        hashed_password=hashed_default_pwd, # Save the securely hashed password
        role="member" 
    )

    # 5. Save to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user