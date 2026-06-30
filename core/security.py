import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt


# In production, this goes in a .env file. For MVP, we define it here.
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
#ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days so leaders don't get logged out constantly

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if the provided password matches the hash in the database."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    """Takes a plaintext string and returns a secure bcrypt hash."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode('utf-8')

def create_access_token(data: dict) -> str:
    """Generates the JWT token."""
    to_encode = data.copy()
    
    # Set expiration time (UTC)
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Create the JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """
    Generates a long-lived JWT specifically for refreshing the access token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt