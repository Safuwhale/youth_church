from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal
from uuid import UUID

class AttendanceScan(BaseModel):
    """Payload for Ushers scanning Members"""
    serial_number: str = Field(..., example="HORYC-001")
    service_id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    check_in_method: Literal["QR_SCAN", "SELF_SCAN", "MANUAL"] = Field(default="QR_SCAN", example="QR_SCAN")

class SelfCheckIn(BaseModel):
    """Payload for Members scanning the Sunday Service Poster"""
    service_id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000")

class AttendanceResponse(BaseModel):
    message: str
    user_name: Optional[str] = None
    check_in_time: Optional[datetime] = None
    check_in_method: Optional[Literal["QR_SCAN", "SELF_SCAN", "MANUAL"]] = None

    class Config:
        from_attributes = True


class ServiceAttendanceItem(BaseModel):
    id: UUID
    serial_number: str
    first_name: str
    last_name: str
    phone_number: str
    check_in_time: datetime
    check_in_method: Literal["QR_SCAN", "SELF_SCAN", "MANUAL"]


class ServiceAttendanceResponse(BaseModel):
    id: UUID
    title: str
    service_date: date
    is_active: bool
    attendance_count: int
    attendees: list[ServiceAttendanceItem]
        
        