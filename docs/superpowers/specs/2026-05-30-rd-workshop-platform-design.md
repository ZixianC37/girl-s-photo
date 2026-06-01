# 研发工作坊平台设计规格

**Date:** 2026-05-30
**Status:** Draft

## 概述

将现有业务中台改造为**研发工作坊平台**，以"工作坊"为核心可视化概念，管理写真产品从灵感收集到门店上新的全流程。管理者在中台创建研发项目，系统按模板自动生成各阶段子任务，通过钉钉群卡片和私聊实现任务分发、交付物收集和异常处理。

## 核心设计决策

1. **通知链而非审批流** — 每个环节完成后自动通知下一环节负责人，无需管理者逐个审批
2. **管理者集中分配** — 只有管理者操作后台，团队成员在钉钉接单和提交交付物
3. **全流程数字化** — 8 个阶段全部走中台管理
4. **2D 像素风工作坊视图** — 仪表盘以游戏化场景展示项目进度和人员状态

## 菜单结构

```
📊 仪表盘        — 工作坊场景视图 + 运营概览统计 + 异常告警
📋 研发项目      — 项目 CRUD + 流水线进度管理 + 交付物汇总
📝 模板管理      — 流水线阶段模板配置（字段、默认负责人、交付物、催办规则）
🔔 异常中心      — 超时/返工/裁决/暂停的集中处理
⚙️ 系统配置      — 路由管理 + 用户映射 + 群映射（Tab 页）
```

移除原有独立的"产品研发"、"任务路由"、"用户映射"页面，功能分别合并到上述新页面。

## 研发流水线

### 标准流程（8 个阶段）

```
1.灵感收集 → 2.灵感创作 → 3.品鉴会 → 4.服化道方案
→ 5.样片拍摄 → 6.确认上新 → 7.运营安排 → 8.正式上新
```

每个阶段定义：
- 阶段名称和描述
- 默认负责人（可配置）
- 交付物列表（名称 × 数量）
- 超时规则和催办策略
- 完成后的通知目标

### 阶段完成条件

交付物按**阶段**计算（非按个人）。一个阶段的所有交付物由所有负责人共同完成。任何负责人都可以上传文件，当交付物全部收齐后该阶段自动标记为完成。

### 阶段模板配置示例

```
阶段: 样片拍摄
  默认负责人: (空，每次手动填)
  交付物: [样片 × 3 组]
  超时规则: 5 天
  催办策略:
    - 首次: 24h 后私聊提醒
    - 第二次: +12h 后群@提醒
    - 升级: +24h 后通知管理者
    - 最大催办次数: 3
  通知目标:
    - manager（管理者私聊通知）
    - next_stage_assignee（自动推进到下一阶段）
```

### 项目创建流程

1. 管理者选择模板 → 系统生成阶段子任务（草稿）
2. 管理者补充各阶段的：负责人、截止日期、目标钉钉群
3. 点击"启动项目" → 第一个阶段下发钉钉卡片
4. 后续阶段通过通知链自动串联推进

## 工作坊 2D 场景视图

### 概念

每个研发项目渲染为一个**像素风 2D 工作坊场景**。工位代表流水线阶段，角色（钉钉头像）代表参与者，动画表现当前状态。

### 场景布局

- 上方：工位区域（灵感墙、创作台、品鉴桌、服化间、摄影棚、上新台、运营部、门店）
- 下方：休息区（空闲人员）
- 右侧：人员列表面板

### 工位状态

| 状态 | 视觉表现 |
|------|---------|
| 已完成 | 绿色勾 + 角色举旗 |
| 进行中 | 蓝色脉冲 + 角色工作动画 + 气泡显示任务名 |
| 待开始 | 灰色 + 角色在休息区 |
| 异常 | 红色闪烁 + 角色头顶感叹号 |
| 暂停 | 黄色 + 角色坐下 |
| 返工中 | 橙色闪烁 + 角色头顶回旋箭头 |

### 角色表现

- 使用钉钉头像作为角色图标
- 角色自动出现在当前工作工位旁
- 空闲时出现在底部休息区
- 移动时有走动动画（从休息区走到工位）

### 交互

- 点击角色 → 右侧面板筛选到该人 → 展开详情（当前任务、交付物、时间线、催办按钮）
- 点击工位 → 展示该阶段信息（进度、参与者状态、交付物汇总）
- 不选中任何角色 → 右侧面板显示全部成员
- 场景支持缩放和拖拽

