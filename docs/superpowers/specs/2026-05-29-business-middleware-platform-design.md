# 业务中台基座设计

## 背景

写真产品研发部门已完成任务分发中台的概念设计（见 `2026-05-26-task-dispatch-middleware-design.md`），现需在此基础上搭建可运行的业务中台基座。核心诉求：

1. **飞书新建数据 → 中台引擎 → 钉钉/企微创建任务**：完整的事件驱动链路
2. **前端可配置**：运营人员可在管理后台配置任务路由、群映射、字段映射
3. **多业务可扩展**：不同业务类型（品鉴会、产品研发、门店运营等）通过插件方式接入
4. **双触达渠道**：钉钉和企微作为并行的触达渠道，适配器层统一翻译

## 设计原则

1. **插件式架构**：每个业务类型是一个独立的 TaskHandler 插件，实现统一接口；新业务 = 新 Handler + 前端配置路由
2. **代码扩展 + 前端参数**：新业务类型需要开发写 Handler 代码，运行参数（群、字段映射等）通过前端配置
3. **飞书为主数据源，中台为运行时层**：业务主数据存飞书多维表，中台只存运行时数据
4. **机器人窗口 + 任务 agent**：以聊天机器人为入口，任务作为 agent 运行在机器人对话中
5. **适配器隔离平台差异**：Handler 输出平台无关的卡片数据，适配器翻译为钉钉/企微格式

## 系统架构

### 分层结构

```
┌──────────────────────────────────────────────────────┐
│                    前端管理后台                        │
│   路由配置 / 群映射 / 用户映射 / 任务监控               │
├──────────────────────────────────────────────────────┤
│                    触达层（适配器）                     │
│  DingTalkAdapter（群聊卡片 + 私聊文件收集）            │
│  WeComAdapter（群聊消息 + 私聊文件收集）               │
├──────────────────────────────────────────────────────┤
│                    中台引擎                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │ 事件网关     │  │ 身份映射     │  │ 消息队列      │ │
│  └──────┬──────┘  └─────────────┘  └──────────────┘ │
│         │                                            │
│  ┌──────▼──────────────────────────────────────────┐ │
│  │          Plugin-based Task Engine               │ │
│  │  TastingHandler / RDTaskHandler / ...Handler    │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐                   │
│  │ 文件管理器   │  │ 催办调度器    │                   │
│  └─────────────┘  └──────────────┘                   │
│  ┌─────────────────────────────────────────────────┐ │
│  │              中台数据库（6 张表）                  │ │
│  └─────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│                    数据层（飞书多维表）                  │
│   品鉴会表 / 研发任务表 / 门店运营表 / ...             │
└──────────────────────────────────────────────────────┘
```

### 数据流向

**下行（飞书 → 钉钉/企微）**：
飞书新增/更新记录 → 飞书自动化 webhook → 事件网关（验签/去重/路由）→ 查 task_route 表确定 Handler → Handler.parseEvent() → Handler.buildCard() → 适配器发送

**上行（钉钉/企微 → 飞书）**：
用户点击按钮/发送文件 → 平台回调 → 事件网关 → 查 task_instance 确定 Handler → Handler.handleCallback() → 更新状态 → 适配器更新卡片/回写飞书

**定时（中台主动）**：
催办调度器扫描 task_participant → 调用 Handler.getReminderRules() → 适配器发送催办消息

## 核心组件

### 1. TaskHandler 插件接口

每个业务类型实现统一的 Handler 接口：

```python
class TaskHandler(ABC):
    def parse_event(self, event: Event, field_mapping: dict) -> TaskData:
        """从飞书事件中解析任务数据，使用 field_mapping 做字段映射"""

    def get_flow(self) -> FlowDefinition:
        """返回该业务的状态机定义（步骤、流转条件）"""

    def get_roles(self) -> RoleDefinition:
        """返回角色定义（创建者/执行者/评审者等）"""

    def build_card(self, task: TaskInstance, state: str) -> CardData:
        """生成平台无关的卡片内容"""

    def get_reminder_rules(self) -> list[ReminderRule]:
        """返回催办规则列表"""

    def handle_callback(self, action: str, user: User, task: TaskInstance) -> TaskUpdate:
        """处理用户交互回调"""
```

