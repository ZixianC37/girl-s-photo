from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.tables import UserMapping
from app.admin.auth import verify_admin
from app.services.identity import IdentityService

router = APIRouter(prefix="/api", tags=["admin"])


class UserUpdate(BaseModel):
    feishu_user_id: Optional[str] = None
    dingtalk_user_id: Optional[str] = None
    wecom_user_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Mask phone number for privacy"""
    if phone and len(phone) >= 7:
        return phone[:3] + "****" + phone[-4:]
    return None


def compute_sync_status(user: UserMapping) -> str:
    """Compute sync status based on platform IDs"""
    has_feishu = bool(user.feishu_user_id)
    has_platform = bool(user.dingtalk_user_id or user.wecom_user_id)
    return "matched" if (has_feishu and has_platform) else "unmatched"


@router.get("/users")
async def list_users(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """List user mappings with optional filtering and pagination"""
    query = db.query(UserMapping)

    # Filter by sync status
    if status == "matched":
        query = query.filter(
            UserMapping.feishu_user_id.isnot(None),
            (UserMapping.dingtalk_user_id.isnot(None)) | (UserMapping.wecom_user_id.isnot(None))
        )
    elif status == "unmatched":
        query = query.filter(
            (UserMapping.feishu_user_id.is_(None)) |
            ((UserMapping.dingtalk_user_id.is_(None)) & (UserMapping.wecom_user_id.is_(None)))
        )

    # Search by name or phone (fuzzy)
    if search:
        query = query.filter(
            (UserMapping.name.ilike(f"%{search}%")) |
            (UserMapping.phone.ilike(f"%{search}%"))
        )

    # Get total count
    total = query.count()

    # Pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "id": u.id,
                "feishu_user_id": u.feishu_user_id,
                "dingtalk_user_id": u.dingtalk_user_id,
                "wecom_user_id": u.wecom_user_id,
                "name": u.name,
                "phone": mask_phone(u.phone),
                "sync_status": compute_sync_status(u),
                "synced_at": u.synced_at.isoformat() if u.synced_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    update: UserUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """Update user mapping"""
    user = db.query(UserMapping).filter(UserMapping.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.feishu_user_id is not None:
        user.feishu_user_id = update.feishu_user_id
    if update.dingtalk_user_id is not None:
        user.dingtalk_user_id = update.dingtalk_user_id
    if update.wecom_user_id is not None:
        user.wecom_user_id = update.wecom_user_id
    if update.name is not None:
        user.name = update.name
    if update.phone is not None:
        user.phone = update.phone

    db.commit()
    return {"id": user.id, "status": "updated"}


@router.post("/users/sync")
async def sync_users(
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """Trigger automatic user matching by phone number"""
    service = IdentityService(db)
    synced = service.auto_match()
    total = db.query(UserMapping).count()

    return {
        "synced": synced,
        "total": total,
    }
