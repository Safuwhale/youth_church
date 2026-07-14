from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status
from models import User, CellGroup, Service, AttendanceLog
from schemas.cell import CellCreate, CellUpdate, CellAssignment, CellMembersAssignment, CellMembersRemoval


def _serialize_member(member: User):
    return {
        "id": member.id,
        "serial_number": member.serial_number,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "phone_number": member.phone_number,
        "location_zone": member.location_zone,
        "role": member.role,
        "is_active": member.is_active,
        "cell_group_id": member.cell_group_id,
    }

def create_cell(db: Session, cell_data: CellCreate):
    new_cell = CellGroup(name=cell_data.name)
    db.add(new_cell)
    db.commit()
    db.refresh(new_cell)
    return new_cell


def update_cell(db: Session, cell_group_id: str, cell_data: CellUpdate):
    cell = db.query(CellGroup).filter(CellGroup.id == cell_group_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell group not found")

    update_data = cell_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cell, key, value)

    db.commit()
    db.refresh(cell)
    return cell


def delete_cell(db: Session, cell_group_id: str):
    cell = db.query(CellGroup).filter(CellGroup.id == cell_group_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell group not found")

    db.query(User).filter(User.cell_group_id == cell.id).update({"cell_group_id": None}, synchronize_session=False)
    db.delete(cell)
    db.commit()


def list_cells(db: Session):
    cells = db.query(CellGroup).order_by(CellGroup.created_at.desc()).all()
    result = []
    for cell in cells:
        leaders = db.query(User).filter(User.cell_group_id == cell.id, User.role == "leader", User.is_active == True).order_by(User.first_name.asc()).all()
        result.append({
            "id": cell.id,
            "name": cell.name,
            "member_count": db.query(User).filter(User.cell_group_id == cell.id).count(),
            "leader_count": len(leaders),
            "leader_name": f"{leaders[0].first_name} {leaders[0].last_name}" if leaders else None,
            "leader_phone": leaders[0].phone_number if leaders else None,
        })
    return result


def list_cell_members(db: Session, cell_group_id: str):
    cell = db.query(CellGroup).filter(CellGroup.id == cell_group_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell group not found")

    members = db.query(User).filter(User.cell_group_id == cell.id).order_by(User.first_name.asc()).all()
    return [
        _serialize_member(member)
        for member in members
    ]

def assign_member(db: Session, assignment: CellAssignment):
    user = db.query(User).filter(User.id == assignment.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.cell_group_id = assignment.cell_group_id
    if assignment.make_leader:
        user.role = "leader"
        
    db.commit()
    db.refresh(user)
    return user


def assign_members_bulk(db: Session, cell_group_id: str, payload: CellMembersAssignment):
    cell = db.query(CellGroup).filter(CellGroup.id == cell_group_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell group not found")

    updated_members = []
    for user_id in payload.user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            continue
        user.cell_group_id = cell.id
        if payload.make_leader:
            user.role = "leader"
        updated_members.append(user)

    db.commit()
    for member in updated_members:
        db.refresh(member)

    return {"message": "Members assigned successfully.", "updated_count": len(updated_members)}


def remove_members_bulk(db: Session, cell_group_id: str, payload: CellMembersRemoval):
    cell = db.query(CellGroup).filter(CellGroup.id == cell_group_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell group not found")

    removed_count = 0
    for user_id in payload.user_ids:
        user = db.query(User).filter(User.id == user_id, User.cell_group_id == cell.id).first()
        if not user:
            continue
        user.cell_group_id = None
        if user.role == "leader":
            user.role = "member"
        removed_count += 1

    db.commit()
    return {"message": "Members removed successfully.", "removed_count": removed_count}

def generate_leader_dashboard(db: Session, current_user: User):
    """
    Returns the cell dashboard including the 7-week attendance history for all members.
    """
    if not current_user.cell_group_id:
        raise HTTPException(status_code=404, detail="You are not assigned to a cell group.")

    cell = db.query(CellGroup).filter(CellGroup.id == current_user.cell_group_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell group not found.")

    # 1. Get the last 7 active services, ordered oldest to newest
    last_7_services = db.query(Service).filter(Service.is_active == True).order_by(desc(Service.service_date)).limit(7).all()
    # Reverse to chronological order (oldest first, newest last) for the UI dots
    last_7_services.reverse()
    
    # Pre-extract IDs for faster lookup
    service_ids = [s.id for s in last_7_services]

    leader = db.query(User).filter(
        User.cell_group_id == cell.id, 
        User.role == "leader"
    ).first()

    all_members = db.query(User).filter(User.cell_group_id == cell.id).all()
    
    # 2. Build the member payload and calculate history
    enriched_members = []
    
    for member in all_members:
        # Get all attendance records for this specific member for the last 7 services
        member_attendances = db.query(AttendanceLog).filter(
            AttendanceLog.user_id == member.id,
            AttendanceLog.service_id.in_(service_ids)
        ).all()
        
        attended_service_ids = {att.service_id for att in member_attendances}
        
        # Build the exact array the React component expects
        history_array = []
        for svc in last_7_services:
            if svc.id in attended_service_ids:
                history_array.append("attended")
            else:
                history_array.append("absent")
                
        # If there are fewer than 7 services in the whole database, pad the front
        while len(history_array) < 7:
            history_array.insert(0, "no_service")

        # Create a dictionary matching UserDirectoryItem, but inject the history array
        member_dict = {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "serial_number": member.serial_number,
            "phone_number": member.phone_number,
            "location_zone": member.location_zone,
            "role": member.role,
            "attendance_history": history_array
        }
        enriched_members.append(member_dict)

    # For the today views (present/absent), we just look at the last service in the list
    present_today = []
    absent_today = []
    
    if last_7_services:
        latest_service_id = last_7_services[-1].id
        for m_dict in enriched_members:
            if m_dict["attendance_history"][-1] == "attended":
                present_today.append(m_dict)
            else:
                absent_today.append(m_dict)
    else:
        # Edge case: No services exist in the database at all yet
        absent_today = enriched_members

    return {
        "cell_name": cell.name,
        "total_members": len(all_members),
        "leader_name": f"{leader.first_name} {leader.last_name}" if leader else None,
        "leader_phone": leader.phone_number if leader else None,
        "members": enriched_members,
        "present_today": present_today,
        "absent_today": absent_today
    }