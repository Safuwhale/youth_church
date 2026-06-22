from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, String, Boolean, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.sql import func
import uuid

# ==========================================
# 1. DATABASE SETUP
# ==========================================
# Replace 'username', 'password', and 'dbname'
SQLALCHEMY_DATABASE_URL = "postgresql://username:password@localhost/church_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. DATABASE MODELS
# ==========================================
class CellGroup(Base):
    __tablename__ = "cell_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    meeting_location = Column(String(150))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("User", back_populates="cell_group")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_number = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    whatsapp_number = Column(String(20))
    dob = Column(Date, nullable=False)
    location_zone = Column(String(100), nullable=False)
    contact_person_name = Column(String(100), nullable=False)
    contact_person_relation = Column(String(50), nullable=False)
    role = Column(String(20), default="member") 
    is_active = Column(Boolean, default=True) 
    
    cell_group_id = Column(UUID(as_uuid=True), ForeignKey("cell_groups.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cell_group = relationship("CellGroup", back_populates="members")
    attendance_records = relationship("AttendanceLog", foreign_keys="[AttendanceLog.user_id]", back_populates="user", cascade="all, delete-orphan")

class Service(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False) 
    service_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    attendances = relationship("AttendanceLog", back_populates="service", cascade="all, delete-orphan")

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    usher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    check_in_time = Column(DateTime(timezone=True), server_default=func.now())
    check_in_method = Column(String(20), default="QR_SCAN")

    __table_args__ = (UniqueConstraint('user_id', 'service_id', name='_user_service_uc'),)

    user = relationship("User", foreign_keys=[user_id], back_populates="attendance_records")
    service = relationship("Service", back_populates="attendances")
    usher = relationship("User", foreign_keys=[usher_id])

# ==========================================
# 3. FASTAPI INITIALIZATION
# ==========================================
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Youth Church Attendance API",
    description="API backend for the Flipped QR check-in system.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"status": "online", "message": "Youth Church API is running"}