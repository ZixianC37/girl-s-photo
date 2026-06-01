# R&D Workshop Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the workshop-themed frontend for the R&D platform — a pixel-art 2D workshop scene dashboard, project management pages, template editor, and anomaly center — on top of the existing Ant Design + React 19 + Vite codebase.

**Architecture:** New pages added to the existing SPA. Workshop scene is an SVG component rendered inline in React, with CSS animations for character/workstation states. API layer uses the existing Axios client pattern. Pages follow the existing GlassCard + Ant Design component patterns.

**Tech Stack:** React 19 / TypeScript / Ant Design v6 / React Router v7 / Axios / Vite / SVG + CSS animations

**Spec:** `docs/superpowers/specs/2026-05-30-rd-workshop-platform-design.md`

---

## File Structure

```
中台/web/src/
├── api/
│   ├── client.ts                # Existing — no change
│   ├── templates.ts             # New: template CRUD API
│   ├── projects.ts              # New: project CRUD + pipeline API
│   └── anomalies.ts             # New: anomaly query + resolve API
├── components/
│   ├── AppLayout.tsx             # Modify: add new sidebar items
│   ├── GlassCard.tsx             # No change
│   ├── ProtectedRoute.tsx        # No change
│   ├── ThemeSwitcher.tsx         # No change
│   └── workshop/                 # New directory
│       ├── WorkshopScene.tsx     # Main SVG workshop scene
│       ├── Workstation.tsx       # Individual workstation component
│       ├── WorkshopStatusIcon.tsx# Status indicator overlay
│       └── workshop.css          # Workshop-specific styles + animations
├── pages/
│   ├── Dashboard.tsx             # Modify: replace with workshop dashboard
│   ├── Login.tsx                 # No change
│   ├── Templates.tsx             # New: template list + editor
│   ├── TemplateEditor.tsx        # New: template edit/create form
│   ├── Projects.tsx              # New: project list page
│   ├── ProjectDetail.tsx         # New: project detail with tabs
│   ├── ProjectTimeline.tsx       # New: vertical timeline tab
│   ├── Anomalies.tsx             # New: anomaly center
│   ├── RDTasks.tsx               # Existing — keep
│   ├── Routes.tsx                # Existing — keep
│   ├── TaskMonitor.tsx           # Existing — keep
│   └── UserMapping.tsx           # Existing — keep
├── App.tsx                       # Modify: add new routes
└── main.tsx                      # No change
```

---

## Task 1: API Layer — templates, projects, anomalies

**Files:**
- Create: `中台/web/src/api/templates.ts`
- Create: `中台/web/src/api/projects.ts`
- Create: `中台/web/src/api/anomalies.ts`

- [ ] **Step 1: Create templates API**

Create `中台/web/src/api/templates.ts`:

```typescript
import client from './client';

export interface StageDef {
  name: string;
  description?: string;
  default_assignees?: string[];
  deliverables?: { name: string; count: number }[];
  timeout_days?: number;
  reminder_policy?: {
    first_delay_hours: number;
    interval_hours: number;
    escalation_delay_hours: number;
    max_retries: number;
  };
  notify_target?: {
    type: string;
    also_notify_manager?: boolean;
    group_name?: string;
  };
}

export interface PipelineTemplate {
  id: number;
  name: string;
  description: string;
  stages: string; // JSON string
  created_at: string;
  updated_at: string;
}

// NOTE: follow existing .then(r => r.data) pattern from rdTasks.ts
export const listTemplates = () =>
  client.get<PipelineTemplate[]>('/api/templates').then(r => r.data);

export const getTemplate = (id: number) =>
  client.get<PipelineTemplate>(`/api/templates/${id}`).then(r => r.data);

export const createTemplate = (data: { name: string; description?: string; stages: StageDef[] }) =>
  client.post<PipelineTemplate>('/api/templates', data).then(r => r.data);

export const updateTemplate = (id: number, data: { name?: string; description?: string; stages?: StageDef[] }) =>
  client.put<PipelineTemplate>(`/api/templates/${id}`, data).then(r => r.data);

export const deleteTemplate = (id: number) =>
  client.delete(`/api/templates/${id}`).then(r => r.data);

export const cloneTemplate = (id: number) =>
  client.post<PipelineTemplate>(`/api/templates/${id}/clone`).then(r => r.data);
```

- [ ] **Step 2: Create projects API**

Create `中台/web/src/api/projects.ts`:

```typescript
import client from './client';

export interface SubTask {
  id: number;
  project_id: number;
  stage_index: number;
  stage_name: string;
  title: string;
  description: string;
  assignees: string; // JSON string
  group_id: string;
  platform: string;
  deadline: string | null;
  deliverables: string; // JSON string
  status: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface RDProject {
  id: number;
  name: string;
  description: string;
  template_id: number;
  stages_snapshot: string;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  sub_tasks?: SubTask[];
}

export const listProjects = (params?: { status?: string }) =>
  client.get<RDProject[]>('/api/projects', { params }).then(r => r.data);

export const getProject = (id: number) =>
  client.get<RDProject>(`/api/projects/${id}`).then(r => r.data);

export const createProject = (data: {
  name: string;
  description?: string;
  template_id: number;
  stage_overrides?: Record<string, {
    assignees?: string[];
    deadline?: string;
    group_id?: string;
    platform?: string;
  }>;
}) => client.post<RDProject>('/api/projects', data).then(r => r.data);

export const startProject = (id: number) =>
  client.post<RDProject>(`/api/projects/${id}/start`).then(r => r.data);

export const advanceProject = (id: number, stageIndex: number) =>
  client.post<RDProject>(`/api/projects/${id}/advance`, { stage_index: stageIndex }).then(r => r.data);

export const reworkStage = (id: number, stageIndex: number, reason?: string) =>
  client.post<RDProject>(`/api/projects/${id}/rework`, { stage_index: stageIndex, reason }).then(r => r.data);

export const patchProjectStatus = (id: number, status: string) =>
  client.patch<RDProject>(`/api/projects/${id}`, { status }).then(r => r.data);

export const deleteProject = (id: number) =>
  client.delete(`/api/projects/${id}`).then(r => r.data);
```

- [ ] **Step 3: Create anomalies API**

Create `中台/web/src/api/anomalies.ts`:

```typescript
import client from './client';

export interface Anomaly {
  id: number;
  type: string;
  severity: string;
  project_id: number;
  project_name: string | null;
  stage_name: string;
  stage_index: number;
  assignees: string[];
  status: string;
  created_at: string;
  updated_at: string;
}

export const listAnomalies = (params?: { project_id?: number; severity?: string }) =>
  client.get<Anomaly[]>('/api/anomalies', { params }).then(r => r.data);

export const resolveAnomaly = (id: number, action: string, data?: Record<string, unknown>) =>
  client.patch<Anomaly>(`/api/anomalies/${id}`, { action, data }).then(r => r.data);
```

