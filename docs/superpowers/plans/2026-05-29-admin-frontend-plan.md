# 管理后台前端 + 后端 API 补充 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建业务中台管理后台前端（React + Ant Design 玻璃拟态风格），补齐后端缺失的 API。

**Architecture:** 前端独立 Vite 项目在 `中台/web/`，开发时 proxy 到 FastAPI :8000，构建后由 FastAPI StaticFiles 托管。后端新增 4 组 API（groups、users、tasks、dashboard）和 1 张新表（group_mapping）。前端 4 个页面 + 登录页，6 套玻璃拟态主题预设。

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy / React 18 / TypeScript / Vite 5 / Ant Design 5.x / React Router 6 / axios

**Spec:** `docs/superpowers/specs/2026-05-29-admin-frontend-design.md`

---

## File Structure

```
中台/
├── app/
│   ├── models/tables.py              # 新增 GroupMapping 模型
│   ├── admin/
│   │   ├── routes_api.py             # 已有：路由 CRUD
│   │   ├── auth.py                   # 已有：Bearer 认证
│   │   ├── groups_api.py             # 新增：群映射 CRUD
│   │   ├── users_api.py              # 新增：用户映射 API
│   │   ├── tasks_api.py              # 新增：任务监控 API
│   │   └── dashboard_api.py          # 新增：仪表盘统计
│   └── main.py                       # 修改：挂载新路由 + 静态文件
├── web/                              # 全新 React 项目
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── vite-env.d.ts
│       ├── api/
│       │   ├── client.ts
│       │   ├── routes.ts
│       │   ├── handlers.ts
│       │   ├── groups.ts
│       │   ├── users.ts
│       │   ├── tasks.ts
│       │   └── dashboard.ts
│       ├── theme/
│       │   ├── themes.ts
│       │   ├── ThemeContext.tsx
│       │   └── glass.css
│       ├── components/
│       │   ├── AppLayout.tsx
│       │   ├── GlassCard.tsx
│       │   ├── ThemeSwitcher.tsx
│       │   └── ProtectedRoute.tsx
│       └── pages/
│           ├── Login.tsx
│           ├── Dashboard.tsx
│           ├── Routes.tsx
│           ├── UserMapping.tsx
│           └── TaskMonitor.tsx
├── tests/
│   ├── test_groups_api.py
│   ├── test_users_api.py
│   ├── test_tasks_api.py
│   └── test_dashboard_api.py
└── Dockerfile                        # 修改：多阶段构建
```

---

## Task 1: GroupMapping 表 + API

**Files:**
- Modify: `中台/app/models/tables.py` (新增 GroupMapping)
- Create: `中台/app/admin/groups_api.py`
- Modify: `中台/app/main.py` (挂载 groups router)
- Test: `中台/tests/test_groups_api.py`

- [ ] **Step 1: Add GroupMapping model to tables.py**

在 `app/models/tables.py` 末尾追加：

```python
class GroupMapping(Base):
    __tablename__ = "group_mapping"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    group_id: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

同步更新 `app/models/__init__.py` 导出。

- [ ] **Step 2: Write failing test**

```python
# tests/test_groups_api.py
AUTH = {"Authorization": "Bearer changeme"}

def test_create_group(client, db_session):
    resp = client.post("/api/groups", json={
        "name": "品鉴会通知群",
        "group_id": "group_123",
        "platform": "dingtalk"
    }, headers=AUTH)
    assert resp.status_code == 201
    assert resp.json()["name"] == "品鉴会通知群"

