from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models import Service
from schemas.service import ServiceCreate

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
    db.commit()
    db.refresh(target_service)
    return target_service

def deactivate_service(db: Session, service_id: str):
    target_service = db.query(Service).filter(Service.id == service_id).first()
    if not target_service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        
    target_service.is_active = False
    db.commit()
    db.refresh(target_service)
    return target_service