import enum
from datetime import datetime

from sqlalchemy import Column, String, Boolean, Date, ForeignKey, DateTime, UniqueConstraint, Enum, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base


class AttendanceMethod(enum.Enum):
    QR_SCAN = "QR_SCAN"
    SELF_SCAN = "SELF_SCAN"
    MANUAL = "MANUAL"

class CellGroup(Base):
    __tablename__ = "cell_groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationship to link back to the users in this cell
    members = relationship("User", back_populates="cell_group")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")
    
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_number = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    phone_number = Column(String(20), nullable=False, index=True)
    whatsapp_number = Column(String(20))
    dob = Column(Date, nullable=True) 
    location_zone = Column(String(100), nullable=True) 
    contact_person_name = Column(String(100), nullable=True) 
    contact_person_relation = Column(String(50), nullable=True)
    contact_person_phone = Column(String(20), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=True)
    sex = Column(String(20), nullable=True)
    profile_photo_url = Column(String(500), nullable=True)
    is_claimed = Column(Boolean, default=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="member", index=True)
    is_active = Column(Boolean, default=True, index=True)
    token_version = Column(Integer, nullable=False, default=0)
    cell_group_id = Column(UUID(as_uuid=True), ForeignKey("cell_groups.id", ondelete="SET NULL"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    cell_group = relationship("CellGroup", back_populates="members")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceLog", foreign_keys="[AttendanceLog.user_id]", back_populates="user", cascade="all, delete-orphan")

class Service(Base):
    __tablename__ = "services"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False) 
    service_date = Column(Date, nullable=False, index=True)
    is_active = Column(Boolean, default=False, index=True)
    time_started = Column(DateTime(timezone=True), nullable=True)
    time_closed = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    attendances = relationship("AttendanceLog", back_populates="service", cascade="all, delete-orphan")

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    usher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    check_in_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    check_in_method = Column(Enum(AttendanceMethod, name="check_in_method_enum"), nullable=False, default=AttendanceMethod.QR_SCAN, server_default=AttendanceMethod.QR_SCAN.value)
    __table_args__ = (
        UniqueConstraint('user_id', 'service_id', name='_user_service_uc'),
        Index('ix_attendance_logs_service_usher', 'service_id', 'usher_id'),
        Index('ix_attendance_logs_service_time', 'service_id', 'check_in_time'),
    )
    
    user = relationship("User", foreign_keys=[user_id], back_populates="attendance_records")
    service = relationship("Service", back_populates="attendances")
    usher = relationship("User", foreign_keys=[usher_id])