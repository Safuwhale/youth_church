from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv() 
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

# --- INCREASED POOL SIZE FOR HIGH TRAFFIC ---
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_pre_ping=True,
    pool_size=20,        # Holds 20 connections open and ready at all times
    max_overflow=30,     # Allows up to 30 additional connections during a traffic spike
    pool_timeout=30      # Gives the server 30 seconds to find an open connection before failing
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()