Handler 注册机制：启动时自动扫描并注册所有 Handler 类，前端配置路由表绑定 Handler 与飞书表。

**品鉴会 Handler 示例**：

| 方法 | 实现逻辑 |
|------|---------|
| parse_event | 从飞书记录提取：任务名、参会人、截止时间、材料要求 |
| get_flow | 待确认 → 已确认 → 已提交 → 已完成 |
| get_roles | 创建者（管理员）、参与者（参会人） |
| build_card | 群卡片：任务详情 + 确认按钮；私聊：引导上传文件 |
| get_reminder_rules | 50% 未确认私聊提醒、24h 未确认群内@、逾期升级通知 |
| handle_callback | 点确认 → 更新状态；收到文件 → 记录提交 |

**产品研发 Handler 示例**：

| 方法 | 实现逻辑 |
|------|---------|
| get_flow | 待开始 → 进行中 → 待评审 → 已完成（多阶段） |
| get_roles | 创建者、执行者、评审者 |
| build_card | 展示研发阶段、交付物要求、当前进度 |
| get_reminder_rules | 按阶段截止时间催办，评审前提醒 |

### 2. 事件网关（Event Gateway）

接收外部事件，统一处理：

**输入源**：
- 飞书多维表自动化 webhook（记录新增/更新）
- 钉钉互动卡片回调 / 消息回调
- 企微消息回调

**处理流程**：
1. 验证请求签名
2. 基于事件唯一 ID 去重（幂等处理）
3. 根据事件类型和来源表 ID 查 task_route 表，路由到对应 Handler
4. 将事件交给 Handler 处理

### 3. 消息适配器层（Message Adapter）

隔离平台差异，Handler 不关心消息发到哪个平台：

```python
class MessageAdapter(ABC):
    def send_group_card(self, group_id: str, card: CardData) -> str
    def update_group_card(self, card_id: str, card: CardData)
    def send_private_message(self, user_id: str, message: str)
    def send_private_card(self, user_id: str, card: CardData)
    def download_file(self, message_id: str) -> FileData
```

- **DingTalkAdapter**：使用钉钉互动卡片 API（创建/更新卡片、回调处理）
- **WeComAdapter**：使用企微应用消息 API（文本/卡片消息、文件下载）

前端路由配置中指定每个 Handler 使用的平台，适配器层根据配置选择。

### 4. 私聊任务路由（MVP）

不引入 LLM，用规则处理私聊中的文件归属：

```
用户在私聊中发送文件/图片
    │
    ├── 查询 task_participant 表
    │   WHERE platform_user_id = ? AND status IN ('pending', 'confirmed')
    │
    ├── 只有 1 个活跃任务 → 自动归属
    │   → Handler.handleCallback('file_received')
    │   → 回复："已收到，品鉴会准备材料（1/3）"
    │
    ├── 有多个活跃任务 → 发送选择卡片
    │   "你有多个待提交任务，请选择："
    │   [品鉴会准备材料] [研发样片提交] [门店巡检报告]
    │   → 用户点击后归属
    │
    └── 没有活跃任务 → 回复："当前没有待处理的任务"
```

### 5. 共享基础服务

沿用之前 spec 设计：

- **身份映射服务**：飞书用户 ID ↔ 钉钉/企微用户 ID，通过手机号自动匹配
- **文件管理器**：下载平台消息中的文件，存储到 OSS，回写飞书
- **催办调度器**：定时扫描，按 Handler 定义的规则催办
- **消息队列**：控制发送速率（钉钉 20 条/分钟，留 buffer）

## 数据模型

### 中台数据库（6 张表）

