import enum

from sqlalchemy import Column, String, Boolean, Date, ForeignKey, DateTime, UniqueConstraint, Enum
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
    
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_number = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    whatsapp_number = Column(String(20))
    dob = Column(Date, nullable=True) # Relaxed for data migration
    location_zone = Column(String(100), nullable=True) # Relaxed for data migration
    contact_person_name = Column(String(100), nullable=True) # Relaxed for data migration
    contact_person_relation = Column(String(50), nullable=True) # Relaxed for data migration
    hashed_password = Column(String(255), nullable=False) # MUST have a hashed password
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
    time_started = Column(DateTime(timezone=True), nullable=True)
    time_closed = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    attendances = relationship("AttendanceLog", back_populates="service", cascade="all, delete-orphan")

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    usher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    check_in_time = Column(DateTime(timezone=True), server_default=func.now())
    check_in_method = Column(Enum(AttendanceMethod, name="check_in_method_enum"), nullable=False, default=AttendanceMethod.QR_SCAN, server_default=AttendanceMethod.QR_SCAN.value)
    __table_args__ = (UniqueConstraint('user_id', 'service_id', name='_user_service_uc'),)
    user = relationship("User", foreign_keys=[user_id], back_populates="attendance_records")
    service = relationship("Service", back_populates="attendances")
    usher = relationship("User", foreign_keys=[usher_id])