from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.dependencies import get_current_user
from models import User
from schemas.tag import TagCreate, TagResponse
from services.tag_service import archive_tag, create_tag, list_tags

router = APIRouter()


def require_manager(current_user: User):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized.")


@router.get("", response_model=list[TagResponse])
def get_tags(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_manager(current_user)
    return list_tags(db)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def add_tag(payload: TagCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_manager(current_user)
    return create_tag(db, payload)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag(tag_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_manager(current_user)
    archive_tag(db, tag_id)