def test_list_groups(client, db_session):
    client.post("/api/groups", json={"name": "群1", "group_id": "g1", "platform": "dingtalk"}, headers=AUTH)
    client.post("/api/groups", json={"name": "群2", "group_id": "g2", "platform": "wecom"}, headers=AUTH)
    resp = client.get("/api/groups", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

def test_delete_group(client, db_session):
    resp = client.post("/api/groups", json={"name": "群1", "group_id": "g1", "platform": "dingtalk"}, headers=AUTH)
    gid = resp.json()["id"]
    resp = client.delete(f"/api/groups/{gid}", headers=AUTH)
    assert resp.status_code == 200
    assert client.get("/api/groups", headers=AUTH).json() == []
```

- [ ] **Step 3: Create groups_api.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.tables import GroupMapping
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api", tags=["admin"])

class GroupCreate(BaseModel):
    name: str
    group_id: str
    platform: str

@router.get("/groups")
async def list_groups(db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    groups = db.query(GroupMapping).all()
    return [{"id": g.id, "name": g.name, "group_id": g.group_id, "platform": g.platform} for g in groups]

@router.post("/groups", status_code=201)
async def create_group(group: GroupCreate, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    g = GroupMapping(name=group.name, group_id=group.group_id, platform=group.platform)
    db.add(g)
    db.commit()
    db.refresh(g)
    return {"id": g.id, "name": g.name, "group_id": g.group_id, "platform": g.platform}

@router.delete("/groups/{group_id}")
async def delete_group(group_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    g = db.query(GroupMapping).filter(GroupMapping.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(g)
    db.commit()
    return {"status": "deleted"}
```

- [ ] **Step 4: Mount in main.py**

在 main.py 中添加：
```python
from app.admin.groups_api import router as groups_router
app.include_router(groups_router)
```

- [ ] **Step 5: Run tests**

Run: `cd 中台 && python3 -m pytest tests/test_groups_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/models/tables.py app/admin/groups_api.py app/main.py tests/test_groups_api.py
git commit -m "feat(middleware): group mapping table + CRUD API"
```

---

## Task 2: Users API

**Files:**
- Create: `中台/app/admin/users_api.py`
- Modify: `中台/app/main.py` (挂载 users router)
- Test: `中台/tests/test_users_api.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_users_api.py
AUTH = {"Authorization": "Bearer changeme"}

def test_list_users(client, db_session):
    from app.models.tables import UserMapping
    db_session.add(UserMapping(feishu_user_id="f1", dingtalk_user_id="d1", phone="13800000001", name="张三"))
    db_session.commit()
    resp = client.get("/api/users", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["sync_status"] == "matched"
    assert "****" in data["items"][0]["phone"]

def test_list_users_unmatched(client, db_session):
    from app.models.tables import UserMapping
    db_session.add(UserMapping(feishu_user_id="f2", phone="13800000002", name="李四"))
    db_session.commit()
    resp = client.get("/api/users?status=unmatched", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1

def test_update_user(client, db_session):
    from app.models.tables import UserMapping
    db_session.add(UserMapping(feishu_user_id="f3", phone="13800000003", name="王五"))
    db_session.commit()
    uid = db_session.query(UserMapping).first().id
    resp = client.put(f"/api/users/{uid}", json={"dingtalk_user_id": "d3"}, headers=AUTH)
    assert resp.status_code == 200

def test_sync_users(client, db_session):
    from app.models.tables import UserMapping
    db_session.add(UserMapping(feishu_user_id="f1", phone="13800000001"))
    db_session.add(UserMapping(dingtalk_user_id="d1", phone="13800000001"))
    db_session.commit()
    resp = client.post("/api/users/sync", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["synced"] >= 1
```

- [ ] **Step 2: Create users_api.py**

实现要点：
- `GET /api/users`：支持 `status`（matched/unmatched）、`search`（姓名/手机号模糊匹配）、`page`/`page_size` 分页。响应时计算 `sync_status`，手机号脱敏。
- `PUT /api/users/{id}`：更新指定字段。
- `POST /api/users/sync`：调用 `IdentityService(db).auto_match()`，返回 `{"synced": count, "total": total}`。

- [ ] **Step 3: Mount in main.py and run tests**

Run: `cd 中台 && python3 -m pytest tests/test_users_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add app/admin/users_api.py app/main.py tests/test_users_api.py
git commit -m "feat(middleware): user mapping API with sync and pagination"
```

---

## Task 3: Tasks API + Dashboard API

**Files:**
- Create: `中台/app/admin/tasks_api.py`
- Create: `中台/app/admin/dashboard_api.py`
- Modify: `中台/app/main.py` (挂载新路由)
- Test: `中台/tests/test_tasks_api.py`
- Test: `中台/tests/test_dashboard_api.py`

- [ ] **Step 1: Write failing tests for tasks**

```python
# tests/test_tasks_api.py
AUTH = {"Authorization": "Bearer changeme"}

def test_list_tasks(client, db_session):
    from app.models.tables import TaskInstance, TaskRoute
    route = TaskRoute(handler_name="H", feishu_table_id="t", platform="dingtalk", group_id="g", field_mapping="{}", enabled=True)
    db_session.add(route)
    db_session.flush()
    db_session.add(TaskInstance(handler_name="H", route_id=route.id, feishu_record_id="r1", platform="dingtalk", group_id="g", status="pending", flow_state="{}"))
    db_session.commit()
    resp = client.get("/api/tasks", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

def test_task_detail(client, db_session):
    # 创建 task_instance + task_participant
    # GET /api/tasks/{id} 返回 participants 列表
    ...
```

- [ ] **Step 2: Write failing tests for dashboard**

```python
# tests/test_dashboard_api.py
AUTH = {"Authorization": "Bearer changeme"}

def test_dashboard_stats(client, db_session):
    resp = client.get("/api/dashboard/stats", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "active_routes" in data
    assert "registered_handlers" in data
    assert "today_tasks" in data
    assert "error_rate" in data
    assert "recent_tasks" in data
```

- [ ] **Step 3: Create tasks_api.py**

实现要点：
- `GET /api/tasks`：支持 `status`、`handler` 筛选，`page`/`page_size` 分页
- `GET /api/tasks/{id}`：返回 task_instance + 关联 participants 列表

- [ ] **Step 4: Create dashboard_api.py**

实现要点：
- `GET /api/dashboard/stats`：聚合查询 active_routes、registered_handlers、today_tasks、error_rate、recent_tasks

- [ ] **Step 5: Mount in main.py and run ALL tests**

Run: `cd 中台 && python3 -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/admin/tasks_api.py app/admin/dashboard_api.py app/main.py tests/test_tasks_api.py tests/test_dashboard_api.py
git commit -m "feat(middleware): task monitoring + dashboard stats API"
```

---

## Task 4: React 项目脚手架

**Files:**
- Create: `中台/web/package.json`
- Create: `中台/web/tsconfig.json`
- Create: `中台/web/vite.config.ts`
- Create: `中台/web/index.html`
- Create: `中台/web/src/main.tsx`
- Create: `中台/web/src/App.tsx`
- Create: `中台/web/src/vite-env.d.ts`

- [ ] **Step 1: Scaffold Vite + React + TS project**

```bash
cd 中台 && npm create vite@latest web -- --template react-ts
cd web && npm install
```

- [ ] **Step 2: Install dependencies**

```bash
cd web && npm install antd @ant-design/icons react-router-dom axios
```

- [ ] **Step 3: Configure vite.config.ts**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    }
  }
})
```

- [ ] **Step 4: Clean up scaffolded files**

删除默认的 App.css、index.css 等无用文件，保留最小结构。

- [ ] **Step 5: Verify dev server starts**

Run: `cd web && npm run dev`
Expected: Vite dev server 在 :5173 启动

- [ ] **Step 6: Commit**

```bash
git add web/
git commit -m "feat(web): React + Vite + Ant Design project scaffold"
```

---

## Task 5: 主题系统 + 玻璃拟态组件

**Files:**
- Create: `中台/web/src/theme/themes.ts`
- Create: `中台/web/src/theme/ThemeContext.tsx`
- Create: `中台/web/src/theme/glass.css`
- Create: `中台/web/src/components/GlassCard.tsx`
- Create: `中台/web/src/components/ThemeSwitcher.tsx`

- [ ] **Step 1: Create themes.ts with 6 presets**

每套主题包含：name, gradient (CSS gradient string), antToken (Ant Design DesignToken override)。参考 spec 中的 6 套色板。

- [ ] **Step 2: Create ThemeContext.tsx**

ThemeProvider 组件：管理当前主题 state，从 localStorage 读取初始值（key: `theme_name`），切换时更新 localStorage + CSS 变量 + Ant Design ConfigProvider token。

- [ ] **Step 3: Create glass.css**

全局玻璃拟态样式：`.glass` 类（backdrop-filter, 半透明背景, 边框）+ 渐变背景动画 + 侧边栏/表格/弹窗的玻璃样式。

- [ ] **Step 4: Create GlassCard.tsx**

可复用的玻璃卡片组件：接收 children + 可选 title，渲染为带 `.glass` 类的 div。

- [ ] **Step 5: Create ThemeSwitcher.tsx**

6 个彩色圆点（每点的背景色 = 对应主题的渐变色），点击切换主题。当前选中主题有白色边框高亮。

- [ ] **Step 6: Verify**

Run: `cd web && npm run dev`，在浏览器中查看主题切换效果。

- [ ] **Step 7: Commit**

```bash
git add web/src/theme/ web/src/components/GlassCard.tsx web/src/components/ThemeSwitcher.tsx
git commit -m "feat(web): glassmorphism theme system with 6 presets"
```

---

## Task 6: API 客户端 + 认证

**Files:**
- Create: `中台/web/src/api/client.ts`
- Create: `中台/web/src/api/routes.ts`
- Create: `中台/web/src/api/handlers.ts`
- Create: `中台/web/src/api/groups.ts`
- Create: `中台/web/src/api/users.ts`
- Create: `中台/web/src/api/tasks.ts`
- Create: `中台/web/src/api/dashboard.ts`

- [ ] **Step 1: Create client.ts**

axios 实例：baseURL 为空（同源），请求拦截器从 localStorage 读取 `admin_token` 附加 Bearer header，响应拦截器处理 401 跳转登录。

- [ ] **Step 2: Create API 函数文件**

每个文件对应一组后端 API：
- routes.ts: listRoutes, createRoute, updateRoute, deleteRoute
- handlers.ts: listHandlers
- groups.ts: listGroups, createGroup, deleteGroup
- users.ts: listUsers, updateUser, syncUsers
- tasks.ts: listTasks, getTaskDetail
- dashboard.ts: getStats

全部函数使用 client.ts 的 axios 实例。

- [ ] **Step 3: Commit**

```bash
git add web/src/api/
git commit -m "feat(web): API client with auth interceptor"
```

---

## Task 7: 全局布局 + 登录页 + 路由

**Files:**
- Create: `中台/web/src/components/AppLayout.tsx`
- Create: `中台/web/src/components/ProtectedRoute.tsx`
- Create: `中台/web/src/pages/Login.tsx`
- Modify: `中台/web/src/App.tsx`
- Modify: `中台/web/src/main.tsx`

- [ ] **Step 1: Create Login.tsx**

玻璃拟态登录卡片：一个 Token 输入框 + "进入" 按钮。提交后存入 localStorage 并跳转 `/`。

- [ ] **Step 2: Create ProtectedRoute.tsx**

检查 localStorage token，无则跳转 `/login`。

- [ ] **Step 3: Create AppLayout.tsx**

左侧玻璃侧边栏（菜单项：仪表盘/路由/用户/监控）+ 右侧内容区。侧边栏底部放 ThemeSwitcher + 用户信息（登出按钮）。使用 Ant Design Menu + React Router Outlet。

- [ ] **Step 4: Update App.tsx with routes**

React Router 配置：
- `/login` → Login.tsx
- `/` → ProtectedRoute → AppLayout → Dashboard.tsx
- `/routes` → ProtectedRoute → AppLayout → Routes.tsx
- `/users` → ProtectedRoute → AppLayout → UserMapping.tsx
- `/tasks` → ProtectedRoute → AppLayout → TaskMonitor.tsx

- [ ] **Step 5: Verify**

Run: `cd web && npm run dev`
打开 http://localhost:5173，应看到登录页。输入 `changeme` 后进入仪表盘。

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(web): app layout, login page, and routing"
```