- [ ] **Step 4: Commit**

```bash
git add 中台/web/src/api/templates.ts 中台/web/src/api/projects.ts 中台/web/src/api/anomalies.ts
git commit -m "feat: add frontend API layer for templates, projects, and anomalies"
```

---

## Task 2: App Shell — routes and sidebar navigation

**Files:**
- Modify: `中台/web/src/App.tsx`
- Modify: `中台/web/src/components/AppLayout.tsx`

- [ ] **Step 1: Add new routes to App.tsx**

In `中台/web/src/App.tsx`, add lazy imports and routes for the new pages. Add these imports after existing ones:

```typescript
const Templates = lazy(() => import('./pages/Templates'));
const TemplateEditor = lazy(() => import('./pages/TemplateEditor'));
const Projects = lazy(() => import('./pages/Projects'));
const ProjectDetail = lazy(() => import('./pages/ProjectDetail'));
const Anomalies = lazy(() => import('./pages/Anomalies'));
```

Add these routes inside the `<Routes>` block (after existing routes, before the catch-all):

```tsx
<Route path="/templates" element={<Templates />} />
<Route path="/templates/new" element={<TemplateEditor />} />
<Route path="/templates/:id/edit" element={<TemplateEditor />} />
<Route path="/projects" element={<Projects />} />
<Route path="/projects/:id" element={<ProjectDetail />} />
<Route path="/anomalies" element={<Anomalies />} />
```

Wrap with `<Suspense fallback={<div>加载中...</div>}>` if not already present.

- [ ] **Step 2: Update AppLayout sidebar**

In `中台/web/src/components/AppLayout.tsx`, add new menu items to the sidebar navigation. Find the menu items array and add these entries:

```tsx
import { ExperimentOutlined, AppstoreOutlined, WarningOutlined } from '@ant-design/icons';
```

Add menu items (after existing R&D Tasks item):

```tsx
{ key: '/templates', icon: <ExperimentOutlined />, label: '模板管理' },
{ key: '/projects', icon: <AppstoreOutlined />, label: '研发项目' },
{ key: '/anomalies', icon: <WarningOutlined />, label: '异常中心' },
```

- [ ] **Step 3: Commit**

```bash
git add 中台/web/src/App.tsx 中台/web/src/components/AppLayout.tsx
git commit -m "feat: add routes and sidebar navigation for workshop pages"
```

---

## Task 3: Templates Page — list + create/edit

**Files:**
- Create: `中台/web/src/pages/Templates.tsx`
- Create: `中台/web/src/pages/TemplateEditor.tsx`

- [ ] **Step 1: Create Templates list page**

Create `中台/web/src/pages/Templates.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Table, Modal, message, Tag, Space } from 'antd';
import { PlusOutlined, CopyOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { listTemplates, deleteTemplate, cloneTemplate, type PipelineTemplate } from '../api/templates';

export default function Templates() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch {
      message.error('加载模板失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTemplates(); }, []);

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后不可恢复，确定要删除此模板吗？',
      onOk: async () => {
        try {
          await deleteTemplate(id);
          message.success('删除成功');
          fetchTemplates();
        } catch (e: any) {
          const status = e?.response?.status;
          if (status === 409) {
            message.warning('该模板仍有活跃项目引用，无法删除');
          } else {
            message.error('删除失败');
          }
        }
      },
    });
  };

  const handleClone = async (id: number) => {
    try {
      await cloneTemplate(id);
      message.success('复制成功');
      fetchTemplates();
    } catch {
      message.error('复制失败');
    }
  };

  const columns = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: PipelineTemplate) => (
        <a onClick={() => navigate(`/templates/${record.id}/edit`)}>{name}</a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '阶段数',
      key: 'stages',
      render: (_: unknown, record: PipelineTemplate) => {
        try {
          return <Tag color="blue">{JSON.parse(record.stages).length} 个阶段</Tag>;
        } catch {
          return <Tag>0</Tag>;
        }
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: PipelineTemplate) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => navigate(`/templates/${record.id}/edit`)} />
          <Button type="link" icon={<CopyOutlined />} onClick={() => handleClone(record.id)} />
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>流水线模板</h2>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/templates/new')}>
            新建模板
          </Button>
        </div>
        <Table
          dataSource={templates}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </GlassCard>
    </div>
  );
}
```

- [ ] **Step 2: Create Template Editor page**