#### task_route（前端配置的路由表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| handler_name | VARCHAR | Handler 类名，如 TastingHandler |
| feishu_table_id | VARCHAR | 对应的飞书多维表 ID |
| platform | VARCHAR | 触达平台：dingtalk / wecom / both |
| group_id | VARCHAR | 默认目标群 ID |
| field_mapping | JSONB | 飞书字段 → 任务参数映射 |
| enabled | BOOLEAN | 是否启用 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

#### task_instance（任务实例）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| handler_name | VARCHAR | 哪个 Handler 处理 |
| route_id | FK → task_route | 关联的路由配置 |
| feishu_record_id | VARCHAR | 飞书记录 ID |
| platform | VARCHAR | dingtalk / wecom |
| group_id | VARCHAR | 实际发送的群 |
| card_id | VARCHAR | 互动卡片 ID |
| status | VARCHAR | 任务级状态 |
| flow_state | JSONB | Handler 自定义的状态机数据 |
| deadline | TIMESTAMP | 截止时间 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

#### task_participant（任务参与者）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| task_id | FK → task_instance | |
| feishu_user_id | VARCHAR | |
| platform_user_id | VARCHAR | 钉钉/企微用户 ID |
| role | VARCHAR | 创建者/执行者/评审者 |
| status | VARCHAR | pending/confirmed/submitted/completed |
| file_count | INT | 已提交文件数 |
| submitted_at | TIMESTAMP | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

#### file_record（文件记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| task_id | FK → task_instance | |
| participant_id | FK → task_participant | |
| file_url | VARCHAR | 存储地址 |
| file_name | VARCHAR | |
| file_type | VARCHAR | image/document/video |
| platform_msg_id | VARCHAR | 原始消息 ID |
| created_at | TIMESTAMP | |

#### reminder_log（催办记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| task_id | FK → task_instance | |
| participant_id | FK → task_participant | |
| remind_type | VARCHAR | private/group/escalation |
| remind_count | INT | 已催办次数 |
| next_remind_at | TIMESTAMP | |
| last_remind_at | TIMESTAMP | |

#### user_mapping（用户映射）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| feishu_user_id | VARCHAR | |
| dingtalk_user_id | VARCHAR | |
| wecom_user_id | VARCHAR | |
| phone | VARCHAR | 手机号（匹配用） |
| name | VARCHAR | |
| synced_at | TIMESTAMP | |

## 前端管理后台

### 4 个核心页面

#### 1. 任务路由配置

路由列表表格，每行一条配置：
- Handler 名称（下拉选择已注册的 Handler）
- 飞书表 ID（输入或从已连接的表中选择）
- 触达平台（钉钉/企微/双平台）
- 目标群（下拉选择已配置的群）
- 字段映射（可视化映射编辑器：飞书字段 → 任务参数）
- 启用/禁用开关

点击"配置"展开字段映射面板，以 `飞书字段 → 任务参数` 的形式展示和编辑映射关系。

#### 2. 群映射管理

管理钉钉群和企微群的 ID：
- 群名称、群 ID、平台类型
- 支持手动添加和 API 自动发现
- 测试发送功能（验证群 ID 是否正确）

#### 3. 用户映射管理

飞书 ↔ 钉钉/企微用户映射：
- 映射状态（已匹配/未匹配/冲突）
- 自动同步按钮（触发全量手机号匹配）
- 手动补充映射的编辑功能

#### 4. 任务监控 & 日志

- 任务实例列表（状态、进度、创建时间）
- 消息发送记录
- 错误日志（API 调用失败、映射缺失等）
- 催办记录

## 私聊交互流程

### 单任务场景

```
Bot: "品鉴会准备材料（截止 5/30）
     请在对话中发送你的准备材料"

User: [发送文件/图片]

Bot: "已收到「xxx.pdf」（1/3）
     还需要 2 份材料，请继续发送
     如果已全部提交，请点击 [提交完成]"

User: [发送文件] [发送文件]

Bot: "已收到全部 3 份材料 ✓
     品鉴会准备材料任务已完成"
```

