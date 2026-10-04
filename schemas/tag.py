from pydantic import BaseModel, Field
from uuid import UUID


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class TagResponse(BaseModel):
    id: UUID
    name: str
    is_archived: bool = False

    class Config:
        from_attributes = True


class MemberTagsUpdate(BaseModel):
    tag_ids: list[UUID]