### 技术实现

- SVG 绘制场景和角色（与 React 集成，支持事件绑定）
- CSS `@keyframes` 实现动画（呼吸、闪烁、走动）
- 钉钉头像通过 `<image>` 标签嵌入 SVG
- 像素风通过 `image-rendering: pixelated` CSS 属性实现

## 研发项目页面

### 项目列表

卡片式布局，每张卡片包含：
- 项目状态颜色条（进行中=蓝、已完成=绿、暂停=黄）
- 项目名称
- 进度条（当前阶段 / 总阶段数）
- 状态标签
- 异常标记（有异常时显示红色角标）

### 项目详情页

顶部：项目名称 + 创建时间 + 整体状态

Tab 切换：
- **工作坊视图** — 完整 2D 场景（与仪表盘共享组件）
- **时间线视图** — 纵向时间轴，每个阶段的起止时间、负责人、交付物
- **交付物汇总** — 所有阶段交付物的网格展示，支持预览

## 通知链

### 自动通知规则

上游环节完成 → 系统自动通知下游：

| # | 上游完成 | 通知目标 | 通知方式 |
|---|---------|---------|---------|
| 1 | 灵感收集 | 创作者 | 私聊卡片（含灵感素材缩略图）|
| 2 | 灵感创作 | 品鉴群 | 群卡片（含创作方案）|
| 3 | 品鉴会 | 服化负责人 | 私聊卡片（含品鉴结论）|
| 4 | 服化道方案 | 拍摄群 | 群卡片（含道具清单）|
| 5 | 样片拍摄 | 管理者 + 运营 | 私聊卡片（含样片预览）+ 运营群通知 |
| 6 | 确认上新 | 运营群 | 群卡片（含上新指令）|
| 7 | 运营安排 | 门店群 | 群卡片（含上架执行计划）|
| 8 | 正式上新 | 管理者 | 私聊闭环通知 + 项目标记 completed |

### 钉钉卡片类型

**任务下发卡片** — 接到任务时看到：
- 标题：子任务名称
- 正文：交付物、负责人、截止时间
- 按钮：确认接单 / 上报问题

**进度更新卡片** — 群内展示整体进度：
- 项目名称
- 流水线各阶段状态
- 已确认人数
- 按钮：查看详情

**异常告警卡片** — 超时/异常时：
- 告警类型和描述
- 超时时长
- 按钮：催办 / 换人 / 暂停环节

## 异常处理

### 无响应/失联

自动催办流程：
1. 任务下发后 24h 无人接单 → 钉钉私聊提醒
2. +12h 后 → 钉钉群@提醒
3. +24h 后 → 通知管理者，异常中心出现红色告警
4. 管理者操作：催办 / 换人 / 暂停环节

催办策略在模板里可配置（首次延迟、间隔、最大次数）。

### 交付不合格/返工

1. 管理者查看交付物 → 标记"不合格" + 填写原因
2. 系统回退：环节状态变为"返工中"
3. 钉钉通知负责人返工原因
4. 负责人重新提交交付物
5. 管理者再次审核

工作坊表现：角色头顶🔄回旋箭头，工位闪烁橙色。

### 品鉴会意见分歧

1. 品鉴会结论为"待定"或评分差异大
2. 系统不自动推进下一环节
3. 钉钉通知管理者："品鉴会结论待确认"
4. 管理者在后台查看各方意见 → 做最终决策 → 手动推进

工作坊表现：品鉴桌上有❓标记。

### 资源不到位

1. 负责人在钉钉卡片点"上报问题" + 填写原因
2. 该环节自动暂停
3. 钉钉通知管理者
4. 管理者操作：等待恢复 / 调整方案 / 跳过该环节

工作坊表现：工位变黄，角色坐下。

### 异常中心页面

按紧急程度排序：

| 优先级 | 类型 | 颜色 |
|--------|------|------|
| 紧急 | 超时升级（催办无果）| 红色 |
| 高 | 需裁决（品鉴分歧）| 橙色 |
| 中 | 待审核（交付物待确认）| 黄色 |
| 低 | 已暂停（资源不到位）| 蓝色 |

每张异常卡片提供快捷操作按钮。

