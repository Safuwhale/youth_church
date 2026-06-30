from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from schemas.attendance import AttendanceScan, AttendanceResponse, SelfCheckIn
from services.attendance_service import process_scan, process_self_checkin, export_attendance_csv
from models import User
from database import get_db
from core.dependencies import get_current_user

router = APIRouter()

@router.post("/scan", response_model=AttendanceResponse, status_code=status.HTTP_200_OK)
def scan_user(
    scan_data: AttendanceScan, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Added dependency to track the usher
):
    """
    Core check-in endpoint. 
    Accepts a serial number and logs the user into the currently active service.
    """
    # Passed current_user to the service layer so it can log the usher_id
    return process_scan(db=db, scan_data=scan_data, current_user=current_user)

@router.post("/self-checkin", response_model=AttendanceResponse, status_code=status.HTTP_200_OK)
def self_checkin(
    scan_data: SelfCheckIn, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    MEMBER ENDPOINT:
    Accepts a service ID and logs the authenticated user.
    """
    return process_self_checkin(db=db, current_user=current_user, service_id=scan_data.service_id)

@router.get("/export", response_class=Response)
def download_attendance_report(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    HOD ENDPOINT: 
    Downloads a CSV spreadsheet of the currently active service attendance.
    """
    csv_data = export_attendance_csv(db=db, current_user=current_user)
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendance_report.csv"'}
    )