from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models import User, Service, AttendanceLog
from schemas.attendance import AttendanceScan
import io
import csv

def process_scan(db: Session, scan_data: AttendanceScan, current_user: User):
    """Core check-in logic for Ushers scanning members into a specific service."""
    
    # 1. Consistency Check: Role Authorization
    if current_user.role not in ["usher", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    # 2. Check for the SPECIFIC service requested by the scanner
    target_service = db.query(Service).filter(Service.id == scan_data.service_id).first()
    
    if not target_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="The selected service could not be found."
        )
        
    if not target_service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="This service is closed. You cannot scan members into a closed service."
        )

    # 3. Find User by serial_number
    member = db.query(User).filter(User.serial_number == scan_data.serial_number).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Member not found."
        )

    # 4. Check if the user is soft-deleted
    if not member.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This user account has been deactivated."
        )

    # 5. Duplicate Failsafe (Triggers the yellow frontend screen)
    existing = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == member.id,
        AttendanceLog.service_id == target_service.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Member already checked in."
        )

    # 6. Save with Usher context
    new_log = AttendanceLog(
        user_id=member.id,
        service_id=target_service.id,
        usher_id=current_user.id, # Tracks exactly who scanned this member
        check_in_method=getattr(scan_data, 'check_in_method', 'QR_SCAN')
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return new_log


def process_self_checkin(db: Session, current_user: User, service_id: str):
    """Used by Members scanning the Service QR code poster."""
    
    # 1. Verify the service exists and is actually open
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")

    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="This service is not currently open for check-in."
        )

    # 2. Duplicate Failsafe for Self-Check-in
    existing_log = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.service_id == service.id
    ).first()

    if existing_log:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Already checked in."
        )

    # 3. Log the check-in with the SELF_SCAN method
    new_log = AttendanceLog(
        user_id=current_user.id,
        service_id=service.id,
        check_in_method="SELF_SCAN"
    )

    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return new_log


def export_attendance_csv(db: Session, current_user: User):
    """Generates a CSV of the currently active service attendance."""
    
    # Security: Only HOD or Admin can export the whole church data
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to export data.")
        
    active_service = db.query(Service).filter(Service.is_active == True).first()
    if not active_service:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="There is no active service to export.")
        
    logs = db.query(AttendanceLog).filter(AttendanceLog.service_id == active_service.id).all()
    
    # Create the CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write the Header row
    writer.writerow(["Date", "Service Title", "Serial Number", "First Name", "Last Name", "Check-in Time", "Method"])
    
    # Write the Data rows
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        writer.writerow([
            active_service.service_date,
            active_service.title,
            user.serial_number,
            user.first_name,
            user.last_name,
            log.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if log.check_in_time else "N/A",
            log.check_in_method
        ])
        
    return output.getvalue()