Create `中台/web/src/pages/TemplateEditor.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Button, Form, Input, InputNumber, Card, Space, message,
  Select, Divider, Empty, Typography,
} from 'antd';
import { PlusOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined, SaveOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import {
  getTemplate, createTemplate, updateTemplate,
  type StageDef, type PipelineTemplate,
} from '../api/templates';

const { TextArea } = Input;
const { Text } = Typography;

const DEFAULT_STAGE: StageDef = {
  name: '',
  description: '',
  default_assignees: [],
  deliverables: [],
  timeout_days: 3,
  reminder_policy: {
    first_delay_hours: 24,
    interval_hours: 12,
    escalation_delay_hours: 24,
    max_retries: 3,
  },
  notify_target: { type: 'next_stage_assignee' },
};

export default function TemplateEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [stages, setStages] = useState<StageDef[]>([{ ...DEFAULT_STAGE, name: '阶段 1' }]);
  const [selectedStage, setSelectedStage] = useState(0);
  const [loading, setLoading] = useState(false);
  const isEdit = !!id;

  useEffect(() => {
    if (id) {
      setLoading(true);
      getTemplate(Number(id))
        .then((data) => {
          const t = data;
          form.setFieldsValue({ name: t.name, description: t.description });
          try {
            const parsed = JSON.parse(t.stages);
            if (parsed.length > 0) setStages(parsed);
          } catch { /* keep default */ }
        })
        .catch(() => message.error('加载模板失败'))
        .finally(() => setLoading(false));
    }
  }, [id, form]);

  const addStage = () => {
    if (stages.length >= 20) { message.warning('最多 20 个阶段'); return; }
    const newStages = [...stages, { ...DEFAULT_STAGE, name: `阶段 ${stages.length + 1}` }];
    setStages(newStages);
    setSelectedStage(newStages.length - 1);
  };

  const removeStage = (index: number) => {
    if (stages.length <= 1) return;
    const newStages = stages.filter((_, i) => i !== index);
    setStages(newStages);
    setSelectedStage(Math.min(selectedStage, newStages.length - 1));
  };

  const moveStage = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= stages.length) return;
    const newStages = [...stages];
    [newStages[index], newStages[target]] = [newStages[target], newStages[index]];
    setStages(newStages);
    setSelectedStage(target);
  };

  const updateStage = (index: number, updates: Partial<StageDef>) => {
    const newStages = [...stages];
    newStages[index] = { ...newStages[index], ...updates };
    setStages(newStages);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const data = { ...values, stages };
      if (isEdit) {
        await updateTemplate(Number(id), data);
        message.success('更新成功');
      } else {
        await createTemplate(data);
        message.success('创建成功');
      }
      navigate('/templates');
    } catch {
      message.error('保存失败');
    }
  };

  const stage = stages[selectedStage];

  return (
    <div style={{ padding: 24 }}>
      <GlassCard loading={loading}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>{isEdit ? '编辑模板' : '新建模板'}</h2>
          <Space>
            <Button onClick={() => navigate('/templates')}>取消</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>保存</Button>
          </Space>
        </div>

        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input placeholder="例：标准写真研发流程" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="可选描述" />
          </Form.Item>
        </Form>

        <Divider>阶段配置（{stages.length}/20）</Divider>

        <div style={{ display: 'flex', gap: 16 }}>
          {/* Stage list */}
          <div style={{ width: 240, flexShrink: 0 }}>
            {stages.map((s, i) => (
              <Card
                key={i}
                size="small"
                hoverable
                style={{
                  marginBottom: 8,
                  border: selectedStage === i ? '2px solid #1890ff' : undefined,
                  cursor: 'pointer',
                }}
                onClick={() => setSelectedStage(i)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text strong>{s.name || `阶段 ${i + 1}`}</Text>
                  <Space size={4}>
                    <Button size="small" type="text" icon={<ArrowUpOutlined />}
                      onClick={(e) => { e.stopPropagation(); moveStage(i, -1); }} disabled={i === 0} />
                    <Button size="small" type="text" icon={<ArrowDownOutlined />}
                      onClick={(e) => { e.stopPropagation(); moveStage(i, 1); }} disabled={i === stages.length - 1} />
                    <Button size="small" type="text" danger icon={<DeleteOutlined />}
                      onClick={(e) => { e.stopPropagation(); removeStage(i); }} disabled={stages.length <= 1} />
                  </Space>
                </div>
              </Card>
            ))}
            <Button block type="dashed" icon={<PlusOutlined />} onClick={addStage}>添加阶段</Button>
          </div>

          {/* Stage config */}
          <div style={{ flex: 1 }}>
            {stage ? (
              <Card title={`阶段 ${selectedStage + 1}：${stage.name || '未命名'}`}>
                <Form layout="vertical">
                  <Form.Item label="阶段名称" required>
                    <Input value={stage.name} onChange={(e) => updateStage(selectedStage, { name: e.target.value })} />
                  </Form.Item>
                  <Form.Item label="描述">
                    <Input value={stage.description} onChange={(e) => updateStage(selectedStage, { description: e.target.value })} />
                  </Form.Item>
                  <Form.Item label="超时天数">
                    <InputNumber min={1} value={stage.timeout_days}
                      onChange={(v) => updateStage(selectedStage, { timeout_days: v ?? 3 })} />
                  </Form.Item>
                  <Form.Item label="通知目标">
                    <Select
                      value={stage.notify_target?.type || 'next_stage_assignee'}
                      onChange={(v) => updateStage(selectedStage, { notify_target: { type: v } })}
                      options={[
                        { label: '下一阶段负责人', value: 'next_stage_assignee' },
                        { label: '管理员', value: 'manager' },
                        { label: '指定群组', value: 'specific_group' },
                      ]}
                    />
                  </Form.Item>
                </Form>
              </Card>
            ) : (
              <Empty description="请选择一个阶段" />
            )}
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add 中台/web/src/pages/Templates.tsx 中台/web/src/pages/TemplateEditor.tsx
git commit -m "feat: add Templates list page and Template editor with stage management"
```

---

## Task 4: Projects List Page

**Files:**
- Create: `中台/web/src/pages/Projects.tsx`

- [ ] **Step 1: Create Projects list page**

Create `中台/web/src/pages/Projects.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Tag, Row, Col, Modal, Form, Select, Input, message, Statistic, Space } from 'antd';
import { PlusOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import {
  listProjects, createProject, startProject, patchProjectStatus, deleteProject,
  type RDProject,
} from '../api/projects';
import { listTemplates, type PipelineTemplate } from '../api/templates';

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  active: 'processing',
  paused: 'warning',
  completed: 'success',
};

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  active: '进行中',
  paused: '已暂停',
  completed: '已完成',
};

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<RDProject[]>([]);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm] = Form.useForm();

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const data = await listProjects();
      setProjects(data);
    } catch {
      message.error('加载项目失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchProjects(); fetchTemplates(); }, []);

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      await createProject(values);
      message.success('创建成功');
      setShowCreate(false);
      createForm.resetFields();
      fetchProjects();
    } catch {
      message.error('创建失败');
    }
  };

  const handleStart = async (id: number) => {
    try {
      await startProject(id);
      message.success('项目已启动');
      fetchProjects();
    } catch {
      message.error('启动失败');
    }
  };

  const handlePause = async (id: number) => {
    try {
      await patchProjectStatus(id, 'paused');
      message.success('项目已暂停');
      fetchProjects();
    } catch {
      message.error('操作失败');
    }
  };

  const handleResume = async (id: number) => {
    try {
      await patchProjectStatus(id, 'active');
      message.success('项目已恢复');
      fetchProjects();
    } catch {
      message.error('操作失败');
    }
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后不可恢复，确定要删除此项目吗？',
      onOk: async () => {
        try {
          await deleteProject(id);
          message.success('删除成功');
          fetchProjects();
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const stats = {
    active: projects.filter(p => p.status === 'active').length,
    completed: projects.filter(p => p.status === 'completed').length,
    draft: projects.filter(p => p.status === 'draft').length,
  };

  return (
    <div style={{ padding: 24 }}>
      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>研发项目</h2>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowCreate(true)}>
            新建项目
          </Button>
        </div>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}><Statistic title="进行中" value={stats.active} valueStyle={{ color: '#1890ff' }} /></Col>
          <Col span={8}><Statistic title="已完成" value={stats.completed} valueStyle={{ color: '#52c41a' }} /></Col>
          <Col span={8}><Statistic title="草稿" value={stats.draft} valueStyle={{ color: '#999' }} /></Col>
        </Row>

        <Row gutter={[16, 16]}>
          {projects.map(p => (
            <Col xs={24} sm={12} md={8} key={p.id}>
              <Card
                hoverable
                onClick={() => navigate(`/projects/${p.id}`)}
                style={{ borderLeft: `4px solid ${
                  p.status === 'active' ? '#1890ff' :
                  p.status === 'completed' ? '#52c41a' :
                  p.status === 'paused' ? '#faad14' : '#d9d9d9'
                }` }}
              >
                <Card.Meta
                  title={<div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{p.name}</span>
                    <Tag color={STATUS_COLORS[p.status]}>{STATUS_LABELS[p.status]}</Tag>
                  </div>}
                  description={p.description || '无描述'}
                />
                <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                  {p.status === 'draft' && (
                    <Button size="small" type="primary" icon={<PlayCircleOutlined />}
                      onClick={(e) => { e.stopPropagation(); handleStart(p.id); }}>启动</Button>
                  )}
                  {p.status === 'active' && (
                    <Button size="small" icon={<PauseCircleOutlined />}
                      onClick={(e) => { e.stopPropagation(); handlePause(p.id); }}>暂停</Button>
                  )}
                  {p.status === 'paused' && (
                    <Button size="small" type="primary" icon={<PlayCircleOutlined />}
                      onClick={(e) => { e.stopPropagation(); handleResume(p.id); }}>恢复</Button>
                  )}
                  {p.status !== 'completed' && (
                    <Button size="small" danger onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}>删除</Button>
                  )}
                </div>
              </Card>
            </Col>
          ))}
        </Row>

        {projects.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
            暂无项目，点击"新建项目"开始
          </div>
        )}
      </GlassCard>

      <Modal title="新建项目" open={showCreate} onOk={handleCreate} onCancel={() => setShowCreate(false)}>
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input placeholder="例：春季写真研发" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="template_id" label="选择模板" rules={[{ required: true }]}>
            <Select placeholder="选择流水线模板">
              {templates.map(t => (
                <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add 中台/web/src/pages/Projects.tsx
git commit -m "feat: add Projects list page with create, start, pause, delete"
```

