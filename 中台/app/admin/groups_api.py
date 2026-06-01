from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.tables import GroupMapping
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api", tags=["admin"])


class GroupCreate(BaseModel):
    name: str
    group_id: str
    platform: str


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    group_id: str
    platform: str


@router.get("/groups", response_model=List[GroupResponse])
async def list_groups(db: Session = Depends(get_db), _token: str = Depends(verify_admin)):
    """List all group mappings."""
    groups = db.query(GroupMapping).all()
    return groups


@router.post("/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(group: GroupCreate, db: Session = Depends(get_db), _token: str = Depends(verify_admin)):
    """Create a new group mapping."""
    # Check if group_id already exists
    existing = db.query(GroupMapping).filter(GroupMapping.group_id == group.group_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group ID already exists")

    db_group = GroupMapping(
        name=group.name,
        group_id=group.group_id,
        platform=group.platform
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


@router.delete("/groups/{group_id}", status_code=status.HTTP_200_OK)
async def delete_group(group_id: str, db: Session = Depends(get_db), _token: str = Depends(verify_admin)):
    """Delete a group mapping by ID."""
    # First try to find by integer ID, then by group_id string
    group = db.query(GroupMapping).filter(GroupMapping.id == int(group_id)).first()
    if not group:
        # Try finding by group_id string
        group = db.query(GroupMapping).filter(GroupMapping.group_id == group_id).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    db.delete(group)
    db.commit()
    return {"message": "Group deleted successfully"}
