# 产品研发模块设计

## 背景

中台骨架（P0）和管理后台前端已完成。现需实现第一个实际业务场景——产品研发任务管理。运营人员在管理后台创建研发主任务并拆分为多个子任务，保存后自动下发到钉钉群卡片，参与者通过群卡片互动完成确认和材料提交。

## 核心概念

- **主任务（RDTask）**：一个产品研发项目，如"春季新品研发"
- **子任务（RDSubTask）**：主任务下的独立工作单元，如"样片拍摄"、"色彩方案"、"后期修图"。每个子任务独立配置负责人、目标群、截止时间
- **自动下发**：保存主任务时，系统为每个子任务自动创建 task_route + task_instance，并通过 TaskEngine 下发钉钉群卡片

## 数据模型

### 新增表：rd_task（产品研发主任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| title | VARCHAR | 主任务标题 |
| description | TEXT | 任务描述 |
| status | VARCHAR | draft / active / completed |
| created_by | VARCHAR | 创建者 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 新增表：rd_sub_task（研发子任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| rd_task_id | FK → rd_task ON DELETE CASCADE | 所属主任务 |
| title | VARCHAR NOT NULL | 子任务标题 |
| description | TEXT | 子任务描述 |
| assignees | TEXT | 负责人列表（JSON 数组，存飞书用户 ID） |
| group_id | VARCHAR NOT NULL | 目标钉钉群 ID |
| platform | VARCHAR NOT NULL | dingtalk / wecom |
| deadline | TIMESTAMP | 截止时间 |
| deliverables | TEXT | 交付物要求（JSON 数组） |
| status | VARCHAR | pending / dispatched / completed |
| task_instance_id | INTEGER | 关联的 task_instance.id（下发后填入），建立索引 |
| task_route_id | INTEGER | 关联的 task_route.id（下发后填入） |
| sort_order | INTEGER DEFAULT 0 | 排序序号 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

## 数据流

### 自动下发架构适配

产品研发任务不走飞书 webhook → 事件网关这条路径，而是由管理后台直接创建。适配方式：

1. **task_route.feishu_table_id** 使用 `rd_sub_task:{id}` 格式作为唯一标识（不是真正的飞书表 ID，而是占位符）
2. **RDTaskHandler.parse_event()** 接收合成事件（synthetic event），从 `field_mapping` 中提取子任务配置数据
3. **合成事件结构**：

```python
{
    "table_id": "rd_sub_task:1",  # 对应 task_route.feishu_table_id
    "record_id": "rd_sub_task_1",
    "action": "create",
    "fields": {
        "title": "样片拍摄",
        "assignees": ["f_user_1", "f_user_2"],
        "deliverables": [{"name": "样片", "type": "image", "count": 3}],
    }
}
```

4. **field_mapping 结构**（存在 task_route 中）：

```json
{
    "rd_sub_task_id": 1,
    "title": "样片拍摄",
    "assignees": ["f_user_1", "f_user_2"],
    "deliverables": [{"name": "样片", "type": "image", "count": 3}]
}
```

TaskEngine.dispatch() 不需要修改——它接收 table_id，查 task_route，调用 handler.parse_event()，返回 TaskData。RDTaskHandler 的 parse_event 从 field_mapping 读取子任务配置，而不是从飞书事件字段。

### 创建流程

```
1. 前端「产品研发」页面：填写主任务 + 添加子任务列表
2. POST /api/rd-tasks  { title, description, sub_tasks: [...] }
3. 后端（在单个数据库事务中）：
   a. 创建 rd_task 记录（status=active）
   b. 为每个子任务创建 rd_sub_task 记录
   c. 为每个子任务自动创建 task_route：
      - feishu_table_id = f"rd_sub_task:{sub_task.id}"
      - handler_name = "RDTaskHandler"
      - platform / group_id 来自子任务配置
      - field_mapping = JSON.dumps({rd_sub_task_id, title, assignees, deliverables})
      - enabled = True
   d. 构造合成事件，调用 TaskEngine.dispatch()
   e. 更新 rd_sub_task.task_instance_id 和 task_route_id
   f. 如果某个子任务下发失败，记录错误但不回滚其他子任务（部分成功）
```