---

## Task 8: Dashboard 页面

**Files:**
- Create: `中台/web/src/pages/Dashboard.tsx`

- [ ] **Step 1: Implement Dashboard**

- 4 个 GlassCard 统计卡片（活跃路由、Handler 数、今日任务、错误率），数据来自 `getStats()`
- 最近任务列表（Ant Design Table，显示 Handler、状态标签、创建时间）
- 快捷操作按钮（新建路由、同步用户）

- [ ] **Step 2: Verify**

打开 `/` 页面，确认统计卡片和任务列表正常渲染。

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Dashboard.tsx
git commit -m "feat(web): dashboard page with stats and recent tasks"
```

---

## Task 9: Routes 页面

**Files:**
- Create: `中台/web/src/pages/Routes.tsx`

- [ ] **Step 1: Implement Routes page**

- 路由列表表格（GlassTable）：Handler、飞书表 ID、平台（彩色标签）、目标群、启用状态（Switch）、操作按钮
- 新建/编辑弹窗（GlassModal）：Handler 下拉、飞书表 ID、平台选择、目标群 ID、字段映射编辑器（键值对行列表，可增删）
- 删除确认弹窗

- [ ] **Step 2: Verify**

CRUD 操作全部可用，字段映射编辑器可增删行。

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Routes.tsx
git commit -m "feat(web): route config page with CRUD and field mapping editor"
```

