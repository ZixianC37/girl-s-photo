import { useEffect, useState } from 'react';
import {
  Table, Modal, Form, Input, Select, Button, Tag, Popconfirm, Space,
  InputNumber, message, Spin, Steps, Descriptions, Tooltip,
} from 'antd';
import {
  PlayCircleOutlined, CheckCircleOutlined, UndoOutlined,
  ForwardOutlined,
} from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import {
  listRDTasks, getRDTask, createRDTask, deleteRDTask,
  startRDTask, advanceRDTask, reworkRDTaskStage,
} from '../api/rdTasks';
import type { RDTask, RDSubTask } from '../api/rdTasks';
import { listTemplates, getTemplate } from '../api/templates';
import type { PipelineTemplate } from '../api/templates';

const statusColors: Record<string, string> = {
  draft: '#999',
  active: '#1890ff',
  completed: '#52c41a',
  dispatched: '#13c2c2',
  rework: '#fa8c16',
};

const statusLabels: Record<string, string> = {
  draft: '草稿',
  active: '进行中',
  completed: '已完成',
  dispatched: '已分发',
  rework: '返工',
};

export default function RDTasks() {
  const [tasks, setTasks] = useState<RDTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<RDTask | null>(null);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [templateStages, setTemplateStages] = useState<{ title: string; description?: string; role_type?: string }[]>([]);
  const [stagesLoading, setStagesLoading] = useState(false);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [form] = Form.useForm();

  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await listRDTasks();
      setTasks(data);
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch {
      // silent
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    if (createModalOpen) {
      loadTemplates();
    }
  }, [createModalOpen]);

  // When a template is selected, load its stages and auto-fill sub_tasks
  const handleTemplateChange = async (templateId: number | undefined) => {
    setSelectedTemplateId(templateId || null);
    setTemplateStages([]);

    if (!templateId) {
      // Reset form sub_tasks to default empty one
      form.setFieldValue('sub_tasks', [{
        title: '', description: '', assignees: '', group_id: '',
        platform: 'dingtalk', deadline: '', sort_order: 0, deliverables: [],
      }]);
      return;
    }

    setStagesLoading(true);
    try {
      const tmpl = await getTemplate(templateId);
      const subTasks = tmpl.sub_tasks || [];
      setTemplateStages(subTasks);

      const generatedSubTasks = subTasks.map((st: { title: string; description?: string; assignees?: string[]; deliverable_rules?: { name: string; format: string; required_count: number }[] }, index: number) => ({
        title: st.title,
        description: st.description || '',
        assignees: (st.assignees || []).join(','),
        group_id: '',
        platform: 'dingtalk',
        deadline: '',
        sort_order: index,
        deliverables: st.deliverable_rules || [],
      }));
      form.setFieldValue('sub_tasks', generatedSubTasks);
    } catch (e) {
      console.error('Failed to load template:', e);
      message.error('加载模板失败');
    } finally {
      setStagesLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();

      if (selectedTemplateId) {
        // Create from template
        await createRDTask({
          title: values.title,
          description: values.description,
          template_id: selectedTemplateId,
        });
      } else {
        // Manual sub_task creation
        const sub_tasks = values.sub_tasks?.map((st: any, index: number) => ({
          ...st,
          sort_order: index,
          assignees: st.assignees?.split(',').map((s: string) => s.trim()).filter(Boolean) || [],
          deliverables: st.deliverables || [],
        })) || [];

        await createRDTask({
          title: values.title,
          description: values.description,
          sub_tasks,
        });
      }

      message.success('创建成功');
      setCreateModalOpen(false);
      form.resetFields();
      setSelectedTemplateId(null);
      setTemplateStages([]);
      loadTasks();
    } catch (error) {
      console.error('Create failed:', error);
      message.error('创建失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteRDTask(id);
      message.success('删除成功');
      loadTasks();
    } catch (error) {
      console.error('Delete failed:', error);
      message.error('删除失败');
    }
  };

  const showDetail = async (task: RDTask) => {
    setLoading(true);
    try {
      const detail = await getRDTask(task.id);
      setSelectedTask(detail);
      setDetailModalOpen(true);
    } finally {
      setLoading(false);
    }
  };

  // Pipeline operations
  const handleStart = async (id: number) => {
    setPipelineLoading(true);
    try {
      await startRDTask(id);
      message.success('已启动');
      const detail = await getRDTask(id);
      setSelectedTask(detail);
      loadTasks();
    } catch (e) {
      message.error('启动失败');
    } finally {
      setPipelineLoading(false);
    }
  };

  const handleAdvance = async (id: number, stageIndex: number) => {
    setPipelineLoading(true);
    try {
      await advanceRDTask(id, stageIndex);
      message.success('已推进到下一阶段');
      const detail = await getRDTask(id);
      setSelectedTask(detail);
      loadTasks();
    } catch (e) {
      message.error('推进失败');
    } finally {
      setPipelineLoading(false);
    }
  };

  const handleRework = async (id: number, stageIndex: number) => {
    setPipelineLoading(true);
    try {
      await reworkRDTaskStage(id, stageIndex, '返工');
      message.success('已退回返工');
      const detail = await getRDTask(id);
      setSelectedTask(detail);
      loadTasks();
    } catch (e) {
      message.error('返工操作失败');
    } finally {
      setPipelineLoading(false);
    }
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (v: string) => <span style={{ color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>{v}</span>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (v: string) => <span style={{ color: 'rgba(255,255,255,0.5)' }}>{v || '-'}</span>,
    },
    {
      title: '子任务数',
      dataIndex: 'sub_task_count',
      key: 'sub_task_count',
      render: (v: number) => <span style={{ color: 'rgba(255,255,255,0.7)' }}>{v || 0}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => <Tag color={statusColors[v] || '#999'}>{statusLabels[v] || v}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: RDTask) => (
        <Space>
          <a onClick={() => showDetail(record)} style={{ color: '#1890ff' }}>详情</a>
          <Popconfirm
            title="确认删除"
            description="确定要删除这个任务吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const subTaskColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '负责人',
      dataIndex: 'assignees',
      key: 'assignees',
      render: (v: string[]) => v?.join(', ') || '-',
    },
    {
      title: '群组',
      dataIndex: 'group_id',
      key: 'group_id',
      render: (v: string) => v?.slice(0, 12) || '-',
    },
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      render: (v: string) => <Tag color={v === 'dingtalk' ? '#90caf9' : '#69f0ae'}>{v}</Tag>,
    },
    {
      title: '截止时间',
      dataIndex: 'deadline',
      key: 'deadline',
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => <Tag color={statusColors[v] || '#999'}>{statusLabels[v] || v || '-'}</Tag>,
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: unknown, record: RDSubTask) => {
        const p = record.progress;
        if (!p) return '-';
        return `${p.confirmed}/${p.total_participants} 确认, ${p.submitted}/${p.total_participants} 提交`;
      },
    },
  ];

  // Workshop pipeline view for the detail modal
  const renderPipeline = () => {
    if (!selectedTask || !selectedTask.sub_tasks?.length) return null;

    const subTasks = selectedTask.sub_tasks;
    const currentIdx = subTasks.findIndex(s => s.status === 'active' || s.status === 'dispatched');

    return (
      <div style={{ marginBottom: 24 }}>
        <Steps
          current={currentIdx >= 0 ? currentIdx : subTasks.length}
          size="small"
          items={subTasks.map((st) => ({
            title: st.title,
            status: st.status === 'completed' ? 'finish' :
              st.status === 'rework' ? 'error' :
              (st.status === 'active' || st.status === 'dispatched') ? 'process' : 'wait',
            description: (
              <span style={{ fontSize: 11 }}>
                {statusLabels[st.status || ''] || st.status}
              </span>
            ),
          }))}
        />
        <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {selectedTask.status === 'draft' && (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={pipelineLoading}
              onClick={() => handleStart(selectedTask.id)}
            >
              启动流水线
            </Button>
          )}
          {subTasks.map((st, idx) => {
            if (st.status === 'dispatched' || st.status === 'active') {
              return (
                <Space key={st.id || idx}>
                  <Button
                    icon={<CheckCircleOutlined />}
                    loading={pipelineLoading}
                    onClick={() => handleAdvance(selectedTask.id, idx)}
                  >
                    完成阶段: {st.title}
                  </Button>
                  <Tooltip title="退回返工">
                    <Button
                      danger
                      icon={<UndoOutlined />}
                      loading={pipelineLoading}
                      onClick={() => handleRework(selectedTask.id, idx)}
                    >
                      返工
                    </Button>
                  </Tooltip>
                </Space>
              );
            }
            if (st.status === 'rework') {
              return (
                <Button
                  key={st.id || idx}
                  icon={<ForwardOutlined />}
                  loading={pipelineLoading}
                  onClick={() => handleAdvance(selectedTask.id, idx)}
                >
                  重新推进: {st.title}
                </Button>
              );
            }
            return null;
          })}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ color: '#fff', margin: 0, fontSize: 22 }}>产品研发</h2>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '4px 0 0', fontSize: 13 }}>管理产品研发任务和子任务</p>
        </div>
        <Button type="primary" onClick={() => setCreateModalOpen(true)}>创建任务</Button>
      </div>

      <GlassCard>
        <div className="glass">
          <Table
            dataSource={tasks}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={false}
          />
        </div>
      </GlassCard>

      {/* Create Modal */}
      <Modal
        title="创建研发任务"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalOpen(false);
          form.resetFields();
          setSelectedTemplateId(null);
          setTemplateStages([]);
        }}
        width={800}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="任务标题"
            name="title"
            rules={[{ required: true, message: '请输入任务标题' }]}
          >
            <Input placeholder="输入任务标题" />
          </Form.Item>
          <Form.Item
            label="任务描述"
            name="description"
          >
            <Input.TextArea placeholder="输入任务描述" rows={3} />
          </Form.Item>

          {/* Template selection */}
          <Form.Item label="从模板创建" tooltip="选择模板后自动生成子任务阶段">
            <Select
              placeholder="选择一个流水线模板（可选）"
              allowClear
              onChange={handleTemplateChange}
              loading={stagesLoading}
              style={{ width: '100%' }}
            >
              {templates.map(t => (
                <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          {/* Show template stages preview when template is selected */}
          {selectedTemplateId && templateStages.length > 0 && (
            <div style={{
              marginBottom: 16, padding: 12,
              background: 'rgba(24,144,255,0.05)', borderRadius: 8,
              border: '1px solid rgba(24,144,255,0.2)',
            }}>
              <div style={{ fontWeight: 500, marginBottom: 8, color: '#1890ff' }}>
                模板阶段预览 ({templateStages.length} 个阶段)
              </div>
              {templateStages.map((stage, i) => (
                <div key={i} style={{
                  padding: '4px 0', fontSize: 13,
                  borderBottom: i < templateStages.length - 1 ? '1px dashed #f0f0f0' : 'none',
                }}>
                  <span style={{ fontWeight: 500 }}>{i + 1}. {stage.title}</span>
                  {stage.description && (
                    <span style={{ color: 'rgba(0,0,0,0.45)', marginLeft: 8 }}>- {stage.description}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Manual sub_task editing - only when no template selected */}
          {!selectedTemplateId && (
            <Form.List
              name="sub_tasks"
              initialValue={[{
                title: '', description: '', assignees: '', group_id: '',
                platform: 'dingtalk', deadline: '', sort_order: 0, deliverables: [],
              }]}
            >
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <div key={key} style={{ marginBottom: 16, paddingBottom: 16, borderBottom: '1px solid #f0f0f0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontWeight: 500 }}>子任务 {name + 1}</span>
                        {fields.length > 1 && (
                          <Button type="link" danger size="small" onClick={() => remove(name)}>
                            删除
                          </Button>
                        )}
                      </div>
                      <Form.Item
                        {...restField}
                        name={[name, 'title']}
                        label="子任务标题"
                        rules={[{ required: true, message: '请输入子任务标题' }]}
                      >
                        <Input placeholder="输入子任务标题" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'description']}
                        label="子任务描述"
                      >
                        <Input.TextArea placeholder="输入子任务描述" rows={2} />
                      </Form.Item>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <Form.Item
                          {...restField}
                          name={[name, 'assignees']}
                          label="负责人"
                          style={{ flex: 1 }}
                          tooltip="多个负责人用逗号分隔"
                        >
                          <Input placeholder="输入负责人，逗号分隔" />
                        </Form.Item>
                        <Form.Item
                          {...restField}
                          name={[name, 'group_id']}
                          label="群组ID"
                          style={{ flex: 1 }}
                          rules={[{ required: true, message: '请输入群组ID' }]}
                        >
                          <Input placeholder="输入群组ID" />
                        </Form.Item>
                      </div>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <Form.Item
                          {...restField}
                          name={[name, 'platform']}
                          label="平台"
                          style={{ flex: 1 }}
                          rules={[{ required: true, message: '请选择平台' }]}
                        >
                          <Select placeholder="选择平台">
                            <Select.Option value="dingtalk">钉钉</Select.Option>
                            <Select.Option value="wecom">企微</Select.Option>
                          </Select>
                        </Form.Item>
                        <Form.Item
                          {...restField}
                          name={[name, 'deadline']}
                          label="截止时间"
                          style={{ flex: 1 }}
                        >
                          <Input placeholder="输入截止时间 (YYYY-MM-DD HH:mm:ss)" />
                        </Form.Item>
                      </div>
                      <Form.Item
                        {...restField}
                        name={[name, 'sort_order']}
                        label="排序"
                        initialValue={name}
                      >
                        <InputNumber style={{ width: '100%' }} />
                      </Form.Item>
                    </div>
                  ))}
                  <Button type="dashed" onClick={() => add()} block style={{ marginBottom: 12 }}>
                    + 添加子任务
                  </Button>
                </>
              )}
            </Form.List>
          )}
        </Form>
      </Modal>

      {/* Detail Modal with Workshop/Pipeline view */}
      <Modal
        title="任务详情"
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedTask(null);
        }}
        footer={null}
        width={1000}
      >
        {selectedTask && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Descriptions
                title={selectedTask.title}
                size="small"
                column={3}
              >
                <Descriptions.Item label="描述">{selectedTask.description || '-'}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={statusColors[selectedTask.status] || '#999'}>
                    {statusLabels[selectedTask.status] || selectedTask.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {new Date(selectedTask.created_at).toLocaleString('zh-CN')}
                </Descriptions.Item>
              </Descriptions>
            </div>

            {/* Pipeline/Workshop view */}
            {renderPipeline()}

            {/* Sub-tasks table */}
            <h4 style={{ marginBottom: 12 }}>子任务列表</h4>
            {loading ? (
              <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
            ) : (
              <Table
                dataSource={selectedTask.sub_tasks || []}
                columns={subTaskColumns}
                rowKey={(record) => record.id?.toString() || `${record.title}-${record.sort_order}`}
                pagination={false}
                size="small"
              />
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