---

## Task 5: Project Detail Page — workshop view + timeline + deliverables

**Files:**
- Create: `中台/web/src/pages/ProjectDetail.tsx`
- Create: `中台/web/src/pages/ProjectTimeline.tsx`

- [ ] **Step 1: Create Project Detail page**

Create `中台/web/src/pages/ProjectDetail.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, Button, Tag, Spin, message, Descriptions, Space } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { getProject, startProject, advanceProject, reworkStage, type RDProject, type SubTask } from '../api/projects';
import ProjectTimeline from './ProjectTimeline';
import WorkshopScene from '../components/workshop/WorkshopScene';

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿', active: '进行中', paused: '已暂停', completed: '已完成',
  pending: '待开始', dispatched: '已派发', completed: '已完成', rework: '返工中', blocked: '已阻塞',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', active: 'processing', paused: 'warning', completed: 'success',
  pending: 'default', dispatched: 'processing', rework: 'error', blocked: 'warning',
};

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<RDProject | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProject = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await getProject(Number(id));
      setProject(data);
    } catch {
      message.error('加载项目失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProject(); }, [id]);

  const handleStart = async () => {
    if (!id) return;
    try {
      await startProject(Number(id));
      message.success('项目已启动');
      fetchProject();
    } catch {
      message.error('启动失败');
    }
  };

  const handleAdvance = async (stageIndex: number) => {
    if (!id) return;
    try {
      await advanceProject(Number(id), stageIndex);
      message.success('阶段已推进');
      fetchProject();
    } catch {
      message.error('推进失败');
    }
  };

  const handleRework = async (stageIndex: number) => {
    if (!id) return;
    try {
      await reworkStage(Number(id), stageIndex, '质量不达标');
      message.success('已标记返工');
      fetchProject();
    } catch {
      message.error('操作失败');
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>;
  if (!project) return <div>项目不存在</div>;

  const stages = project.sub_tasks || [];

  return (
    <div style={{ padding: 24 }}>
      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/projects')}>返回</Button>
            <h2 style={{ margin: 0 }}>{project.name}</h2>
            <Tag color={STATUS_COLORS[project.status]}>{STATUS_LABELS[project.status]}</Tag>
          </Space>
          {project.status === 'draft' && (
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleStart}>启动项目</Button>
          )}
        </div>

        <Descriptions size="small" column={3} style={{ marginBottom: 16 }}>
          <Descriptions.Item label="模板ID">{project.template_id}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {project.created_at ? new Date(project.created_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="总阶段数">{stages.length}</Descriptions.Item>
        </Descriptions>

        <Tabs defaultActiveKey="workshop" items={[
          {
            key: 'workshop',
            label: '工作坊视图',
            children: (
              <WorkshopScene
                project={project}
                stages={stages}
                onAdvance={handleAdvance}
                onRework={handleRework}
              />
            ),
          },
          {
            key: 'timeline',
            label: '时间线',
            children: <ProjectTimeline stages={stages} onAdvance={handleAdvance} onRework={handleRework} />,
          },
          {
            key: 'stages',
            label: '阶段详情',
            children: (
              <div>
                {stages.map((s: SubTask) => (
                  <div key={s.id} style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid rgba(255,255,255,0.1)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}>
                    <div>
                      <Space>
                        <Tag color={STATUS_COLORS[s.status]}>{STATUS_LABELS[s.status] || s.status}</Tag>
                        <strong>{s.stage_name}</strong>
                        <span style={{ color: '#999' }}>阶段 {s.stage_index + 1}</span>
                      </Space>
                    </div>
                    <Space>
                      {s.status === 'dispatched' && (
                        <>
                          <Button size="small" type="primary"
                            onClick={() => handleAdvance(s.stage_index)}>完成</Button>
                          <Button size="small" danger
                            onClick={() => handleRework(s.stage_index)}>返工</Button>
                        </>
                      )}
                    </Space>
                  </div>
                ))}
              </div>
            ),
          },
        ]} />
      </GlassCard>
    </div>
  );
}
```

- [ ] **Step 2: Create Project Timeline component**

Create `中台/web/src/pages/ProjectTimeline.tsx`:

```tsx
import { Tag, Button, Space } from 'antd';
import type { SubTask } from '../api/projects';

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', dispatched: 'processing', completed: 'success',
  rework: 'error', blocked: 'warning',
};

const STATUS_LABELS: Record<string, string> = {
  pending: '待开始', dispatched: '已派发', completed: '已完成', rework: '返工中', blocked: '已阻塞',
};

interface Props {
  stages: SubTask[];
  onAdvance: (stageIndex: number) => void;
  onRework: (stageIndex: number) => void;
}

export default function ProjectTimeline({ stages, onAdvance, onRework }: Props) {
  return (
    <div style={{ position: 'relative', paddingLeft: 24 }}>
      {stages.map((s, i) => (
        <div key={s.id} style={{ position: 'relative', paddingBottom: 24 }}>
          {/* Vertical line */}
          {i < stages.length - 1 && (
            <div style={{
              position: 'absolute', left: 7, top: 24, bottom: 0, width: 2,
              background: s.status === 'completed' ? '#52c41a' : 'rgba(255,255,255,0.2)',
            }} />
          )}
          {/* Dot */}
          <div style={{
            position: 'absolute', left: 0, top: 6,
            width: 16, height: 16, borderRadius: '50%',
            background: s.status === 'completed' ? '#52c41a' :
              s.status === 'dispatched' ? '#1890ff' :
              s.status === 'rework' ? '#ff4d4f' : '#666',
          }} />
          {/* Content */}
          <div style={{ marginLeft: 28 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <strong>{s.stage_name}</strong>
                <Tag color={STATUS_COLORS[s.status]}>{STATUS_LABELS[s.status] || s.status}</Tag>
              </Space>
              {s.status === 'dispatched' && (
                <Space>
                  <Button size="small" type="primary" onClick={() => onAdvance(s.stage_index)}>完成</Button>
                  <Button size="small" danger onClick={() => onRework(s.stage_index)}>返工</Button>
                </Space>
              )}
            </div>
            <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
              {s.description && <span>{s.description} · </span>}
              {s.deadline && <span>截止 {new Date(s.deadline).toLocaleDateString('zh-CN')}</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add 中台/web/src/pages/ProjectDetail.tsx 中台/web/src/pages/ProjectTimeline.tsx
git commit -m "feat: add Project Detail page with workshop view, timeline, and stage details tabs"
```

---

## Task 6: Workshop 2D Scene — SVG visualization

**Files:**
- Create: `中台/web/src/components/workshop/WorkshopScene.tsx`
- Create: `中台/web/src/components/workshop/Workstation.tsx`
- Create: `中台/web/src/components/workshop/WorkshopStatusIcon.tsx`
- Create: `中台/web/src/components/workshop/workshop.css`

This is the core visual component — a pixel-art SVG workshop scene showing workstations, characters, and status.

- [ ] **Step 1: Create workshop CSS styles and animations**

Create `中台/web/src/components/workshop/workshop.css`:

```css
/* Workshop Scene Styles */
.workshop-scene {
  image-rendering: pixelated;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
}

/* Workstation animations */
@keyframes pulse-blue {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

@keyframes flash-red {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@keyframes flash-orange {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}

@keyframes walk {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(2px) translateY(-1px); }
  75% { transform: translateX(-2px) translateY(-1px); }
}

@keyframes breathing {
  0%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.95); }
}

@keyframes wave-flag {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(15deg); }
  75% { transform: rotate(-15deg); }
}

@keyframes bobble {
  0%, 100% { transform: translateY(0) scaleY(1); }
  50% { transform: translateY(-2px) scaleY(0.98); }
}

.status-active {
  animation: pulse-blue 2s ease-in-out infinite;
}

.status-rework {
  animation: flash-orange 1s ease-in-out infinite;
}

.status-blocked {
  animation: flash-red 1s ease-in-out infinite;
}

.character-working {
  animation: bobble 1.5s ease-in-out infinite;
}

.character-idle {
  animation: breathing 3s ease-in-out infinite;
}

.character-walking {
  animation: walk 0.5s ease-in-out infinite;
}

.character-celebrating {
  animation: wave-flag 0.8s ease-in-out infinite;
}

/* Workstation hover effect */
.workstation-group {
  cursor: pointer;
  transition: filter 0.2s;
}

.workstation-group:hover {
  filter: brightness(1.2);
}

/* Stage label */
.stage-label {
  font-family: monospace;
  font-size: 10px;
  fill: #fff;
  text-anchor: middle;
}

/* Tooltip */
.workshop-tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.85);
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  pointer-events: none;
  z-index: 100;
  max-width: 200px;
}
```

- [ ] **Step 2: Create Workstation component**

Create `中台/web/src/components/workshop/Workstation.tsx`:

```tsx
import WorkshopStatusIcon from './WorkshopStatusIcon';

interface Props {
  x: number;
  y: number;
  label: string;
  status: string;
  onClick?: () => void;
}

const WORKSTATION_COLORS: Record<string, string> = {
  pending: '#555',
  dispatched: '#1890ff',
  completed: '#52c41a',
  rework: '#fa8c16',
  blocked: '#ff4d4f',
};

export default function Workstation({ x, y, label, status, onClick }: Props) {
  const color = WORKSTATION_COLORS[status] || '#555';
  const isActive = status === 'dispatched';
  const isCompleted = status === 'completed';
  const isAnomaly = status === 'rework' || status === 'blocked';

  return (
    <g className="workstation-group" onClick={onClick}>
      {/* Workstation desk */}
      <rect x={x - 50} y={y} width={100} height={40} rx={4}
        fill={color} opacity={0.3} stroke={color} strokeWidth={1.5} />
      {/* Desktop surface */}
      <rect x={x - 45} y={y + 4} width={90} height={6} rx={2} fill={color} opacity={0.6} />

      {/* Status icon */}
      <WorkshopStatusIcon
        x={x}
        y={y - 10}
        status={status}
        active={isActive}
        anomaly={isAnomaly}
        completed={isCompleted}
      />

      {/* Label */}
      <text x={x} y={y + 30} className="stage-label">{label}</text>
    </g>
  );
}
```

- [ ] **Step 3: Create WorkshopStatusIcon component**

Create `中台/web/src/components/workshop/WorkshopStatusIcon.tsx`:

```tsx
interface Props {
  x: number;
  y: number;
  status: string;
  active?: boolean;
  anomaly?: boolean;
  completed?: boolean;
}

export default function WorkshopStatusIcon({ x, y, status, active, anomaly, completed }: Props) {
  if (completed) {
    return (
      <g className="character-celebrating">
        {/* Green checkmark */}
        <circle cx={x} cy={y} r={8} fill="#52c41a" />
        <path d={`M${x - 4},${y} L${x - 1},${y + 3} L${x + 5},${y - 4}`}
          stroke="#fff" strokeWidth={2} fill="none" />
      </g>
    );
  }

  if (anomaly) {
    const cls = status === 'rework' ? 'status-rework' : 'status-blocked';
    return (
      <g className={cls}>
        {/* Warning triangle */}
        <polygon points={`${x},${y - 8} ${x - 7},${y + 5} ${x + 7},${y + 5}`}
          fill={status === 'rework' ? '#fa8c16' : '#ff4d4f'} />
        <text x={x} y={y + 3} textAnchor="middle" fill="#fff" fontSize={8} fontWeight="bold">!</text>
      </g>
    );
  }

  if (active) {
    return (
      <g className="status-active">
        {/* Blue pulse dot */}
        <circle cx={x} cy={y} r={6} fill="#1890ff" />
        <circle cx={x} cy={y} r={10} fill="none" stroke="#1890ff" strokeWidth={1} opacity={0.4} />
      </g>
    );
  }

  // Pending — gray dot
  return (
    <g>
      <circle cx={x} cy={y} r={5} fill="#555" />
    </g>
  );
}
```

