from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models import User, Service, AttendanceLog
from schemas.attendance import AttendanceScan
import io
import csv


def _attendance_method_value(method):
    return getattr(method, "value", method)


def _attendance_response(message: str, member: User, log: AttendanceLog) -> dict:
    return {
        "message": message,
        "user_name": f"{member.first_name} {member.last_name}",
        "check_in_time": log.check_in_time,
        "check_in_method": _attendance_method_value(log.check_in_method),
    }


def process_scan(db: Session, scan_data: AttendanceScan, current_user: User):
    """Core check-in logic for Ushers scanning members into a specific service."""

    if current_user.role not in ["usher", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    target_service = db.query(Service).filter(Service.id == scan_data.service_id).first()
    if not target_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected service could not be found.",
        )

    if not target_service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This service is closed. You cannot scan members into a closed service.",
        )

    member = db.query(User).filter(User.serial_number == scan_data.serial_number).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found.",
        )

    if not member.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated.",
        )

    existing = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == member.id,
        AttendanceLog.service_id == target_service.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member already checked in.",
        )

    new_log = AttendanceLog(
        user_id=member.id,
        service_id=target_service.id,
        usher_id=current_user.id,
        check_in_method=_attendance_method_value(getattr(scan_data, "check_in_method", "QR_SCAN")),
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return _attendance_response("Member checked in successfully.", member, new_log)


def process_self_checkin(db: Session, current_user: User, service_id: str):
    """Used by Members scanning the Service QR code poster."""

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")

    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This service is not currently open for check-in.",
        )

    existing_log = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.service_id == service.id,
    ).first()
    if existing_log:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked in.",
        )

    new_log = AttendanceLog(
        user_id=current_user.id,
        service_id=service.id,
        check_in_method="SELF_SCAN",
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return _attendance_response("Self check-in successful.", current_user, new_log)


def export_attendance_csv(db: Session, current_user: User):
    """Generates a CSV of the currently active service attendance."""

    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to export data.")

    active_service = db.query(Service).filter(Service.is_active == True).first()
    if not active_service:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="There is no active service to export.")

    logs = db.query(AttendanceLog).filter(AttendanceLog.service_id == active_service.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Service Title", "Serial Number", "First Name", "Last Name", "Check-in Time", "Method"])

    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        writer.writerow([
            active_service.service_date,
            active_service.title,
            user.serial_number,
            user.first_name,
            user.last_name,
            log.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if log.check_in_time else "N/A",
            log.check_in_method,
        ])

    return output.getvalue()


def get_service_attendance_detail(db: Session, current_user: User, service_id: str):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")

    logs = db.query(AttendanceLog).filter(AttendanceLog.service_id == service.id).order_by(AttendanceLog.check_in_time.asc()).all()

    attendees = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        if not user:
            continue
        attendees.append({
            "id": user.id,
            "serial_number": user.serial_number,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "check_in_time": log.check_in_time,
            "check_in_method": _attendance_method_value(log.check_in_method),
        })

    return {
        "id": service.id,
        "title": service.title,
        "service_date": service.service_date,
        "is_active": service.is_active,
        "attendance_count": len(attendees),
        "attendees": attendees,
    }