### 多任务场景

```
User: [发送文件]

Bot: "你有 3 个待提交任务，请选择归属："
     [品鉴会准备材料 - 截止5/30]
     [研发样片提交 - 截止6/1]
     [门店巡检报告 - 截止6/3]

User: [点击"品鉴会准备材料"]

Bot: "已归入「品鉴会准备材料」（1/3）..."
```

## Handler 核心类型定义

```python
@dataclass
class TaskData:
    title: str                    # 任务标题
    participants: list[str]       # 参与者飞书用户 ID 列表
    deadline: datetime | None     # 截止时间
    parameters: dict              # Handler 自定义的业务参数

@dataclass
class CardData:
    title: str                    # 卡片标题
    subtitle: str | None          # 副标题
    sections: list[CardSection]   # 卡片内容区域
    actions: list[CardAction]     # 可点击的操作按钮

@dataclass
class CardSection:
    text: str                     # 文本内容
    fields: list[dict] | None     # 键值对字段（如 "截止时间: 5/30"）

@dataclass
class CardAction:
    label: str                    # 按钮文字
    action: str                   # 回调标识（如 "confirm", "submit"）
    style: str = "primary"        # primary / danger / default

@dataclass
class TaskUpdate:
    task_status: str | None       # 任务级状态变更
    participant_status: str | None # 参与者状态变更
    flow_state_update: dict | None # flow_state 的增量更新
    reply_message: str | None     # 回复给用户的消息

@dataclass
class FlowDefinition:
    states: list[str]             # 状态列表（如 ["pending", "confirmed", "submitted", "completed"]）
    transitions: list[dict]       # 转换规则（如 {"from": "pending", "trigger": "confirm", "to": "confirmed"}）
    initial: str                  # 初始状态

@dataclass
class RoleDefinition:
    roles: list[str]              # 角色列表
    default_role: str             # 默认角色（参与者通常为 default_role）
    creator_role: str             # 创建者角色

@dataclass
class ReminderRule:
    condition: str                # 触发条件描述
    offset: str                   # 相对截止时间的偏移（如 "50%", "-24h"）
    channel: str                  # private / group / escalation
    message_template: str         # 催办消息模板
```

## Handler 注册机制

Handler 通过 Python 基类 + 类名约定自动注册：

```python
# 所有 Handler 放在 handlers/ 目录下，继承 BaseHandler
# 文件名约定：handlers/tasting_handler.py → class TastingHandler(BaseHandler)
# 启动时扫描 handlers/ 目录，自动加载所有 BaseHandler 子类
# handler_name = 类名（如 "TastingHandler"），存入 task_route.handler_name

class BaseHandler(TaskHandler, ABC):
    handler_name: str  # 自动设为类名

    @classmethod
    def validate(cls) -> bool:
        """启动时校验接口是否完整实现"""
```

- 命名冲突：启动时检查，同名 Handler 报错拒绝启动
- 接口校验：启动时对所有 Handler 调用 validate()，确保必要方法已实现
- 前端下拉列表：从已注册的 Handler 列表动态生成

## flow_state JSONB 约定

每个 Handler 在 `flow_state` 中存储自己的状态机数据。引擎不解析内容，只透传。

```json
{
  "current_state": "confirmed",
  "steps": [
    {"name": "confirm", "completed": true, "at": "2026-05-29T10:00:00Z"},
    {"name": "upload", "completed": false}
  ],
  "custom": {}
}
```

Handler 通过 `TaskUpdate.flow_state_update` 增量更新，引擎合并到现有 JSONB。

## 双平台任务实例策略

当 `task_route.platform = 'both'` 时，一个飞书记录产生**两个 task_instance**（每个平台各一个），共享同一个 `feishu_record_id`。

