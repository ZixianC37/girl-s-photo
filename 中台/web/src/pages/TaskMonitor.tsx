import { useEffect, useState } from 'react';
import { Table, Select, Tag, Modal, Descriptions, Space } from 'antd';
import { GlassCard } from '../components/GlassCard';
import { listTasks, getTaskDetail } from '../api/tasks';
import type { TaskInstance, TaskDetail } from '../api/tasks';
import { listHandlers } from '../api/handlers';

const statusColors: Record<string, string> = {
  pending: '#ffd54f',
  confirmed: '#69f0ae',
  submitted: '#90caf9',
  completed: '#69f0ae',
  error: '#ff5252',
};

const statusLabels: Record<string, string> = {
  pending: '待处理',
  confirmed: '已确认',
  submitted: '已提交',
  completed: '已完成',
  error: '错误',
};

export default function TaskMonitor() {
  const [data, setData] = useState<{ items: TaskInstance[]; total: number; page: number; page_size: number }>({ items: [], total: 0, page: 1, page_size: 20 });
  const [handlers, setHandlers] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [handlerFilter, setHandlerFilter] = useState<string | undefined>();
  const [detail, setDetail] = useState<TaskDetail | null>(null);

  const loadData = async (page = 1) => {
    const params: Record<string, unknown> = { page, page_size: 20 };
    if (statusFilter) params.status = statusFilter;
    if (handlerFilter) params.handler = handlerFilter;
    setData(await listTasks(params));
  };

  useEffect(() => {
    loadData();
    listHandlers().then(setHandlers);
  }, [statusFilter, handlerFilter]);

  const showDetail = async (record: TaskInstance) => {
    const d = await getTaskDetail(record.id);
    setDetail(d);
  };

  const columns = [
    { title: 'Handler', dataIndex: 'handler_name', key: 'handler' },
    {
      title: '飞书记录', dataIndex: 'feishu_record_id', key: 'record',
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v?.slice(0, 12)}...</span>,
    },
    {
      title: '平台', dataIndex: 'platform', key: 'platform',
      render: (v: string) => <Tag color={v === 'dingtalk' ? '#90caf9' : '#69f0ae'}>{v}</Tag>,
    },
    { title: '群', dataIndex: 'group_id', key: 'group', render: (v: string) => v?.slice(0, 12) },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColors[v] || '#999'}>{statusLabels[v] || v}</Tag>,
    },
    {
      title: '截止时间', dataIndex: 'deadline', key: 'deadline',
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created',
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'actions',
      render: (_: unknown, record: TaskInstance) => (
        <a onClick={() => showDetail(record)}>详情</a>
      ),
    },
  ];

  const participantColumns = [
    { title: '飞书 ID', dataIndex: 'feishu_user_id', key: 'feishu' },
    { title: '平台 ID', dataIndex: 'platform_user_id', key: 'platform' },
    { title: '角色', dataIndex: 'role', key: 'role' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColors[v] || '#999'}>{statusLabels[v] || v}</Tag>,
    },
    { title: '文件数', dataIndex: 'file_count', key: 'files' },
    {
      title: '提交时间', dataIndex: 'submitted_at', key: 'submitted',
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ color: '#fff', margin: 0, fontSize: 22 }}>任务监控</h2>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '4px 0 0', fontSize: 13 }}>查看所有任务实例的运行状态</p>
        </div>
        <Space>
          <Select
            placeholder="任务状态"
            allowClear
            style={{ width: 120 }}
            onChange={v => setStatusFilter(v)}
            options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
          />
          <Select
            placeholder="Handler"
            allowClear
            style={{ width: 160 }}
            onChange={v => setHandlerFilter(v)}
            options={handlers.map(h => ({ value: h, label: h }))}
          />
        </Space>
      </div>

      <GlassCard>
        <div className="glass">
          <Table
            dataSource={data.items}
            columns={columns}
            rowKey="id"
            size="small"
            pagination={{
              current: data.page,
              total: data.total,
              pageSize: data.page_size,
              onChange: (page) => loadData(page),
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        </div>
      </GlassCard>

      <Modal
        title="任务详情"
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={700}
      >
        {detail && (
          <>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="Handler">{detail.handler_name}</Descriptions.Item>
              <Descriptions.Item label="平台">{detail.platform}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColors[detail.status]}>{statusLabels[detail.status] || detail.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="截止时间">{detail.deadline ? new Date(detail.deadline).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="飞书记录" span={2}>{detail.feishu_record_id}</Descriptions.Item>
            </Descriptions>
            <h4 style={{ marginTop: 16, marginBottom: 8 }}>参与者</h4>
            <Table
              dataSource={detail.participants}
              columns={participantColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </>
        )}
      </Modal>
    </div>
  );
}
