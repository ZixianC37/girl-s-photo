import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Form, Input, InputNumber, Space, message,
  Select, Collapse,
} from 'antd';
import { PlusOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { createProject } from '../api/projects';

const { TextArea } = Input;

const FORMAT_OPTIONS = [
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'document', label: '文档' },
  { value: 'any', label: '任意' },
];

interface SubTaskItem {
  title: string;
  description: string;
  assignees: string[];
  deliverable_rules: { name: string; format: string; required_count: number; description?: string }[];
  reminder_config?: { first_delay_hours: number; interval_hours: number; escalation_delay_hours: number; max_retries: number };
}

const DEFAULT_SUB_TASKS: SubTaskItem[] = [
  { title: '灵感收集', description: '收集拍摄灵感和参考图', assignees: [], deliverable_rules: [{ name: '灵感板', format: 'image', required_count: 3 }] },
  { title: '风格创作', description: '根据灵感进行风格创作', assignees: [], deliverable_rules: [{ name: '风格方案', format: 'document', required_count: 1 }] },
  { title: '品鉴会', description: '全员品鉴确认方向', assignees: [], deliverable_rules: [{ name: '品鉴记录', format: 'document', required_count: 1 }] },
  { title: '服化道准备', description: '服装化妆道具准备', assignees: [], deliverable_rules: [{ name: '道具清单', format: 'document', required_count: 1 }, { name: '服装照片', format: 'image', required_count: 5 }] },
  { title: '样片拍摄', description: '执行拍摄', assignees: [], deliverable_rules: [{ name: '原始照片', format: 'image', required_count: 50 }], reminder_config: { first_delay_hours: 6, interval_hours: 4, escalation_delay_hours: 24, max_retries: 5 } },
  { title: '后期修图', description: '精修调色', assignees: [], deliverable_rules: [{ name: '精修成片', format: 'image', required_count: 20 }] },
  { title: '上新运营', description: '上架和推广', assignees: [], deliverable_rules: [{ name: '上架截图', format: 'image', required_count: 3 }] },
];

