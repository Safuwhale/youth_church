from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# We will update this URL shortly
SQLALCHEMY_DATABASE_URL = "postgresql://church_admin:admin123@localhost/church_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()