from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models import User, CellGroup, Service, AttendanceLog
from schemas.cell import CellCreate, CellAssignment

def create_cell(db: Session, cell_data: CellCreate):
    new_cell = CellGroup(name=cell_data.name, location=cell_data.location)
    db.add(new_cell)
    db.commit()
    db.refresh(new_cell)
    return new_cell

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

def generate_leader_dashboard(db: Session, current_user: User):
    if current_user.role not in ["leader", "admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized to view cell dashboards.")
        
    if not current_user.cell_group_id:
        raise HTTPException(status_code=400, detail="You are not assigned to a cell group.")

    cell = db.query(CellGroup).filter(CellGroup.id == current_user.cell_group_id).first()
    
    # Get all active members of this cell
    cell_members = db.query(User).filter(
        User.cell_group_id == cell.id, 
        User.is_active == True
    ).all()

    # Find the active service
    active_service = db.query(Service).filter(Service.is_active == True).first()
    
    present = []
    absent = []

    if not active_service:
        # If no service is running, everyone is "absent" by default
        absent = cell_members
    else:
        # Cross-reference attendance
        for member in cell_members:
            attended = db.query(AttendanceLog).filter(
                AttendanceLog.user_id == member.id,
                AttendanceLog.service_id == active_service.id
            ).first()
            
            if attended:
                present.append(member)
            else:
                absent.append(member)

    return {
        "cell_name": cell.name,
        "total_members": len(cell_members),
        "present_today": present,
        "absent_today": absent
    }