---

## Task 10: UserMapping 页面

**Files:**
- Create: `中台/web/src/pages/UserMapping.tsx`

- [ ] **Step 1: Implement UserMapping page**

- 筛选栏：映射状态（全部/已匹配/未匹配）、搜索框
- 用户列表表格：姓名、飞书 ID、钉钉 ID、企微 ID、手机号（脱敏）、映射状态标签、操作
- 一键同步按钮 → 调用 `syncUsers()`
- 手动编辑弹窗：补充缺失的平台 ID

- [ ] **Step 2: Verify**

筛选、同步、编辑功能正常。

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/UserMapping.tsx
git commit -m "feat(web): user mapping page with sync and inline edit"
```

---

## Task 11: TaskMonitor 页面

**Files:**
- Create: `中台/web/src/pages/TaskMonitor.tsx`

- [ ] **Step 1: Implement TaskMonitor page**

- 筛选栏：状态多选、Handler 下拉
- 任务实例列表表格：Handler、飞书记录 ID、平台、群、状态标签、截止时间、创建时间
- 行点击 → 详情弹窗：任务信息 + 参与者列表

- [ ] **Step 2: Verify**

筛选、分页、详情弹窗正常。

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/TaskMonitor.tsx
git commit -m "feat(web): task monitor page with filter and detail modal"
```

