from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.tables import TaskRoute
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api", tags=["admin"])

class RouteCreate(BaseModel):
    handler_name: str
    feishu_table_id: str
    platform: str
    group_id: str
    field_mapping: dict = {}
    enabled: bool = True

class RouteUpdate(BaseModel):
    handler_name: Optional[str] = None
    feishu_table_id: Optional[str] = None
    platform: Optional[str] = None
    group_id: Optional[str] = None
    field_mapping: Optional[dict] = None
    enabled: Optional[bool] = None

@router.get("/routes")
async def list_routes(db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    routes = db.query(TaskRoute).all()
    return [
        {
            "id": r.id,
            "handler_name": r.handler_name,
            "feishu_table_id": r.feishu_table_id,
            "platform": r.platform,
            "group_id": r.group_id,
            "field_mapping": r.field_mapping,
            "enabled": r.enabled,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in routes
    ]

@router.post("/routes", status_code=201)
async def create_route(route: RouteCreate, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    import json
    r = TaskRoute(
        handler_name=route.handler_name,
        feishu_table_id=route.feishu_table_id,
        platform=route.platform,
        group_id=route.group_id,
        field_mapping=json.dumps(route.field_mapping),
        enabled=route.enabled,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "handler_name": r.handler_name, "feishu_table_id": r.feishu_table_id}

@router.put("/routes/{route_id}")
async def update_route(route_id: int, update: RouteUpdate, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    import json
    r = db.query(TaskRoute).filter(TaskRoute.id == route_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Route not found")
    if update.handler_name is not None:
        r.handler_name = update.handler_name
    if update.feishu_table_id is not None:
        r.feishu_table_id = update.feishu_table_id
    if update.platform is not None:
        r.platform = update.platform
    if update.group_id is not None:
        r.group_id = update.group_id
    if update.field_mapping is not None:
        r.field_mapping = json.dumps(update.field_mapping)
    if update.enabled is not None:
        r.enabled = update.enabled
    db.commit()
    return {"id": r.id, "handler_name": r.handler_name}

@router.delete("/routes/{route_id}")
async def delete_route(route_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    r = db.query(TaskRoute).filter(TaskRoute.id == route_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Route not found")
    db.delete(r)
    db.commit()
    return {"status": "deleted"}

@router.get("/handlers")
async def list_handlers(request: Request, _: str = Depends(verify_admin)):
    registry = getattr(request.app.state, "handler_registry", None)
    if registry:
        return registry.list_handlers()
    return []