export default function ProjectCreate() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [subTasks, setSubTasks] = useState<SubTaskItem[]>(DEFAULT_SUB_TASKS.map(s => ({ ...s, deliverable_rules: [...s.deliverable_rules] })));
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [saving, setSaving] = useState(false);

  const addSubTask = () => {
    const next: SubTaskItem = { title: `子任务 ${subTasks.length + 1}`, description: '', assignees: [], deliverable_rules: [] };
    const updated = [...subTasks, next];
    setSubTasks(updated);
    setSelectedIdx(updated.length - 1);
  };

  const removeSubTask = (index: number) => {
    if (subTasks.length <= 1) return;
    const updated = subTasks.filter((_, i) => i !== index);
    setSubTasks(updated);
    setSelectedIdx(Math.min(selectedIdx, updated.length - 1));
  };

  const updateSubTask = (index: number, patch: Partial<SubTaskItem>) => {
    const updated = [...subTasks];
    updated[index] = { ...updated[index], ...patch };
    setSubTasks(updated);
  };

  const updateRule = (taskIdx: number, ruleIdx: number, patch: Partial<SubTaskItem['deliverable_rules'][0]>) => {
    const rules = [...subTasks[taskIdx].deliverable_rules];
    rules[ruleIdx] = { ...rules[ruleIdx], ...patch };
    updateSubTask(taskIdx, { deliverable_rules: rules });
  };

  const addRule = (taskIdx: number) => {
    updateSubTask(taskIdx, { deliverable_rules: [...subTasks[taskIdx].deliverable_rules, { name: '', format: 'any', required_count: 1 }] });
  };

  const removeRule = (taskIdx: number, ruleIdx: number) => {
    updateSubTask(taskIdx, { deliverable_rules: subTasks[taskIdx].deliverable_rules.filter((_, i) => i !== ruleIdx) });
  };

  const updateReminder = (taskIdx: number, patch: Partial<NonNullable<SubTaskItem['reminder_config']>>) => {
    const current = subTasks[taskIdx].reminder_config ?? { first_delay_hours: 24, interval_hours: 12, escalation_delay_hours: 24, max_retries: 3 };
    updateSubTask(taskIdx, { reminder_config: { ...current, ...patch } });
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await createProject({
        name: values.name,
        description: values.description,
        sub_tasks: subTasks,
      });
      message.success('项目创建成功');
      navigate('/projects');
    } catch {
      message.error('创建失败');
    } finally {
      setSaving(false);
    }
  };

  const task = subTasks[selectedIdx];

  return (
    <div style={{ padding: 24 }}>
      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>新建项目</h2>
          <Space>
            <Button onClick={() => navigate('/projects')}>取消</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>创建项目</Button>
          </Space>
        </div>

        <Form form={form} layout="vertical" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]} style={{ flex: 1, marginBottom: 0 }}>
              <Input placeholder="例：春季新品写真" />
            </Form.Item>
            <Form.Item name="description" label="描述" style={{ flex: 2, marginBottom: 0 }}>
              <TextArea rows={1} placeholder="可选描述" />
            </Form.Item>
          </div>
        </Form>

        <div style={{ display: 'flex', gap: 16, minHeight: 480 }}>
          {/* Left sidebar — sub-task list */}
          <div style={{ width: 280, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {subTasks.map((st, i) => (
              <div
                key={i}
                onClick={() => setSelectedIdx(i)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: selectedIdx === i ? '2px solid #1890ff' : '1px solid rgba(255,255,255,0.12)',
                  background: selectedIdx === i ? 'rgba(24,144,255,0.08)' : 'transparent',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  transition: 'border-color 0.2s, background 0.2s',
                }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  {i + 1}. {st.title}
                </span>
                <Button
                  size="small"
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  disabled={subTasks.length <= 1}
                  onClick={(e) => { e.stopPropagation(); removeSubTask(i); }}
                />
              </div>
            ))}
            <Button block type="dashed" icon={<PlusOutlined />} onClick={addSubTask}>添加子任务</Button>
          </div>

          {/* Right panel — edit form */}
          <div style={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 260px)' }}>
            {task ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', gap: 16 }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: 4, fontSize: 13, opacity: 0.85 }}>标题</label>
                    <Input
                      value={task.title}
                      onChange={e => updateSubTask(selectedIdx, { title: e.target.value })}
                      placeholder="子任务标题"
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 13, opacity: 0.85 }}>描述</label>
                  <TextArea
                    rows={2}
                    value={task.description}
                    onChange={e => updateSubTask(selectedIdx, { description: e.target.value })}
                    placeholder="子任务描述"
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: 4, fontSize: 13, opacity: 0.85 }}>负责人</label>
                  <Select
                    mode="tags"
                    value={task.assignees}
                    onChange={v => updateSubTask(selectedIdx, { assignees: v })}
                    placeholder="输入姓名后回车添加"
                    style={{ width: '100%' }}
                    open={false}
                  />
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <label style={{ fontSize: 13, opacity: 0.85 }}>成果收集规则</label>
                    <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => addRule(selectedIdx)}>添加规则</Button>
                  </div>
                  {task.deliverable_rules.length === 0 && (
                    <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12, padding: '4px 0' }}>暂无收集规则</div>
                  )}
                  {task.deliverable_rules.map((rule, ri) => (
                    <div key={ri} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                      <Input
                        placeholder="成果名称"
                        value={rule.name}
                        onChange={e => updateRule(selectedIdx, ri, { name: e.target.value })}
                        style={{ flex: 2 }}
                      />
                      <Select
                        value={rule.format}
                        onChange={v => updateRule(selectedIdx, ri, { format: v })}
                        options={FORMAT_OPTIONS}
                        style={{ width: 90 }}
                      />
                      <InputNumber
                        min={1}
                        value={rule.required_count}
                        onChange={v => v && updateRule(selectedIdx, ri, { required_count: v })}
                        style={{ width: 70 }}
                        addonAfter="份"
                      />
                      <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => removeRule(selectedIdx, ri)} />
                    </div>
                  ))}
                </div>

                <Collapse
                  ghost
                  items={[{
                    key: 'reminder',
                    label: <span style={{ fontSize: 13, opacity: 0.85 }}>定时提醒 {task.reminder_config ? '（已启用）' : '（未启用）'}</span>,
                    children: task.reminder_config ? (
                      <div style={{ display: 'flex', gap: 12 }}>
                        <div>
                          <label style={{ fontSize: 11, opacity: 0.7 }}>首次延迟(小时)</label>
                          <InputNumber min={1} value={task.reminder_config.first_delay_hours} onChange={v => v && updateReminder(selectedIdx, { first_delay_hours: v })} style={{ width: '100%' }} />
                        </div>
                        <div>
                          <label style={{ fontSize: 11, opacity: 0.7 }}>间隔(小时)</label>
                          <InputNumber min={1} value={task.reminder_config.interval_hours} onChange={v => v && updateReminder(selectedIdx, { interval_hours: v })} style={{ width: '100%' }} />
                        </div>
                        <div>
                          <label style={{ fontSize: 11, opacity: 0.7 }}>升级延迟(小时)</label>
                          <InputNumber min={1} value={task.reminder_config.escalation_delay_hours} onChange={v => v && updateReminder(selectedIdx, { escalation_delay_hours: v })} style={{ width: '100%' }} />
                        </div>
                        <div>
                          <label style={{ fontSize: 11, opacity: 0.7 }}>最大次数</label>
                          <InputNumber min={1} value={task.reminder_config.max_retries} onChange={v => v && updateReminder(selectedIdx, { max_retries: v })} style={{ width: '100%' }} />
                        </div>
                        <Button size="small" type="link" danger onClick={() => updateSubTask(selectedIdx, { reminder_config: undefined })}>禁用</Button>
                      </div>
                    ) : (
                      <Button size="small" type="dashed" onClick={() => updateSubTask(selectedIdx, { reminder_config: { first_delay_hours: 24, interval_hours: 12, escalation_delay_hours: 24, max_retries: 3 } })}>
                        启用提醒
                      </Button>
                    ),
                  }]}
                />
              </div>
            ) : null}
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
