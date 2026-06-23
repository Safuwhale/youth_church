from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID

class ServiceCreate(BaseModel):
    title: str = Field(..., example="Sunday Youth Service")
    service_date: date = Field(..., example="2026-06-28")

class ServiceResponse(BaseModel):
    id: UUID
    title: str
    service_date: date
    is_active: bool

    class Config:
        from_attributes = True