- [ ] **Step 4: Create WorkshopScene main component**

Create `中台/web/src/components/workshop/WorkshopScene.tsx`:

```tsx
import { useState } from 'react';
import { Button, Tag, Space, Tooltip } from 'antd';
import Workstation from './Workstation';
import type { RDProject, SubTask } from '../../api/projects';
import './workshop.css';

const STATUS_LABELS: Record<string, string> = {
  pending: '待开始', dispatched: '进行中', completed: '已完成', rework: '返工中', blocked: '已阻塞',
};

interface Props {
  project: RDProject;
  stages: SubTask[];
  onAdvance: (stageIndex: number) => void;
  onRework: (stageIndex: number) => void;
}

export default function WorkshopScene({ project, stages, onAdvance, onRework }: Props) {
  const [hoveredStage, setHoveredStage] = useState<number | null>(null);

  const SCENE_WIDTH = 800;
  const SCENE_HEIGHT = 400;
  const STATION_Y = 120;
  const STATION_SPACING = Math.min(160, (SCENE_WIDTH - 100) / Math.max(stages.length, 1));
  const startX = (SCENE_WIDTH - STATION_SPACING * (stages.length - 1)) / 2;

  // Rest area for pending characters
  const restAreaY = SCENE_HEIGHT - 80;

  return (
    <div>
      <svg
        viewBox={`0 0 ${SCENE_WIDTH} ${SCENE_HEIGHT}`}
        className="workshop-scene"
        style={{ width: '100%', maxWidth: 900, borderRadius: 12 }}
      >
        {/* Background decorations */}
        <defs>
          <radialGradient id="spotlight" cx="50%" cy="30%" r="60%">
            <stop offset="0%" stopColor="rgba(24,144,255,0.08)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width={SCENE_WIDTH} height={SCENE_HEIGHT} fill="url(#spotlight)" />
        <rect width={SCENE_WIDTH} height={SCENE_HEIGHT} fill="url(#grid)" />

        {/* Title banner */}
        <text x={SCENE_WIDTH / 2} y={30} textAnchor="middle" fill="rgba(255,255,255,0.6)"
          fontSize={14} fontFamily="monospace">
          工作坊：{project.name}
        </text>

        {/* Pipeline connection line */}
        {stages.length > 1 && (
          <line
            x1={startX} y1={STATION_Y + 20}
            x2={startX + STATION_SPACING * (stages.length - 1)} y2={STATION_Y + 20}
            stroke="rgba(255,255,255,0.15)" strokeWidth={2} strokeDasharray="4 4"
          />
        )}

        {/* Workstations */}
        {stages.map((s, i) => (
          <g key={s.id}
            onMouseEnter={() => setHoveredStage(i)}
            onMouseLeave={() => setHoveredStage(null)}
          >
            <Workstation
              x={startX + STATION_SPACING * i}
              y={STATION_Y}
              label={s.stage_name || `阶段${i + 1}`}
              status={s.status}
            />

            {/* Progress number */}
            <text
              x={startX + STATION_SPACING * i}
              y={STATION_Y - 24}
              textAnchor="middle"
              fill="rgba(255,255,255,0.4)"
              fontSize={9}
              fontFamily="monospace"
            >
              #{i + 1}
            </text>

            {/* Character avatar (simple) */}
            {s.status === 'dispatched' ? (
              <g className="character-working">
                <circle cx={startX + STATION_SPACING * i} cy={STATION_Y + 55}
                  r={12} fill="#1890ff" opacity={0.8} />
                <text x={startX + STATION_SPACING * i} y={STATION_Y + 59}
                  textAnchor="middle" fill="#fff" fontSize={10}>
                  {(s.stage_name || '?')[0]}
                </text>
              </g>
            ) : s.status === 'completed' ? (
              <g className="character-celebrating">
                <circle cx={startX + STATION_SPACING * i} cy={STATION_Y + 55}
                  r={12} fill="#52c41a" opacity={0.8} />
                <text x={startX + STATION_SPACING * i} y={STATION_Y + 59}
                  textAnchor="middle" fill="#fff" fontSize={10}>
                  {(s.stage_name || '?')[0]}
                </text>
              </g>
            ) : s.status === 'rework' ? (
              <g className="status-rework">
                <circle cx={startX + STATION_SPACING * i} cy={STATION_Y + 55}
                  r={12} fill="#fa8c16" opacity={0.8} />
                <text x={startX + STATION_SPACING * i} y={STATION_Y + 59}
                  textAnchor="middle" fill="#fff" fontSize={10}>
                  {(s.stage_name || '?')[0]}
                </text>
              </g>
            ) : null}

            {/* Hover tooltip */}
            {hoveredStage === i && (
              <g>
                <rect
                  x={startX + STATION_SPACING * i - 70} y={STATION_Y + 72}
                  width={140} height={28} rx={4}
                  fill="rgba(0,0,0,0.8)" />
                <text
                  x={startX + STATION_SPACING * i} y={STATION_Y + 90}
                  textAnchor="middle" fill="#fff" fontSize={10} fontFamily="monospace">
                  {s.stage_name} · {STATUS_LABELS[s.status] || s.status}
                </text>
              </g>
            )}
          </g>
        ))}

        {/* Rest area for pending */}
        {stages.filter(s => s.status === 'pending').length > 0 && (
          <g>
            <text x={SCENE_WIDTH / 2} y={restAreaY - 8} textAnchor="middle"
              fill="rgba(255,255,255,0.3)" fontSize={10} fontFamily="monospace">
              休息区
            </text>
            <rect x={SCENE_WIDTH / 2 - 100} y={restAreaY} width={200} height={40}
              rx={8} fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)" />
            {stages.filter(s => s.status === 'pending').map((s, i) => (
              <g key={s.id} className="character-idle">
                <circle cx={SCENE_WIDTH / 2 - 60 + i * 40} cy={restAreaY + 20}
                  r={10} fill="#666" opacity={0.5} />
                <text x={SCENE_WIDTH / 2 - 60 + i * 40} y={restAreaY + 24}
                  textAnchor="middle" fill="#fff" fontSize={8}>
                  {(s.stage_name || '?')[0]}
                </text>
              </g>
            ))}
          </g>
        )}

        {/* Project status badge */}
        <g>
          <rect x={SCENE_WIDTH - 110} y={8} width={100} height={24} rx={12}
            fill={project.status === 'active' ? 'rgba(24,144,255,0.3)' :
              project.status === 'completed' ? 'rgba(82,196,26,0.3)' :
              'rgba(255,255,255,0.1)'} />
          <text x={SCENE_WIDTH - 60} y={24} textAnchor="middle" fill="#fff" fontSize={10}>
            {STATUS_LABELS[project.status] || project.status}
          </text>
        </g>
      </svg>

      {/* Action buttons below the scene */}
      <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {stages.filter(s => s.status === 'dispatched').map(s => (
          <Space key={s.id}>
            <Tag color="processing">{s.stage_name}</Tag>
            <Button size="small" type="primary" onClick={() => onAdvance(s.stage_index)}>
              完成
            </Button>
            <Button size="small" danger onClick={() => onRework(s.stage_index)}>
              返工
            </Button>
          </Space>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add 中台/web/src/components/workshop/
git commit -m "feat: add Workshop 2D scene with SVG workstations, status icons, and CSS animations"
```

