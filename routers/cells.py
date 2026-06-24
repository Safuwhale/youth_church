from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.cell import CellCreate, CellAssignment, CellDashboardResponse
from services.cell_service import create_cell, assign_member, generate_leader_dashboard
from database import get_db
from models import User
from core.dependencies import get_current_user

router = APIRouter()

@router.post("/create")
def create_new_cell(cell: CellCreate, db: Session = Depends(get_db)):
    """HOD Endpoint: Creates a new cell group."""
    return create_cell(db=db, cell_data=cell)

@router.post("/assign")
def assign_user_to_cell(assignment: CellAssignment, db: Session = Depends(get_db)):
    """HOD Endpoint: Drops a member into a cell and optionally makes them a leader."""
    return assign_member(db=db, assignment=assignment)

@router.get("/my-cell", response_model=CellDashboardResponse)
def get_my_cell_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Leader Endpoint: Uses the JWT token to find the leader's cell, 
    and returns a clean list of exactly who showed up and who is absent today.
    """
    return generate_leader_dashboard(db=db, current_user=current_user)