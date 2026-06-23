from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from schemas.service import ServiceCreate, ServiceResponse
from services.church_service import create_service, activate_service, deactivate_service
from database import get_db

router = APIRouter()

@router.post("/create", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_new_service(service: ServiceCreate, db: Session = Depends(get_db)):
    """HOD creates a new Sunday Service calendar event."""
    return create_service(db=db, service_data=service)

@router.patch("/{service_id}/activate", response_model=ServiceResponse)
def open_service_gates(service_id: str, db: Session = Depends(get_db)):
    """Opens the gates for check-in. Automatically closes any other active services."""
    return activate_service(db=db, service_id=service_id)

@router.patch("/{service_id}/deactivate", response_model=ServiceResponse)
def close_service_gates(service_id: str, db: Session = Depends(get_db)):
    """Closes the check-in gates and triggers the absentee list generation phase."""
    return deactivate_service(db=db, service_id=service_id)