---

## Task 7: Anomalies Center Page

**Files:**
- Create: `中台/web/src/pages/Anomalies.tsx`

- [ ] **Step 1: Create Anomalies page**

Create `中台/web/src/pages/Anomalies.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Tag, Button, Select, Space, message, Empty, Row, Col, Badge } from 'antd';
import {
  CheckCircleOutlined, RightCircleOutlined, StopOutlined,
  SwapOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { listAnomalies, resolveAnomaly, type Anomaly } from '../api/anomalies';

const SEVERITY_CONFIG: Record<string, { color: string; label: string; bg: string }> = {
  critical: { color: '#ff4d4f', label: '严重', bg: 'rgba(255,77,79,0.1)' },
  high: { color: '#fa8c16', label: '高', bg: 'rgba(250,140,22,0.1)' },
  medium: { color: '#faad14', label: '中', bg: 'rgba(250,173,20,0.1)' },
  low: { color: '#1890ff', label: '低', bg: 'rgba(24,144,255,0.1)' },
};

const TYPE_LABELS: Record<string, string> = {
  rework: '返工',
  blocked: '阻塞',
  overdue_escalation: '超时升级',
};

const RESOLVE_ACTIONS = [
  { key: 'resume', label: '恢复', icon: <RightCircleOutlined />, color: '#1890ff' },
  { key: 'dismiss', label: '忽略', icon: <CheckCircleOutlined />, color: '#52c41a' },
  { key: 'skip', label: '跳过', icon: <StopOutlined />, color: '#faad14' },
  { key: 'reassign', label: '转派', icon: <SwapOutlined />, color: '#722ed1' },
];

export default function Anomalies() {
  const navigate = useNavigate();
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string | undefined>();

  const fetchAnomalies = async () => {
    setLoading(true);
    try {
      const data = await listAnomalies(filterSeverity ? { severity: filterSeverity } : undefined);
      setAnomalies(data);
    } catch {
      message.error('加载异常列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAnomalies(); }, [filterSeverity]);

  const handleResolve = async (id: number, action: string) => {
    try {
      await resolveAnomaly(id, action);
      message.success('处理成功');
      fetchAnomalies();
    } catch {
      message.error('处理失败');
    }
  };

  // Sort by severity
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const sorted = [...anomalies].sort((a, b) =>
    (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
  );

  const counts = {
    critical: anomalies.filter(a => a.severity === 'critical').length,
    high: anomalies.filter(a => a.severity === 'high').length,
    medium: anomalies.filter(a => a.severity === 'medium').length,
  };

  return (
    <div style={{ padding: 24 }}>
      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>异常中心</h2>
          <Select
            placeholder="筛选严重程度"
            allowClear
            style={{ width: 160 }}
            value={filterSeverity}
            onChange={setFilterSeverity}
            options={[
              { label: '全部', value: undefined },
              { label: '严重', value: 'critical' },
              { label: '高', value: 'high' },
              { label: '中', value: 'medium' },
            ]}
          />
        </div>

        {/* Severity summary */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          {Object.entries(counts).map(([key, count]) => {
            const cfg = SEVERITY_CONFIG[key];
            return (
              <Col span={8} key={key}>
                <Card size="small" style={{ background: cfg.bg, borderColor: cfg.color }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: cfg.color, fontWeight: 'bold' }}>{cfg.label}</span>
                    <Badge count={count} style={{ backgroundColor: cfg.color }} />
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>

        {sorted.length === 0 && !loading ? (
          <Empty description="暂无异常，一切正常" />
        ) : (
          <div>
            {sorted.map(anomaly => {
              const sev = SEVERITY_CONFIG[anomaly.severity] || SEVERITY_CONFIG.medium;
              return (
                <Card
                  key={anomaly.id}
                  size="small"
                  style={{
                    marginBottom: 12,
                    borderLeft: `4px solid ${sev.color}`,
                    background: sev.bg,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <Space>
                        <ExclamationCircleOutlined style={{ color: sev.color }} />
                        <Tag color={sev.color}>{sev.label}</Tag>
                        <Tag>{TYPE_LABELS[anomaly.type] || anomaly.type}</Tag>
                        <strong>{anomaly.stage_name}</strong>
                      </Space>
                      <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                        {anomaly.project_name && (
                          <a onClick={() => navigate(`/projects/${anomaly.project_id}`)}>
                            项目：{anomaly.project_name}
                          </a>
                        )}
                        {anomaly.assignees.length > 0 && (
                          <span> · 负责人：{anomaly.assignees.join(', ')}</span>
                        )}
                      </div>
                    </div>
                    <Space>
                      {RESOLVE_ACTIONS.map(act => (
                        <Button key={act.key} size="small"
                          onClick={() => handleResolve(anomaly.id, act.key)}>
                          {act.icon} {act.label}
                        </Button>
                      ))}
                    </Space>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add 中台/web/src/pages/Anomalies.tsx
git commit -m "feat: add Anomalies center page with severity sorting and resolve actions"
```

---

## Task 8: Dashboard Redesign — workshop scene as homepage

**Files:**
- Modify: `中台/web/src/pages/Dashboard.tsx`

- [ ] **Step 1: Rewrite Dashboard with workshop overview**

