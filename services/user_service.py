from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from models import User
from schemas.user import UserCreate
from core.security import get_password_hash 

def get_next_available_serial(db: Session) -> str:
    """
    Finds the lowest available sequential serial number, filling in any deleted gaps.
    """
    prefix = "HORYC-"
    
    # Get all existing serial numbers from the database
    existing_users = db.query(User.serial_number).filter(User.serial_number.like(f"{prefix}%")).all()
    
    # Extract the integer parts into a highly optimized Python set
    used_numbers = set()
    for (serial,) in existing_users:
        try:
            num = int(serial.split("-")[1])
            used_numbers.add(num)
        except (IndexError, ValueError):
            continue
            
    # Start counting from 1 and find the first number that isn't in the used set
    expected_number = 1
    while expected_number in used_numbers:
        expected_number += 1
        
    return f"{prefix}{expected_number:03d}"

def create_new_user(db: Session, user_data: UserCreate):
    # 1. Check if phone number already exists
    existing_user = db.query(User).filter(User.phone_number == user_data.phone_number).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A user with this phone number already exists."
        )

    # CONCURRENCY RETRY LOOP: Try to save up to 5 times if a collision happens
    max_retries = 5
    for attempt in range(max_retries):
        
        # 2. Find the lowest missing number (fills gaps)
        new_serial = get_next_available_serial(db)
        
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
            hashed_password=hashed_default_pwd, 
            role="member" 
        )

        # 5. Attempt to save to the database safely
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user  # Success! Exit the loop and return the user.
            
        except IntegrityError:
            # A collision happened! Roll back this failed attempt so the database doesn't lock up
            db.rollback()
            
            # If we've failed 5 times in a row, the server is under extreme load
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="The server is experiencing high traffic. Please wait a few seconds and click register again."
                )
            
            # Otherwise, the loop automatically restarts, finds the *new* gap, and tries again instantly!