```
task_instance:
  id=1, handler=TastingHandler, platform=dingtalk, group_id=xxx, card_id=dt_card_1
  id=2, handler=TastingHandler, platform=wecom, group_id=yyy, card_id=null
```

- task_participant 按平台分别创建（同一用户可能有两个平台的 ID）
- 催办调度器分别处理两个实例
- 状态同步：任一平台的确认/提交都回写飞书，另一平台通过补偿同步感知

### 企微卡片限制说明

企微不支持钉钉式的互动卡片原地更新。WeComAdapter 的 `update_group_card()` 行为：

- **发送新消息**替代原地更新（群内追加一条更新消息）
- 私聊中使用文本消息 + 链接引导操作
- P2 实现时评估企微模板卡片消息是否可用，若支持则升级

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 钉钉/企微 API 调用失败 | 指数退避重试（1s/2s/4s），最多 3 次，失败后写入 error_log 并通知管理员 |
| Handler.parse_event() 抛异常 | 捕获异常，记录原始事件到 error_log，不中断事件网关 |
| Handler.build_card() 抛异常 | 同上，跳过该任务的消息发送，标记 task_instance.status = 'error' |
| 飞书 webhook 丢失 | 每 5 分钟轮询飞书多维表，查询最近更新的记录，与本地 task_instance 对比，处理差异（飞书为准） |
| 同一事件重复触发 | 事件网关基于 feishu_record_id + action 做幂等去重 |
| 身份映射缺失 | 跳过该参与者，在群卡片中提示管理员补充映射 |
| 文件下载失败 | 重试 1 次，失败后通知用户"文件接收异常，请重新发送" |
| 用户在截止后提交 | 仍接收，task_participant 标记 submitted_at 但 flow_state 记录 is_overdue=true |

## 补偿同步机制

飞书 webhook 可能丢失（网络故障、服务重启等），中台定时补偿：

- 每 5 分钟轮询飞书多维表，查询 `最近修改时间 > 上次轮询时间` 的记录
- 与 task_instance 对比，处理差异：
  - 飞书有但中台无 → 补创建任务
  - 飞书状态变更但中台未同步 → 以飞书为准更新中台
- 去重：基于 feishu_record_id，跳过已处理的记录
- 冲突处理：飞书是 Source of Truth，中台数据始终向飞书对齐

## 安全考虑

### API 凭证管理
- 飞书和钉钉/企微的 app_id/app_secret/tenant_token 使用环境变量注入
- 前端管理后台通过 HTTP Basic Auth 或简单 token 认证（初期）
- 后续引入 RBAC（管理员/操作员/只读）

### 管理后台安全
- 仅内网可访问，不暴露公网
- 操作日志记录所有配置变更

### 数据安全
- 文件存储 URL 使用签名链接，设置过期时间（默认 7 天）
- 用户映射表中手机号仅在匹配时使用，API 返回时脱敏
- 所有外部通信使用 HTTPS

### 平台 API 频率限制

| 平台 | 限制项 | 值 | 应对策略 |
|------|--------|-----|---------|
| 钉钉 | 自定义机器人发送频率 | 20 条/分钟 | 消息队列限速 15 条/分钟 |
| 钉钉 | 标准版 API 调用额度 | 10,000 次/月 | 可能需升级专业版（9,800 元/年） |
| 钉钉 | 群聊文件接收 | 不支持 | 文件收集走私聊 |
| 企微 | Webhook 机器人发送频率 | 20 条/分钟 | 同上 |
| 企微 | 自建应用消息频率 | 200 次/分钟 | 较宽松 |
| 企微 | 群聊文件接收 | 不支持 | 同钉钉 |

## 催办引擎级约束

无论 Handler 如何定义催办规则，引擎层强制执行：
- **同一用户同一任务每天最多催办 2 次**（由 reminder_log 表计数控制）
- **催办时间窗口**：仅在工作日 9:00-21:00 发送催办消息

## 管理后台 API 概要

