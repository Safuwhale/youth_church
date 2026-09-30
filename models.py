import enum

from sqlalchemy import Column, String, Boolean, Date, ForeignKey, DateTime, UniqueConstraint, Enum, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base


class AttendanceMethod(enum.Enum):
    QR_SCAN = "QR_SCAN"
    SELF_SCAN = "SELF_SCAN"
    MANUAL = "MANUAL"

user_tags = Table(
    "user_tags",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class CellGroup(Base):
    __tablename__ = "cell_groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    # Relationship to link back to the users in this cell
    members = relationship("User", back_populates="cell_group")
    
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_number = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    phone_number = Column(String(20), nullable=False)
    whatsapp_number = Column(String(20))
    dob = Column(Date, nullable=True) 
    location_zone = Column(String(100), nullable=True) 
    contact_person_name = Column(String(100), nullable=True) 
    contact_person_relation = Column(String(50), nullable=True)
    contact_person_phone = Column(String(20), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=True)
    sex = Column(String(20), nullable=True)
    profile_photo_url = Column(String(500), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="member") 
    is_active = Column(Boolean, default=True) 
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    cell_group_id = Column(UUID(as_uuid=True), ForeignKey("cell_groups.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cell_group = relationship("CellGroup", back_populates="members")
    attendance_records = relationship("AttendanceLog", foreign_keys="[AttendanceLog.user_id]", back_populates="user")
    tags = relationship("Tag", secondary=user_tags, back_populates="users")

class Service(Base):
    __tablename__ = "services"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False) 
    service_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False)
    time_started = Column(DateTime(timezone=True), nullable=True)
    time_closed = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    attendances = relationship("AttendanceLog", back_populates="service")

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    usher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    check_in_time = Column(DateTime(timezone=True), server_default=func.now())
    check_in_method = Column(Enum(AttendanceMethod, name="check_in_method_enum"), nullable=False, default=AttendanceMethod.QR_SCAN, server_default=AttendanceMethod.QR_SCAN.value)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    __table_args__ = (UniqueConstraint('user_id', 'service_id', name='_user_service_uc'),)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="attendance_records")
    service = relationship("Service", back_populates="attendances")
    usher = relationship("User", foreign_keys=[usher_id])


class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), unique=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    users = relationship("User", secondary=user_tags, back_populates="tags")