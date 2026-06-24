from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from schemas.user import UserResponse

class CellCreate(BaseModel):
    name: str
    location: Optional[str] = None

class CellAssignment(BaseModel):
    user_id: UUID
    cell_group_id: UUID
    make_leader: bool = False # If True, upgrades them from member to leader

class CellDashboardResponse(BaseModel):
    cell_name: str
    total_members: int
    present_today: List[UserResponse]
    absent_today: List[UserResponse]