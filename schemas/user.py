from pydantic import BaseModel, Field, validator, EmailStr
from datetime import date
from typing import Optional, Literal
from uuid import UUID


class PhoneLookupRequest(BaseModel):
    phone_number: str

class NameVerifyRequest(BaseModel):
    phone_number: str
    typed_name: str

class ClaimProfileRequest(BaseModel):
    phone_number: str
    email: Optional[EmailStr] = None
    sex: Optional[str] = None
    contact_person_phone: Optional[str] = None
    profile_photo_url: Optional[str] = None

# Payload expected from the React frontend
class UserCreate(BaseModel):
    first_name: str = Field(..., example="Nandom")
    last_name: str = Field(..., example="Fyamya")
    phone_number: str = Field(..., example="08012345678")
    whatsapp_number: Optional[str] = None
    whatsapp_same_as_phone: bool = True 
    dob: date = Field(..., example="2003-05-14")
    location_zone: str = Field(..., example="Wuse 2")
    contact_person_name: str = Field(..., example="Mrs. Fyamya")
    contact_person_relation: str = Field(..., example="Mother")

    @validator('whatsapp_number', always=True)
    def set_whatsapp_number(cls, v, values):
        if values.get('whatsapp_same_as_phone') and 'phone_number' in values:
            return values['phone_number']
        return v

# Payload returned to the frontend (excludes sensitive internal data)
class UserResponse(BaseModel):
    id: UUID
    serial_number: str
    first_name: str
    last_name: str
    phone_number: str
    whatsapp_number: Optional[str] = None
    dob: Optional[date] = None
    location_zone: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_relation: Optional[str] = None
    role: str
    is_active: bool
    cell_group_id: Optional[UUID] = None

    class Config:
        from_attributes = True

#FOR LOGIN ---
class UserLogin(BaseModel):
    phone_number: str = Field(..., example="08012345678")
    password: str = Field(..., example="HORYC-001") # They use their serial number here

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_same_as_phone: Optional[bool] = None
    dob: Optional[date] = None
    location_zone: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_relation: Optional[str] = None
    new_password: Optional[str] = None 


class UserDirectoryItem(BaseModel):
    id: UUID
    serial_number: str
    first_name: str
    last_name: str
    phone_number: str
    location_zone: Optional[str] = None
    role: str
    is_active: bool
    cell_group_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: Literal["member", "usher", "leader", "hod", "admin"]


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str