from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from schemas.service import ServiceCreate, ServiceResponse
from services.church_service import create_service, activate_service, deactivate_service, get_all_services, delete_service
from database import get_db
from typing import List
from models import User
from core.dependencies import get_current_user
router = APIRouter()

@router.post("/create", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_new_service(service: ServiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """HOD creates a new Sunday Service calendar event."""
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return create_service(db=db, service_data=service)

@router.patch("/{service_id}/activate", response_model=ServiceResponse)
def open_service_gates(service_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Opens the gates for check-in. Automatically closes any other active services."""
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return activate_service(db=db, service_id=service_id)

@router.patch("/{service_id}/deactivate", response_model=ServiceResponse)
def close_service_gates(service_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Closes the check-in gates and triggers the absentee list generation phase."""
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return deactivate_service(db=db, service_id=service_id)

@router.get("", response_model=List[ServiceResponse])
def list_all_services(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Fetches all services for the Usher and HOD Dashboards.
    Returns them sorted so the most recent ones appear first.
    """
    if current_user.role not in ["admin", "hod", "usher"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return get_all_services(db=db)

@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_service(service_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Deletes a draft service. Rejects if the service has already started."""
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    delete_service(db=db, service_id=service_id)
    return None