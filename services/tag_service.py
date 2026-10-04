from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models import Tag, User
from schemas.tag import TagCreate


def list_tags(db: Session):
    return db.query(Tag).filter(Tag.is_archived == False).order_by(Tag.name.asc()).all()


def create_tag(db: Session, payload: TagCreate):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty.")
    existing = db.query(Tag).filter(Tag.name.ilike(name), Tag.is_archived == False).first()
    if existing:
        raise HTTPException(status_code=409, detail="That tag already exists.")
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def archive_tag(db: Session, tag_id: str):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.is_archived == False).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found.")
    tag.is_archived = True
    db.commit()


def replace_member_tags(db: Session, user_id: str, tag_ids: list):
    user = db.query(User).filter(User.id == user_id, User.is_archived == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found.")
    tags = db.query(Tag).filter(Tag.id.in_(tag_ids), Tag.is_archived == False).all() if tag_ids else []
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tags are invalid.")
    user.tags = tags
    db.commit()
    return tags