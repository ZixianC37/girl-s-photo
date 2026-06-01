# 业务中台管理后台前端设计

## 背景

业务中台 P0 骨架（FastAPI 后端 + 6 张表 + TaskHandler 引擎）已完成。现需构建管理后台前端，供运营人员配置任务路由、管理用户映射、监控任务状态。

## 技术选型

| 组件 | 方案 |
|------|------|
| 框架 | React 18 + TypeScript |
| 构建工具 | Vite 5 |
| UI 库 | Ant Design 5.x |
| 路由 | React Router 6 |
| HTTP 客户端 | axios |
| 样式 | CSS Modules + CSS 变量（玻璃拟态） |
| 部署 | Vite build → FastAPI StaticFiles 托管 |

## 架构

### 目录结构

```
中台/
├── app/                    # FastAPI 后端（已有）
├── web/                    # React 前端
│   ├── public/
│   ├── src/
│   │   ├── api/            # axios 实例 + API 函数
│   │   │   ├── client.ts   # axios 实例（baseURL, auth interceptor）
│   │   │   ├── routes.ts   # 路由 CRUD API
│   │   │   ├── handlers.ts # Handler 列表 API
│   │   │   ├── groups.ts   # 群映射 API
│   │   │   ├── users.ts    # 用户映射 API
│   │   │   └── tasks.ts    # 任务监控 API
│   │   ├── components/     # 共享组件
│   │   │   ├── GlassCard.tsx       # 玻璃卡片容器
│   │   │   ├── GlassTable.tsx      # 玻璃表格
│   │   │   ├── GlassModal.tsx      # 玻璃弹窗
│   │   │   ├── ThemeSwitcher.tsx   # 主题切换器
│   │   │   └── AppLayout.tsx       # 全局布局（侧边栏 + 内容区）
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # 仪表盘
│   │   │   ├── Routes.tsx          # 任务路由配置
│   │   │   ├── UserMapping.tsx     # 用户映射管理
│   │   │   └── TaskMonitor.tsx     # 任务监控
│   │   ├── theme/
│   │   │   ├── themes.ts           # 6 套主题预设（渐变 + token）
│   │   │   ├── ThemeContext.tsx     # 主题 Context + Provider
│   │   │   └── glass.css           # 玻璃拟态全局样式
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts      # dev proxy → :8000
│   ├── tsconfig.json
│   └── package.json
└── Dockerfile              # 更新：build 前端 + 托管静态文件
```

### 前后端交互

**开发模式**：Vite dev server (port 5173) → proxy `/api/*` 和 `/webhook/*` → FastAPI (port 8000)

**生产模式**：`npm run build` 输出到 `web/dist/`，FastAPI 通过 `StaticFiles` 中间件托管。所有非 API 路由返回 `index.html`（SPA fallback）。

## 主题系统

### 玻璃拟态设计规范

```css
/* 核心样式变量 */
:root {
  --glass-bg: rgba(255, 255, 255, 0.12);
  --glass-border: rgba(255, 255, 255, 0.18);
  --glass-blur: 16px;
  --glass-radius: 14px;
}

.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--glass-radius);
}
```

### 6 套主题预设

每套主题包含：渐变背景（3 色 CSS gradient）+ Ant Design Design Token 覆盖。

| 名称 | 渐变色 | 气质 |
|------|--------|------|
| 极光紫 | #667eea → #764ba2 | 默认，沉稳科技感 |
| 深海蓝 | #0f2027 → #203a43 → #2c5364 | 专业冷静 |
| 落日粉 | #ee9ca7 → #ffdde1 | 温柔浪漫 |
| 翡翠绿 | #11998e → #38ef7d | 自然清新 |
| 星空夜 | #0f0c29 → #302b63 → #24243e | 深邃神秘 |
| 蜜桃橙 | #f6d365 → #fda085 | 温暖活力 |

### 主题切换实现

```tsx
// ThemeContext.tsx
const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState<ThemePreset>(themes[0]);

  return (
    <ConfigProvider theme={{ token: theme.antToken }}>
      <div style={{ background: theme.gradient }}>
        {children}
      </div>
    </ConfigProvider>
  );
};
```

用户点击 ThemeSwitcher 中的色块 → 更新 Context → CSS 变量 + Ant Design token 同时切换。主题选择持久化到 localStorage。

## 页面设计

### 1. 仪表盘（Dashboard）

**路由**：`/`

**内容**：
- 4 个统计玻璃卡片：活跃路由数、已注册 Handler 数、今日任务数、错误率
- 最近任务列表（最近 10 条 task_instance，含状态标签、Handler 名称、创建时间）
- 快捷操作：新建路由、同步用户