---

## Task 12: FastAPI 静态文件托管 + Dockerfile

**Files:**
- Modify: `中台/app/main.py`
- Modify: `中台/Dockerfile`

- [ ] **Step 1: Add static file serving to main.py**

在所有 API router 之后、app 创建之后添加：

```python
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "dist")
if os.path.isdir(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
```

- [ ] **Step 2: Update Dockerfile to multi-stage build**

```dockerfile
FROM node:20-slim AS frontend
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY --from=frontend /app/web/dist ./web/dist
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Build and verify**

```bash
cd 中台 && cd web && npm run build && cd .. && python3 -m uvicorn app.main:app --port 8000
```

打开 http://localhost:8000，应看到前端页面（非 Swagger）。

- [ ] **Step 4: Commit**

```bash
git add app/main.py Dockerfile
git commit -m "feat(middleware): static file serving + multi-stage Dockerfile"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | GroupMapping | 新表 + CRUD API |
| 2 | Users API | 用户映射 + 同步 + 分页 |
| 3 | Tasks + Dashboard | 任务监控 + 仪表盘统计 |
| 4 | React 脚手架 | Vite + React + TS + AntD |
| 5 | 主题系统 | 玻璃拟态 + 6 套主题 |
| 6 | API 客户端 | axios + 认证拦截 |
| 7 | 布局 + 登录 | 侧边栏 + 路由 + 登录页 |
| 8 | Dashboard | 统计卡片 + 最近任务 |
| 9 | Routes | 路由 CRUD + 字段映射编辑器 |
| 10 | UserMapping | 用户映射 + 同步 |
| 11 | TaskMonitor | 任务列表 + 详情弹窗 |
| 12 | 部署 | 静态文件托管 + Dockerfile |
