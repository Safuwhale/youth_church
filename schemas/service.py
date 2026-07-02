from pydantic import BaseModel, Field
from datetime import date, datetime
from uuid import UUID
from typing import Optional

class ServiceCreate(BaseModel):
    title: str = Field(..., example="Sunday Youth Service")
    service_date: date = Field(..., example="2026-06-28")

class ServiceResponse(BaseModel):
    id: UUID
    title: str
    service_date: date
    is_active: bool
    time_started: Optional[datetime] = None 
    time_closed: Optional[datetime] = None
    attendance_count: Optional[int] = 0

    class Config:
        from_attributes = True