### 2. 任务路由配置（Routes）

**路由**：`/routes`

**内容**：
- 路由列表表格：Handler 名称、飞书表 ID（截断显示）、平台（彩色标签）、目标群、启用状态（开关）、操作按钮
- 新建/编辑弹窗：Handler 下拉（从 `/api/handlers` 获取）、飞书表 ID 输入、平台选择（钉钉/企微/双平台）、目标群 ID 输入、字段映射编辑器（键值对列表，可增删行）
- 删除确认弹窗
- 启用/禁用开关（表格内直接切换）

**字段映射编辑器**：简单的键值对列表。每行：飞书字段名（输入框）→ 任务参数名（输入框）。支持增删行。

### 3. 用户映射管理（UserMapping）

**路由**：`/users`

**内容**：
- 筛选栏：映射状态（已匹配/未匹配/冲突）、平台（全部/钉钉/企微）、搜索框（姓名/手机号）
- 用户列表表格：姓名、飞书 ID、钉钉 ID、企微 ID、手机号（脱敏）、映射状态（彩色标签）、操作
- 一键同步按钮 → 调用 `POST /api/users/sync`
- 手动编辑弹窗：补充缺失的平台用户 ID

### 4. 任务监控（TaskMonitor）

**路由**：`/tasks`

**内容**：
- 筛选栏：状态（全部/pending/confirmed/submitted/completed/error）、Handler 下拉、时间范围
- 任务实例列表：Handler、飞书记录 ID、平台、群、状态（彩色标签）、截止时间、创建时间
- 点击行展开详情弹窗：任务基本信息 + 参与者列表（姓名、角色、状态、文件数、提交时间）

## 后端 API 补充

### 群映射 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/groups | 获取所有群映射 |
| POST | /api/groups | 添加群映射 |
| DELETE | /api/groups/{id} | 删除群映射 |

请求/响应体：

```json
// POST /api/groups
{ "name": "品鉴会通知群", "group_id": "group_xxx", "platform": "dingtalk" }

// GET /api/groups 响应
[{ "id": 1, "name": "品鉴会通知群", "group_id": "group_xxx", "platform": "dingtalk" }]
```

### 群映射后端实现

**新增表**：在 `app/models/tables.py` 添加 `GroupMapping` ORM 模型：

```python
class GroupMapping(Base):
    __tablename__ = "group_mapping"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    group_id: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)  # dingtalk / wecom
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**新增路由**：创建 `app/admin/groups_api.py`，挂载到 admin router 下。

### 用户映射后端实现

**`sync_status` 字段**：不在数据库新增列，而是在 API 响应时动态计算：
- `matched`：feishu_user_id 非空 且 (dingtalk_user_id 非空 或 wecom_user_id 非空)
- `unmatched`：其他情况

**新增路由**：在 `app/admin/` 下创建 `users_api.py`：
- `GET /api/users`：查询 user_mapping 表，支持 `status`/`search` 筛选参数和分页（offset/limit）。响应时动态计算 sync_status，手机号脱敏（`phone[:3] + "****" + phone[-4:]`）
- `POST /api/users/sync`：调用已有的 `IdentityService.auto_match()`，返回匹配数量
- `PUT /api/users/{id}`：更新 user_mapping 的指定字段

### 任务监控后端实现

**新增路由**：在 `app/admin/` 下创建 `tasks_api.py`：
- `GET /api/tasks`：查询 task_instance 表，支持 `status`/`handler` 筛选和分页
- `GET /api/tasks/{id}`：查询 task_instance + 关联的 task_participant 列表

### 仪表盘后端实现

**新增路由**：在 `app/admin/` 下创建 `dashboard_api.py`：
- `GET /api/dashboard/stats`：聚合查询
  - `active_routes`：`SELECT COUNT(*) FROM task_route WHERE enabled = true`
  - `registered_handlers`：从 `app.state.handler_registry.list_handlers()` 获取长度
  - `today_tasks`：`SELECT COUNT(*) FROM task_instance WHERE DATE(created_at) = DATE('now')`
  - `error_rate`：`SELECT CAST(SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) FROM task_instance`
  - `recent_tasks`：`SELECT * FROM task_instance ORDER BY created_at DESC LIMIT 10`

### 用户映射 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users | 用户映射列表（支持分页和状态筛选） |
| POST | /api/users/sync | 触发全量手机号匹配 |
| PUT | /api/users/{id} | 手动补充映射 |

请求/响应体：

```json
// GET /api/users?status=unmatched&page=1&page_size=20
{
  "items": [{ "id": 1, "feishu_user_id": "f1", "dingtalk_user_id": "d1", "wecom_user_id": null, "phone": "138****0001", "name": "张三", "sync_status": "matched" }],
  "total": 42,
  "page": 1,
  "page_size": 20
}