Replace the content of `中台/web/src/pages/Dashboard.tsx` with a workshop-themed dashboard that shows active project workshop scenes:

```tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Row, Col, Card, Statistic, Spin, message, Tag, Empty } from 'antd';
import {
  AppstoreOutlined, CheckCircleOutlined, WarningOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { listProjects, type RDProject } from '../api/projects';
import { listAnomalies } from '../api/anomalies';
import { listTemplates } from '../api/templates';

export default function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<RDProject[]>([]);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [templateCount, setTemplateCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      listProjects(),
      listAnomalies(),
      listTemplates(),
    ]).then(([projData, anomData, tmplData]) => {
      setProjects(projData);
      setAnomalyCount(anomData.length);
      setTemplateCount(tmplData.length);
    }).catch(() => {
      message.error('加载数据失败');
    }).finally(() => setLoading(false));
  }, []);

  const activeProjects = projects.filter(p => p.status === 'active');
  const completedProjects = projects.filter(p => p.status === 'completed');

  return (
    <div style={{ padding: 24 }}>
      {/* Stats bar */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <GlassCard>
            <Statistic title="进行中项目" value={activeProjects.length}
              prefix={<AppstoreOutlined />} valueStyle={{ color: '#1890ff' }} />
          </GlassCard>
        </Col>
        <Col span={6}>
          <GlassCard>
            <Statistic title="已完成项目" value={completedProjects.length}
              prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
          </GlassCard>
        </Col>
        <Col span={6}>
          <GlassCard>
            <Statistic title="当前异常" value={anomalyCount}
              prefix={<WarningOutlined />} valueStyle={{ color: anomalyCount > 0 ? '#ff4d4f' : '#999' }} />
          </GlassCard>
        </Col>
        <Col span={6}>
          <GlassCard>
            <Statistic title="流水线模板" value={templateCount}
              prefix={<ExperimentOutlined />} valueStyle={{ color: '#722ed1' }} />
          </GlassCard>
        </Col>
      </Row>

      {/* Active project thumbnails */}
      <GlassCard>
        <h3 style={{ marginBottom: 16 }}>活跃工作坊</h3>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
        ) : activeProjects.length === 0 ? (
          <Empty description="暂无活跃项目" />
        ) : (
          <Row gutter={[16, 16]}>
            {activeProjects.map(p => {
              const subTasks = p.sub_tasks || [];
              const totalStages = subTasks.length;
              const completedStages = subTasks.filter(s => s.status === 'completed').length;
              const currentStage = subTasks.find(s => s.status === 'dispatched');
              const progress = totalStages > 0 ? Math.round((completedStages / totalStages) * 100) : 0;

              return (
                <Col xs={24} sm={12} md={8} key={p.id}>
                  <Card
                    hoverable
                    onClick={() => navigate(`/projects/${p.id}`)}
                    style={{
                      background: 'linear-gradient(135deg, rgba(24,144,255,0.1), rgba(114,46,209,0.05))',
                      border: '1px solid rgba(24,144,255,0.3)',
                    }}
                  >
                    {/* Mini workshop preview */}
                    <div style={{ marginBottom: 12 }}>
                      <svg viewBox="0 0 200 40" style={{ width: '100%' }}>
                        {subTasks.map((s, i) => {
                          const x = 15 + (170 / Math.max(totalStages - 1, 1)) * i;
                          const color = s.status === 'completed' ? '#52c41a' :
                            s.status === 'dispatched' ? '#1890ff' :
                            s.status === 'rework' ? '#fa8c16' : '#555';
                          return (
                            <g key={s.id}>
                              {i < totalStages - 1 && (
                                <line x1={x} y1={20} x2={15 + (170 / Math.max(totalStages - 1, 1)) * (i + 1)} y2={20}
                                  stroke={s.status === 'completed' ? '#52c41a' : '#333'} strokeWidth={2} />
                              )}
                              <circle cx={x} cy={20} r={6} fill={color} />
                              <text x={x} y={36} textAnchor="middle" fill="#999" fontSize={6}>
                                {(s.stage_name || '').slice(0, 3)}
                              </text>
                            </g>
                          );
                        })}
                      </svg>
                    </div>

                    <Card.Meta
                      title={
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span>{p.name}</span>
                          <Tag color="processing">进行中</Tag>
                        </div>
                      }
                      description={
                        <div>
                          <div style={{ marginBottom: 4 }}>
                            当前阶段：{currentStage?.stage_name || '-'}
                          </div>
                          <div style={{
                            height: 4, borderRadius: 2,
                            background: 'rgba(255,255,255,0.1)',
                          }}>
                            <div style={{
                              height: '100%', borderRadius: 2, width: `${progress}%`,
                              background: 'linear-gradient(90deg, #1890ff, #52c41a)',
                            }} />
                          </div>
                          <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                            {completedStages}/{totalStages} 阶段 ({progress}%)
                          </div>
                        </div>
                      }
                    />
                  </Card>
                </Col>
              );
            })}
          </Row>
        )}
      </GlassCard>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add 中台/web/src/pages/Dashboard.tsx
git commit -m "feat: redesign Dashboard with workshop-themed project overview and mini pipeline previews"
```

---

## Summary of Tasks

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | API Layer (templates, projects, anomalies) | `api/templates.ts`, `api/projects.ts`, `api/anomalies.ts` |
| 2 | App Shell (routes + sidebar) | `App.tsx`, `AppLayout.tsx` |
| 3 | Templates Page (list + editor) | `pages/Templates.tsx`, `pages/TemplateEditor.tsx` |
| 4 | Projects List Page | `pages/Projects.tsx` |
| 5 | Project Detail Page (workshop + timeline) | `pages/ProjectDetail.tsx`, `pages/ProjectTimeline.tsx` |
| 6 | Workshop 2D Scene (SVG + animations) | `components/workshop/` (4 files) |
| 7 | Anomalies Center Page | `pages/Anomalies.tsx` |
| 8 | Dashboard Redesign | `pages/Dashboard.tsx` |

## Dependency Order

```
Task 1 (API layer)
  └── Task 2 (app shell — routes)
        ├── Task 3 (templates page)
        ├── Task 4 (projects list)
        ├── Task 6 (workshop scene)
        │     └── Task 5 (project detail — imports WorkshopScene)
        ├── Task 7 (anomalies center)
        └── Task 8 (dashboard redesign)
```

**Execution order: 1 → 2 → 3 → 4 → 6 → 5 → 7 → 8**

Task 6 (Workshop Scene) MUST complete before Task 5 (Project Detail) since ProjectDetail imports WorkshopScene. Tasks 3, 4, 6, 7 are mutually independent and can be parallelized after Task 2.