### 互动流程

```
1. 钉钉群显示互动卡片（子任务详情 + 确认按钮）
2. 参与者点击「确认」→ 钉钉回调 → handle_callback("confirm")
3. 状态更新：task_participant.status = confirmed
4. 参与者上传文件 → 文件记录关联到 task_instance
5. 所有参与者完成 → task_instance.status = completed
6. 所有子任务完成 → rd_task.status = completed
```

## RDTaskHandler

实现 BaseHandler 接口的研发任务处理器：

| 方法 | 实现逻辑 |
|------|---------|
| parse_event | 从 field_mapping 提取：title → TaskData.title, assignees → TaskData.participants, deliverables/rd_sub_task_id → TaskData.parameters |
| get_flow | states: [pending, confirmed, submitted, completed]，initial: pending |
| get_roles | roles: [creator, assignee]，default_role: assignee |
| build_card | 根据 state 参数构建不同状态的卡片（见下方卡片样式） |
| get_reminder_rules | 截止前 24h 私聊提醒，逾期升级通知 |
| handle_callback | confirm → confirmed；file_received → 记录文件 |

### 状态流转

```
pending → confirmed:  参与者点击「确认接单」
confirmed → submitted: 参与者上传了要求的交付物
submitted → completed: 所有交付物已接收并验证
```

### 卡片样式

**pending 状态**（初始卡片）：

```
┌─────────────────────────────────┐
│  子任务：样片拍摄                  │
│  ─────────────────────────       │
│  截止时间：2026-06-15             │
│  交付物：3 张样片                  │
│  负责人：张三、李四                │
│  ─────────────────────────       │
│  [确认接单]                       │
└─────────────────────────────────┘
```

**confirmed 状态**（确认后）：

```
┌─────────────────────────────────┐
│  子任务：样片拍摄                  │
│  状态：已确认 ✓                    │
│  截止时间：2026-06-15             │
│  已提交：1/3 件                   │
│  [上传文件]                       │
└─────────────────────────────────┘
```

**completed 状态**（完成后）：

```
┌─────────────────────────────────┐
│  子任务：样片拍摄                  │
│  状态：已完成 ✓✓                   │
│  已交付：3 张样片                  │
└─────────────────────────────────┘
```

```
┌─────────────────────────────────┐
│  子任务：样片拍摄                  │
│  ─────────────────────────       │
│  截止时间：2026-06-15             │
│  交付物：3 张样片                  │
│  负责人：张三、李四                │
│  ─────────────────────────       │
│  [确认接单]                       │
└─────────────────────────────────┘
```

## 后端 API

### 产品研发 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/rd-tasks | 获取主任务列表（含子任务概要） |
| POST | /api/rd-tasks | 创建主任务 + 子任务，自动下发 |
| GET | /api/rd-tasks/{id} | 获取主任务详情（含完整子任务列表及进度） |
| PUT | /api/rd-tasks/{id} | 更新主任务 |
| DELETE | /api/rd-tasks/{id} | 删除主任务（级联删除子任务和关联路由） |
| GET | /api/rd-tasks/{id}/progress | 获取子任务完成进度汇总 |

请求/响应体：

