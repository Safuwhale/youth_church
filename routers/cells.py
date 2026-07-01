from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.cell import (
    CellCreate,
    CellUpdate,
    CellAssignment,
    CellMembersAssignment,
    CellMembersRemoval,
    CellDashboardResponse,
    CellGroupResponse,
)
from schemas.user import UserDirectoryItem
from services.cell_service import (
    create_cell,
    update_cell,
    delete_cell,
    list_cells,
    list_cell_members,
    assign_member,
    assign_members_bulk,
    remove_members_bulk,
    generate_leader_dashboard,
)
from database import get_db
from models import User
from core.dependencies import get_current_user

router = APIRouter()

@router.post("/create")
def create_new_cell(cell: CellCreate, db: Session = Depends(get_db)):
    """HOD Endpoint: Creates a new cell group."""
    return create_cell(db=db, cell_data=cell)


@router.get("/groups", response_model=list[CellGroupResponse])
def get_cell_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return list_cells(db=db)


@router.patch("/{cell_group_id}", response_model=CellGroupResponse)
def rename_cell_group(
    cell_group_id: str,
    cell: CellUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return update_cell(db=db, cell_group_id=cell_group_id, cell_data=cell)


@router.delete("/{cell_group_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cell_group(
    cell_group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    delete_cell(db=db, cell_group_id=cell_group_id)
    return None


@router.get("/{cell_group_id}/members", response_model=list[UserDirectoryItem])
def get_members_in_cell(
    cell_group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return list_cell_members(db=db, cell_group_id=cell_group_id)

@router.post("/assign")
def assign_user_to_cell(assignment: CellAssignment, db: Session = Depends(get_db)):
    """HOD Endpoint: Drops a member into a cell and optionally makes them a leader."""
    return assign_member(db=db, assignment=assignment)


@router.post("/{cell_group_id}/members")
def add_members_to_cell(
    cell_group_id: str,
    payload: CellMembersAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return assign_members_bulk(db=db, cell_group_id=cell_group_id, payload=payload)


@router.post("/{cell_group_id}/members/remove")
def remove_members_from_cell(
    cell_group_id: str,
    payload: CellMembersRemoval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["admin", "hod"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return remove_members_bulk(db=db, cell_group_id=cell_group_id, payload=payload)

@router.get("/my-cell", response_model=CellDashboardResponse)
def get_my_cell_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Leader Endpoint: Uses the JWT token to find the leader's cell, 
    and returns a clean list of exactly who showed up and who is absent today.
    """
    return generate_leader_dashboard(db=db, current_user=current_user)