### 路由配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/routes | 获取所有路由配置 |
| POST | /api/routes | 创建路由配置 |
| PUT | /api/routes/{id} | 更新路由配置 |
| DELETE | /api/routes/{id} | 删除路由配置 |
| GET | /api/handlers | 获取已注册的 Handler 列表（前端下拉用） |

### 群映射

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/groups | 获取所有群映射 |
| POST | /api/groups | 添加群映射 |
| DELETE | /api/groups/{id} | 删除群映射 |
| POST | /api/groups/{id}/test | 测试发送（验证群 ID） |

### 用户映射

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users | 获取用户映射列表（支持分页和状态筛选） |
| POST | /api/users/sync | 触发全量同步 |
| PUT | /api/users/{id} | 手动补充映射 |

### 任务监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tasks | 任务实例列表（支持状态筛选） |
| GET | /api/tasks/{id} | 任务详情（含参与者状态） |
| GET | /api/tasks/{id}/logs | 任务执行日志 |
| GET | /api/errors | 错误日志列表 |

认证：所有 API 使用 Bearer Token（管理后台登录后获取）。

## 数据迁移说明

本 spec 替代 `2026-05-26-task-dispatch-middleware-design.md` 中的数据模型。由于前序 spec 未进入实施阶段，无需数据迁移——直接使用新模型创建数据库。

## 扩展预留

### LLM Agent 接入点（V2）

当前 MVP 使用规则处理私聊路由。架构预留以下接入点，供后续引入 Hermes Agent 或类似 LLM Agent：

1. **ConversationManager 接口**：当前用规则实现 `route(message)` 方法，V2 替换为 LLM 意图识别
2. **conversation_state 表**：V2 新增，维护用户对话上下文（当前活跃任务、对话历史摘要）
3. **intent_classifier 接口**：当前硬编码关键词判断，V2 接入 LLM 做意图分类

### 新业务扩展流程

1. 开发新的 Handler 类，实现 6 个接口方法
2. 在前端"任务路由配置"页面添加一条路由
3. 配置字段映射和目标群
4. 启用

无需修改引擎代码。

## 技术选型

| 组件 | 方案 | 备注 |
|------|------|------|
| 后端语言 | Python | 与现有 lighting-sim 服务一致 |
| 框架 | FastAPI | 已有项目经验 |
| 数据库 | SQLite（初期）→ PostgreSQL | 初期单文件部署，后续迁移 |
| 文件存储 | 阿里云 OSS / 本地 | 按现有基础设施选 |
| 定时任务 | APScheduler | 简单可靠 |
| 前端 | React / Vue | 管理后台 SPA |
| 部署 | Docker 单容器起步 | 初期不需要微服务 |

## 阶段规划

| 阶段 | 范围 | 交付物 |
|------|------|--------|
| P0：中台骨架 | 事件网关 + 身份映射 + 消息适配器 + 基础路由 | 能接收多源事件并做路由转发的最小后端 |
| P1：品鉴会闭环 | TastingHandler 完整实现 + 前端路由配置页面 | 飞书品鉴会表 → 钉钉群卡片下发 → 确认 → 文件收集 → 催办 |
| P2：企微渠道 | WeComAdapter + 企微群/私聊支持 | 双渠道触达能力 |
| P3：多业务扩展 | RDTaskHandler + 前端完整管理后台 | 第二个业务接入验证扩展性 |
| V2（后续） | LLM Agent 接入 + conversation_state | 智能对话路由和意图理解 |

## 与已有设计的关系

本设计是 `2026-05-26-task-dispatch-middleware-design.md` 的演进版本：
- 保留原有的三层架构、事件网关、身份映射、文件管理、催办调度设计
- 新增：插件式 Handler 接口、消息适配器层（双平台）、前端管理后台
- 调整：数据模型新增 task_route 表，新增 flow_state JSONB 字段支持 Handler 自定义状态机
- 延后：conversation_state 表和 LLM Agent 能力移至 V2