```json
// POST /api/rd-tasks
{
  "title": "春季新品研发",
  "description": "2026年春季新品研发计划",
  "sub_tasks": [
    {
      "title": "样片拍摄",
      "description": "完成 3 组样片拍摄",
      "assignees": ["f_user_1", "f_user_2"],
      "group_id": "group_001",
      "platform": "dingtalk",
      "deadline": "2026-06-15T00:00:00Z",
      "deliverables": [{"name": "样片", "type": "image", "count": 3}],
      "sort_order": 1
    },
    {
      "title": "色彩方案",
      "description": "制定 2 套色彩方案",
      "assignees": ["f_user_3"],
      "group_id": "group_002",
      "platform": "dingtalk",
      "deadline": "2026-06-20T00:00:00Z",
      "deliverables": [{"name": "方案文档", "type": "document", "count": 1}],
      "sort_order": 2
    }
  ]
}

// GET /api/rd-tasks/{id} 响应
{
  "id": 1,
  "title": "春季新品研发",
  "description": "...",
  "status": "active",
  "created_at": "2026-05-29T10:00:00Z",
  "sub_tasks": [
    {
      "id": 1, "title": "样片拍摄", "status": "dispatched",
      "assignees": ["f_user_1", "f_user_2"], "group_id": "group_001",
      "deadline": "2026-06-15T00:00:00Z",
      "task_instance_id": 10,
      "progress": { "total_participants": 2, "confirmed": 1, "submitted": 0 }
    }
  ]
}

// GET /api/rd-tasks/{id}/progress 响应
{
  "total_sub_tasks": 3,
  "completed": 1,
  "in_progress": 1,
  "pending": 1
}
```

### 自动下发逻辑

创建主任务时（POST /api/rd-tasks），后端执行以下步骤：

1. 创建 `rd_task` 记录
2. 遍历 `sub_tasks`，为每个子任务：
   a. 创建 `rd_sub_task` 记录
   b. 创建 `task_route` 记录（handler_name="RDTaskHandler", platform/group_id 来自子任务配置，feishu_table_id 设为 `rd://sub_task/{id}` 占位，field_mapping 存储 assignees/deliverables）
   c. 构造事件数据，调用 `TaskEngine.dispatch()` 创建 `task_instance` 并下发卡片
   d. 更新 `rd_sub_task.task_instance_id` 和 `status="dispatched"`
3. 返回创建结果

### 删除逻辑

删除主任务时（完整清理）：
1. 查找所有关联的 `rd_sub_task`
2. 对每个已下发的子任务（status=dispatched）：
   a. 通过 DingTalkAdapter 更新卡片为"已取消"状态
   b. 删除关联的 `file_record`（FK cascade）
   c. 删除关联的 `reminder_log`（FK cascade）
   d. 删除关联的 `task_participant`
   e. 删除 `task_instance`
   f. 删除 `task_route`
3. 删除所有 `rd_sub_task`（FK ON DELETE CASCADE 自动处理）
4. 删除 `rd_task`

### 输入验证

- 主任务标题：1-200 字符，必填
- 子任务数量：1-20 个
- 子任务标题：1-200 字符，必填
- 负责人：1-10 人，必填
- 平台：仅允许 dingtalk / wecom
- 截止时间：必须在未来
- 交付物：每项包含 name(必填)、type(image/document/video)、count(≥1)

### 进度状态定义

- **pending**：子任务尚未下发（rd_sub_task.status = pending）
- **in_progress**：子任务已下发，至少一个参与者已确认但未全部完成
- **completed**：所有参与者已提交，task_instance.status = completed

## 前端页面

### 侧边栏变更

在"任务监控"下方新增菜单项「产品研发」，图标用 `ExperimentOutlined`。

### 产品研发页面

**路由**：`/rd-tasks`

**列表视图**：
- 主任务卡片列表（标题、子任务数量、状态、进度条、创建时间）
- 点击卡片进入详情

**创建/编辑视图**：
- 主任务信息：标题、描述
- 子任务列表编辑器：
  - 每行一个子任务：标题、描述、负责人（多选下拉，从用户映射加载）、目标群（下拉）、平台、截止时间、交付物要求
  - 可增删行、拖拽排序
- 保存按钮：保存草稿（status=draft）或直接下发（status=active）

**详情视图**：
- 主任务信息 + 进度概览
- 子任务列表：每个子任务显示标题、状态标签、负责人、截止时间、完成进度
- 点击子任务可展开查看参与者状态

## 不在本次范围内

- 子任务的中间状态变更通知（如从 confirmed 变为 submitted 时发新卡片）
- 文件上传到 OSS 并回写飞书（P1 后续）
- 催办调度器自动运行（APScheduler）
- 主任务完成后的汇总通知
- 子任务之间的依赖关系（串行执行）