// PUT /api/users/{id}
{ "dingtalk_user_id": "d_new" }

// POST /api/users/sync 响应
{ "synced": 15, "total": 42 }
```

`sync_status` 计算逻辑：feishu_user_id 和至少一个平台 ID 都有值 → matched；否则 unmatched。

### 任务监控 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tasks | 任务实例列表（支持状态筛选） |
| GET | /api/tasks/{id} | 任务详情（含参与者） |

请求/响应体：

```json
// GET /api/tasks?status=pending&handler=TastingHandler&page=1&page_size=20
{
  "items": [{
    "id": 1, "handler_name": "TastingHandler", "feishu_record_id": "rec_1",
    "platform": "dingtalk", "group_id": "group_1", "card_id": "card_1",
    "status": "pending", "deadline": "2026-06-01T00:00:00Z",
    "created_at": "2026-05-29T10:00:00Z"
  }],
  "total": 5,
  "page": 1,
  "page_size": 20
}

// GET /api/tasks/{id} 响应
{
  ...task_instance,
  "participants": [
    { "id": 1, "feishu_user_id": "f1", "platform_user_id": "d1", "role": "participant", "status": "confirmed", "file_count": 2, "submitted_at": null }
  ]
}
```

### 仪表盘统计 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/dashboard/stats | 聚合统计数据 |

```json
// GET /api/dashboard/stats 响应
{
  "active_routes": 5,
  "registered_handlers": 3,
  "today_tasks": 12,
  "error_rate": 0.03,
  "recent_tasks": [ ...最近 10 条 task_instance ]
}
```

所有新增 API 均需要 Bearer Token 认证（复用现有 `verify_admin` 依赖）。

## 全局布局

```
┌──────────────────────────────────────────────┐
│  渐变背景（全屏，随主题切换）                    │
│  ┌──────────┬───────────────────────────┐    │
│  │ 玻璃侧边栏 │    玻璃内容区              │    │
│  │          │                           │    │
│  │ 🏢 中台   │  页面标题 + 操作按钮        │    │
│  │          │                           │    │
│  │ 📊 仪表盘 │  统计卡片 / 表格 / 弹窗      │    │
│  │ 🔀 路由   │                           │    │
│  │ 👥 用户   │                           │    │
│  │ 📋 监控   │                           │    │
│  │          │                           │    │
│  │ ─────── │                           │    │
│  │ 🎨 主题色 │                           │    │
│  │ ○○○○○○  │                           │    │
│  │          │                           │    │
│  │ 👤 管理员 │                           │    │
│  └──────────┴───────────────────────────┘    │
└──────────────────────────────────────────────┘
```

侧边栏底部固定主题切换器（6 个彩色圆点）和用户信息。

## 认证流程

1. 首次访问 → 检查 localStorage 中是否有 token → 无则跳转 `/login`
2. 登录页：一个输入框 + "进入" 按钮，输入管理员 Token（与 `settings.admin_token` 一致），存入 localStorage（key: `admin_token`）
3. axios interceptor：所有 `/api/*` 请求自动附加 `Authorization: Bearer <token>` header
4. 401 响应 → 清除 localStorage token，跳转 `/login`
5. 登出：侧边栏底部管理员头像点击 → 清除 token → 跳转 `/login`

P0 使用共享静态 Token（整个管理团队使用同一个 token）。RBAC 留给后续迭代。

## 构建和部署

### Vite 配置

```ts
// vite.config.ts
export default defineConfig({
  server: { proxy: { '/api': 'http://localhost:8000', '/webhook': 'http://localhost:8000' } },
  build: { outDir: 'dist' },
});
```

### FastAPI 静态文件托管

```python
# main.py 追加（放在所有 API router 注册之后、/health 之前）
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 仅在 web/dist 目录存在时启用（开发模式不需要）
DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
if os.path.isdir(DIST_DIR):
    # 静态资源（JS/CSS/图片）
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    # SPA fallback：所有非 /api、非 /webhook、非 /health、非 /assets 的 GET 请求返回 index.html
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
```

FastAPI 路由匹配优先级：具体路径 → catch-all `/{path}`。因为 `/api/*`、`/webhook/*`、`/health` 已有具体路由定义，它们优先匹配。catch-all 只处理前端路由（`/`、`/routes`、`/users`、`/tasks`）。

### Dockerfile 更新

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

## 不在本次范围内

- RBAC 多角色权限
- 国际化
- 群映射的 API 自动发现（P1）
- 企微渠道相关功能（P2）
- 移动端适配
- 实时推送（WebSocket）
