from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models import Service, AttendanceLog
from schemas.service import ServiceCreate
from sqlalchemy.sql import func

def create_service(db: Session, service_data: ServiceCreate):
    new_service = Service(
        title=service_data.title,
        service_date=service_data.service_date,
        is_active=False # Defaults to False until HOD opens the gate
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service

def activate_service(db: Session, service_id: str):
    # 1. SAFETY MEASURE: Deactivate ALL currently active services to prevent overlaps
    db.query(Service).filter(Service.is_active == True).update({"is_active": False})
    
    # 2. Find the requested service
    target_service = db.query(Service).filter(Service.id == service_id).first()
    if not target_service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        
    # 3. Activate it
    target_service.is_active = True
    if not target_service.time_started:
        target_service.time_started = func.now()
    db.commit()
    db.refresh(target_service)
    return target_service

def deactivate_service(db: Session, service_id: str):
    target_service = db.query(Service).filter(Service.id == service_id).first()
    if not target_service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        
    target_service.is_active = False
    if not target_service.time_closed:
        target_service.time_closed = func.now()
    db.commit()
    db.refresh(target_service)
    return target_service

def delete_service(db: Session, service_id: str):
    target_service = db.query(Service).filter(Service.id == service_id).first()
    if not target_service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        
    db.delete(target_service)
    db.commit()

def get_all_services(db: Session):
    services = db.query(Service).order_by(Service.service_date.desc()).all()
    # Dynamically attach attendance count so the dashboard can display it
    for s in services:
        s.attendance_count = db.query(AttendanceLog).filter(AttendanceLog.service_id == s.id).count()
    return services