import os
import secrets
import hmac
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import bcrypt
import hashlib
import secrets
from jose import jwt

load_dotenv()  # Load environment variables from .env file
# In production, this goes in a .env file. For MVP, we define it here.
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    raise RuntimeError("COOKIE_SAMESITE must be lax, strict, or none")
if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
    raise RuntimeError("COOKIE_SECURE must be true when COOKIE_SAMESITE is none")
CSRF_COOKIE_NAME = "csrf_token"


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_is_valid(cookie_token: str | None, header_token: str | None) -> bool:
    return bool(cookie_token and header_token and hmac.compare_digest(cookie_token, header_token))

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

def create_refresh_token(data: dict | None = None):
    """
    Generates a refresh token string.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Creates a stable digest for storing refresh tokens server-side."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()