## 模板管理页面

### 流水线模板列表

展示已有模板，支持创建/编辑/删除/复制。
- 不能删除被活跃项目引用的模板
- 删除模板不影响已创建的项目（项目在创建时快照阶段定义）

### 模板编辑器

- 左侧：阶段列表（可拖拽排序、增删，1-20 个阶段）
- 右侧：选中阶段的配置面板
  - 阶段名称（必填）、描述
  - 默认负责人（可选）
  - 交付物列表（名称 × 数量，可增删）
  - 超时天数（> 0）
  - 催办策略配置
  - 通知目标配置：
    ```json
    "notify_target": {
      "type": "next_stage_assignee | manager | specific_group | multiple",
      "group_name": "品鉴群",
      "also_notify_manager": true
    }
    ```

## 数据模型变更

### 数据模型层级

```
rd_project (新增 — 项目)
  └── rd_sub_task (现有，增加 project_id FK + stage_index)
       └── task_instance (现有，增加 stage_index)
```

`RDTask` 表保留作为向后兼容，但新流程中 `rd_project` 替代其角色。后续迁移时可将 `RDTask` 数据合并到 `rd_project`。

### 新增表：pipeline_template

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(200) | 模板名称 |
| description | TEXT | 模板描述 |
| stages | TEXT(JSON) | 阶段定义列表（1-20 个）|
| created_at | DATETIME | |
| updated_at | DATETIME | |

stages JSON 结构：
```json
[
  {
    "name": "灵感收集",
    "description": "团队提交灵感和参考素材",
    "default_assignees": [],
    "deliverables": [{"name": "参考图", "count": 5}],
    "timeout_days": 3,
    "reminder_policy": {
      "first_delay_hours": 24,
      "interval_hours": 12,
      "escalation_delay_hours": 24,
      "max_retries": 3
    },
    "notify_target": {
      "type": "next_stage_assignee",
      "also_notify_manager": false
    }
  }
]
```

### 新增表：rd_project

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(200) | 项目名称 |
| description | TEXT | |
| template_id | INTEGER FK(pipeline_template) | 创建时快照模板，模板后续修改不影响项目 |
| stages_snapshot | TEXT(JSON) | 创建时复制的阶段定义 |
| status | VARCHAR(20) | draft/active/paused/completed |
| created_by | VARCHAR(100) | 创建者标识 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

不使用 `current_stage_index`。当前阶段通过查询该项目下状态为 active/rework/blocked 的 `rd_sub_task` 动态得出。支持多阶段并行（如上游返工时下游已在进行）。

### 修改表：rd_sub_task

新增字段：
- `project_id` INTEGER FK(rd_project) — 所属项目
- `stage_index` INTEGER — 阶段序号（对应 stages_snapshot 索引）
- `stage_name` VARCHAR(100) — 阶段名称
- `status` 增加值：`rework`（返工中）、`blocked`（暂停）

### 状态映射（三层）

| 层级 | 状态值 | 说明 |
|------|--------|------|
| **rd_project** | draft / active / paused / completed | 项目级别 |
| **rd_sub_task** | pending / dispatched / rework / blocked / completed | 阶段级别 |
| **task_instance** | pending / confirmed / submitted / completed | 任务实例级别 |

`rework` 在 `rd_sub_task` 层级。`TaskInstance` 层级的状态不变（返工时创建新的 TaskInstance）。

## API 端点

### 项目 API（rd_projects_api.py）

```
GET    /api/projects              — 项目列表（支持 ?status= 过滤）
POST   /api/projects              — 创建项目（body: name, template_id, stage_overrides[]）
GET    /api/projects/{id}         — 项目详情（含阶段状态和交付物）
PATCH  /api/projects/{id}         — 更新项目（body: status=active/paused）
POST   /api/projects/{id}/advance — 手动推进到下一阶段（品鉴分歧等场景）
POST   /api/projects/{id}/rework  — 回退某阶段（body: stage_index, reason）
```

### 模板 API（templates_api.py）

```
GET    /api/templates             — 模板列表
POST   /api/templates             — 创建模板（body: name, stages[]）
GET    /api/templates/{id}        — 模板详情
PUT    /api/templates/{id}        — 更新模板
DELETE /api/templates/{id}        — 删除模板（仅无活跃项目引用时可删）
POST   /api/templates/{id}/clone  — 复制模板
```

