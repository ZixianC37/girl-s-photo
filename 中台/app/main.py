import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db, engine, SessionLocal
from app.engine.registry import HandlerRegistry
from app.engine.task_engine import TaskEngine
from app.adapters.dingtalk_adapter import DingTalkAdapter
from app.adapters.wecom_adapter import WeComAdapter
from app.gateway.router import router as gateway_router
from app.admin.routes_api import router as admin_router
from app.admin.groups_api import router as groups_router
from app.admin.users_api import router as users_router
from app.admin.tasks_api import router as tasks_router
from app.admin.dashboard_api import router as dashboard_router
from app.admin.rd_tasks_api import router as rd_tasks_router
from app.admin.templates_api import router as templates_router
from app.admin.rd_projects_api import router as projects_router
from app.admin.anomalies_api import router as anomalies_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)

    # Handler registry - auto-discover handlers
    registry = HandlerRegistry()
    registry.auto_discover("app/handlers")

    # Adapters
    adapters = {
        "dingtalk": DingTalkAdapter(
            settings.dingtalk_app_key,
            settings.dingtalk_app_secret,
            settings.dingtalk_robot_code
        ),
        "wecom": WeComAdapter(),  # stub
    }

    # TaskEngine stored on app.state for gateway routes to access
    app.state.task_engine = TaskEngine(
        db=SessionLocal(),
        registry=registry,
        adapters=adapters
    )
    app.state.handler_registry = registry

    yield

app = FastAPI(title="Business Middleware", lifespan=lifespan)

app.include_router(gateway_router)
app.include_router(admin_router)
app.include_router(groups_router)
app.include_router(users_router)
app.include_router(tasks_router)
app.include_router(dashboard_router)
app.include_router(rd_tasks_router)
app.include_router(templates_router)
app.include_router(projects_router)
app.include_router(anomalies_router)

@app.get("/health")
async def health():
    return {"status": "ok"}


# Static file serving for frontend (only when web/dist exists)
DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")
if os.path.isdir(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("gateway/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
