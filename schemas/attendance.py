from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class AttendanceScan(BaseModel):
    """Payload for Ushers scanning Members"""
    serial_number: str = Field(..., example="HORYC-001")
    service_id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    check_in_method: str = Field(default="QR_SCAN", example="QR_SCAN")

class SelfCheckIn(BaseModel):
    """Payload for Members scanning the Sunday Service Poster"""
    service_id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000")

class AttendanceResponse(BaseModel):
    message: str
    user_name: Optional[str] = None
    check_in_time: Optional[datetime] = None

    class Config:
        from_attributes = True
        
        