### 异常 API（anomalies_api.py）

```
GET    /api/anomalies             — 异常列表（支持 ?severity= & ?project_id= 过滤）
PATCH  /api/anomalies/{id}        — 处理异常（body: action=reassign|resume|skip|dismiss, data）
```

## 催办服务

### 执行模型

FastAPI 启动时创建 `asyncio` 后台任务，每 **5 分钟**轮询一次：
1. 查询所有 `status=dispatched` 且 `created_at < now() - timeout` 的 `rd_sub_task`
2. 根据 `reminder_policy` 计算当前应执行的动作（私聊/群@/升级）
3. 调用 DingTalkAdapter 发送催办消息
4. 记录 `ReminderLog`
5. 超过最大催办次数 → 写入异常中心

## 仪表盘设计

工作坊场景视图为主，上方保留运营概览统计条：
- 活跃项目数 / 已完成项目数 / 当前异常数
- 最近完成的阶段（缩略时间线）

点击某个项目的工作坊缩略图 → 跳转到研发项目详情页。

## 文件结构

```
中台/
├── app/
│   ├── models/
│   │   ├── tables.py              # 新增 PipelineTemplate, RDProject
│   │   └── types.py               # 新增 stage 相关类型
│   ├── handlers/
│   │   ├── rd_task_handler.py      # 修改：支持返工、上报问题
│   │   └── reminder_handler.py    # 新增：催办逻辑
│   ├── services/
│   │   ├── pipeline_service.py    # 新增：流水线推进逻辑
│   │   ├── notification_chain.py  # 新增：通知链
│   │   ├── reminder_service.py    # 新增：催办服务（asyncio 后台轮询）
│   │   └── file_collector.py      # 已有
│   ├── admin/
│   │   ├── rd_projects_api.py     # 新增：项目 CRUD + 启动/暂停
│   │   ├── templates_api.py       # 新增：模板 CRUD
│   │   ├── anomalies_api.py       # 新增：异常查询和处理
│   │   └── rd_tasks_api.py        # 修改：关联 project_id
│   └── engine/
│       └── task_engine.py         # 修改：通知链触发
├── web/src/
│   ├── pages/
│   │   ├── Dashboard.tsx          # 重写：工作坊场景 + 运营统计条
│   │   ├── RDProjects.tsx         # 新增：项目列表+详情
│   │   ├── Templates.tsx          # 新增：模板管理
│   │   ├── Anomalies.tsx          # 新增：异常中心
│   │   └── Settings.tsx           # 新增：合并路由+用户+群配置
│   ├── components/
│   │   ├── WorkshopScene.tsx      # 新增：2D 工作坊 SVG 场景
│   │   ├── WorkshopStation.tsx    # 新增：工位组件
│   │   ├── WorkshopCharacter.tsx  # 新增：角色组件（头像+动画）
│   │   ├── CharacterPanel.tsx     # 新增：右侧人员面板
│   │   └── StageTimeline.tsx      # 新增：时间线视图
│   └── api/
│       ├── projects.ts            # 新增
│       ├── templates.ts           # 新增
│       └── anomalies.ts           # 新增
└── tests/
    ├── test_pipeline_service.py   # 新增
    ├── test_notification_chain.py # 新增
    ├── test_reminder_service.py   # 新增
    ├── test_anomalies_api.py      # 新增
    └── test_rd_projects_api.py    # 新增
```

## 与现有系统的关系

- 现有 `RDTask` 向后兼容，新流程用 `rd_project` 替代
- `RDSubTask` 增加 `project_id` FK，同时保持对 `RDTask` 的兼容
- 现有 `TaskEngine` + `DingTalkAdapter` + `FileCollector` 继续使用
- 新增 `PipelineService` 封装流水线推进逻辑（上游完成 → 通知下游）
- 新增 `ReminderService` 封装催办逻辑（asyncio 后台轮询，5 分钟间隔）
- 前端工作坊视图是全新组件，与现有页面独立

## 延期功能

以下功能在设计范围之外，后续迭代：
- 移动端适配
- 实时 WebSocket 推送（暂用轮询）
- 自定义角色装扮/外观
- 数据统计报表（环节耗时分析、人员效率）
- 飞书多维表双向同步
- 多品牌/多门店的权限隔离
