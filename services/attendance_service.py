from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models import User, Service, AttendanceLog
from schemas.attendance import AttendanceScan
import io
import csv

def process_scan(db: Session, scan_data: AttendanceScan):
    # 1. Find the currently active service (The Gate)
    active_service = db.query(Service).filter(Service.is_active == True).first()
    if not active_service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="There is no active service right now. Please ask the HOD to create a service."
        )

    # 2. Find the user by their serial number
    user = db.query(User).filter(User.serial_number == scan_data.serial_number).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with serial number {scan_data.serial_number} not found."
        )

    # 3. Check if the user is soft-deleted
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This user account has been deactivated."
        )

    # 4. Duplicate Failsafe: Has this user already been scanned for this specific service?
    existing_log = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == user.id,
        AttendanceLog.service_id == active_service.id
    ).first()

    if existing_log:
        # We don't throw an error here, we just return a friendly message so the Usher knows
        # the app didn't crash, the person is just already checked in.
        return {
            "message": f"Already checked in! Welcome back, {user.first_name}.",
            "user_name": f"{user.first_name} {user.last_name}",
            "check_in_time": existing_log.check_in_time
        }

    # 5. Log the new attendance
    new_log = AttendanceLog(
        user_id=user.id,
        service_id=active_service.id,
        check_in_method=scan_data.check_in_method
        # Note: usher_id is left null for MVP until we enforce Usher JWT tokens
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return {
        "message": "Check-in successful!",
        "user_name": f"{user.first_name} {user.last_name}",
        "check_in_time": new_log.check_in_time
    }
    
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

    # 2. Duplicate Failsafe
    existing_log = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.service_id == service.id
    ).first()

    if existing_log:
        return {
            "message": f"Already checked in! Welcome back, {current_user.first_name}.",
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "check_in_time": existing_log.check_in_time
        }

    # 3. Log the check-in with the SELF_SCAN method
    new_log = AttendanceLog(
        user_id=current_user.id,
        service_id=service.id,
        check_in_method="SELF_SCAN"
    )

    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return {
        "message": "Self check-in successful!",
        "user_name": f"{current_user.first_name} {current_user.last_name}",
        "check_in_time": new_log.check_in_time
}
    
def export_attendance_csv(db: Session, current_user: User):
    """Generates a CSV of the currently active service attendance."""
    # Security: Only HOD or Admin can export the whole church data
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=403, detail="Not authorized to export data.")
        
    active_service = db.query(Service).filter(Service.is_active == True).first()
    if not active_service:
        raise HTTPException(status_code=400, detail="There is no active service to export.")
        
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