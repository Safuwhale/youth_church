from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from schemas.user import UserResponse

class CellCreate(BaseModel):
    name: str


class CellUpdate(BaseModel):
    name: Optional[str] = None

class CellAssignment(BaseModel):
    user_id: UUID
    cell_group_id: UUID
    make_leader: bool = False # If True, upgrades them from member to leader


class CellMembersAssignment(BaseModel):
    user_ids: List[UUID] = Field(default_factory=list)
    make_leader: bool = False


class CellMembersRemoval(BaseModel):
    user_ids: List[UUID] = Field(default_factory=list)


class CellGroupResponse(BaseModel):
    id: UUID
    name: str
    member_count: int = 0
    leader_count: int = 0
    leader_name: Optional[str] = None
    leader_phone: Optional[str] = None

    class Config:
        from_attributes = True

class CellDashboardResponse(BaseModel):
    cell_name: str
    total_members: int
    present_today: List[UserResponse]
    absent_today: List[UserResponse]