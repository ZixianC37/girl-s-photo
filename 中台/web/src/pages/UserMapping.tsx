import { useEffect, useState } from 'react';
import { Table, Select, Input, Button, Tag, Space, Modal, Form, message } from 'antd';
import { SyncOutlined, EditOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { listUsers, updateUser, syncUsers } from '../api/users';
import type { UserMapping, UserListResponse } from '../api/users';

export default function UserMapping() {
  const [data, setData] = useState<UserListResponse>({ items: [], total: 0, page: 1, page_size: 20 });
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [search, setSearch] = useState('');
  const [editModal, setEditModal] = useState<UserMapping | null>(null);
  const [form] = Form.useForm();

  const loadData = async (page = 1) => {
    const params: Record<string, unknown> = { page, page_size: 20 };
    if (statusFilter) params.status = statusFilter;
    if (search) params.search = search;
    setData(await listUsers(params));
  };

  useEffect(() => { loadData(); }, [statusFilter]);

  const handleSearch = (value: string) => {
    setSearch(value);
    // Reload with search after a brief delay
    setTimeout(() => {
      const params: Record<string, unknown> = { page: 1, page_size: 20 };
      if (statusFilter) params.status = statusFilter;
      if (value) params.search = value;
      listUsers(params).then(setData);
    }, 0);
  };

  const handleSync = async () => {
    const result = await syncUsers();
    message.success(`同步完成：匹配 ${result.synced} 个用户`);
    loadData();
  };

  const handleSave = async () => {
    if (!editModal) return;
    const values = await form.validateFields();
    await updateUser(editModal.id, values);
    message.success('用户已更新');
    setEditModal(null);
    form.resetFields();
    loadData();
  };

  const openEdit = (record: UserMapping) => {
    setEditModal(record);
    form.setFieldsValue({
      dingtalk_user_id: record.dingtalk_user_id || '',
      wecom_user_id: record.wecom_user_id || '',
    });
  };

  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name', render: (v: string) => v || '-' },
    { title: '飞书 ID', dataIndex: 'feishu_user_id', key: 'feishu', render: (v: string) => v || '-' },
    { title: '钉钉 ID', dataIndex: 'dingtalk_user_id', key: 'dingtalk', render: (v: string) => v || <span style={{ color: '#ff5252' }}>未绑定</span> },
    { title: '企微 ID', dataIndex: 'wecom_user_id', key: 'wecom', render: (v: string) => v || <span style={{ color: '#ff5252' }}>未绑定</span> },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    {
      title: '映射状态', dataIndex: 'sync_status', key: 'status',
      render: (v: string) => <Tag color={v === 'matched' ? '#69f0ae' : '#ff5252'}>{v === 'matched' ? '已匹配' : '未匹配'}</Tag>,
    },
    {
      title: '操作', key: 'actions',
      render: (_: unknown, record: UserMapping) => (
        <a onClick={() => openEdit(record)}><EditOutlined /> 编辑</a>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ color: '#fff', margin: 0, fontSize: 22 }}>用户映射管理</h2>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '4px 0 0', fontSize: 13 }}>飞书 ↔ 钉钉/企微用户映射</p>
        </div>
        <Space>
          <Select
            placeholder="映射状态"
            allowClear
            style={{ width: 120 }}
            onChange={v => setStatusFilter(v)}
            options={[
              { value: 'matched', label: '已匹配' },
              { value: 'unmatched', label: '未匹配' },
            ]}
          />
          <Input.Search
            placeholder="搜索姓名/手机号"
            onSearch={handleSearch}
            style={{ width: 200 }}
            allowClear
          />
          <Button icon={<SyncOutlined />} onClick={handleSync}>一键同步</Button>
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
        title="编辑用户映射"
        open={!!editModal}
        onOk={handleSave}
        onCancel={() => { setEditModal(null); form.resetFields(); }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="dingtalk_user_id" label="钉钉用户 ID">
            <Input placeholder="输入钉钉用户 ID" />
          </Form.Item>
          <Form.Item name="wecom_user_id" label="企微用户 ID">
            <Input placeholder="输入企微用户 ID" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
