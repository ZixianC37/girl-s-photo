# 端到端链路补全设计

## 目标

补全「产品研发创建 → 钉钉卡片下发 → 用户确认」的端到端链路，使其可以实际运行。

## 当前状态

代码基础比预期完整：
- TaskEngine.dispatch() / handle_callback() — 已实现完整
- RDTaskHandler — 6 个接口方法都有实现
- rd_tasks_api.py — 自动下发逻辑已有（创建 route + instance + dispatch）
- DingTalkAdapter — 完整（send/update card, private message, file download）

## 需要修复的 5 个缺口

### 缺口 1：build_card() 卡片内容不准确

**现状**：`build_card()` 用 `task.handler_name` 作为卡片标题（显示为 "子任务：RDTaskHandler"），没有显示子任务的实际标题和负责人。

**修复**：
- 从 task_instance.flow_state 中读取子任务元数据（title、deliverables、assignees）
- dispatch() 时将 field_mapping 中的关键信息写入 flow_state
- build_card() 根据 flow_state 构建准确的卡片内容

**卡片内容（按状态）**：
- pending：子任务标题 + 截止时间 + 交付物列表 + 负责人 + [确认接单] 按钮
- confirmed：标题 + 已确认状态 + 已提交进度 + [上传文件] 按钮
- completed：标题 + 已完成 + 已交付文件数

### 缺口 2：handle_callback() 不更新 flow_state

**现状**：`handle_callback()` 只返回新状态，不记录状态变更细节到 flow_state。

**修复**：
- confirm 时在 flow_state 中记录确认时间和用户
- upload 时记录文件信息
- 返回 flow_state_update 字典，由 TaskEngine 合并

### 缺口 3：参与者 platform_user_id 为空

**现状**：dispatch() 创建 participant 时 `platform_user_id=None`，导致 handle_callback() 按此字段查找参与者时找不到匹配。

**修复**：
- dispatch() 创建 participant 后，调用 IdentityService 解析飞书用户 ID 到平台用户 ID
- handle_callback() 增加 fallback：如果按 platform_user_id 找不到，按 feishu_user_id 关联查找

### 缺口 4：钉钉适配器卡片的实际格式

**现状**：DingTalkAdapter.send_group_card() 接收 CardData 对象，需确认其正确转换为钉钉互动卡片 API 所需的 JSON 格式。

**修复**：
- 验证适配器将 CardData → 钉钉卡片 JSON 的转换逻辑
- 确认卡片回调按钮的 actionData 格式正确（包含 card_id、action 值）
- 如有问题则修正

### 缺口 5：端到端验证

**现状**：没有集成测试验证完整链路。

**修复**：
- 编写集成测试：创建 rd_task → 验证 task_instance 创建 → 验证 adapter.send_group_card 被调用
- 编写回调测试：模拟钉钉回调 → 验证状态更新 → 验证 adapter.update_group_card 被调用
- 手动测试：用真实/模拟数据跑一次完整流程

## 不在范围内

- WeComAdapter 实现（仅钉钉）
- 飞书 webhook → 引擎链路（当前只做管理后台创建 → 引擎下发）
- 文件上传到 OSS
- 催办调度器自动运行
- 前端 UI 新增功能
