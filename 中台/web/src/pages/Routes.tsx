import { useEffect, useState } from 'react';
import { Table, Button, Tag, Switch, Modal, Form, Select, Input, Space, Popconfirm, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { listRoutes, createRoute, updateRoute, deleteRoute, type RouteConfig } from '../api/routes';
import { listHandlers } from '../api/handlers';

const platformColors: Record<string, string> = {
  dingtalk: '#90caf9',
  wecom: '#ffd54f',
  both: '#69f0ae',
};

const platformLabels: Record<string, string> = {
  dingtalk: '钉钉',
  wecom: '企微',
  both: '双平台',
};

export default function RoutesPage() {
  const [routes, setRoutes] = useState<RouteConfig[]>([]);
  const [handlers, setHandlers] = useState<string[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<RouteConfig | null>(null);
  const [form] = Form.useForm();

  const loadData = async () => {
    const [r, h] = await Promise.all([listRoutes(), listHandlers()]);
    setRoutes(r);
    setHandlers(h);
  };

  useEffect(() => { loadData(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();

    // Convert field_mapping from array to object
    if (values.field_mapping && Array.isArray(values.field_mapping)) {
      values.field_mapping = values.field_mapping.reduce((acc: Record<string, string>, item: {feishu?: string; param?: string}) => {
        if (item.feishu && item.param) acc[item.feishu] = item.param;
        return acc;
      }, {});
    }

    if (editingRoute) {
      await updateRoute(editingRoute.id, values);
      message.success('路由已更新');
    } else {
      await createRoute(values);
      message.success('路由已创建');
    }
    setModalOpen(false);
    setEditingRoute(null);
    form.resetFields();
    loadData();
  };

  const handleDelete = async (id: number) => {
    await deleteRoute(id);
    message.success('路由已删除');
    loadData();
  };

  const handleToggle = async (record: RouteConfig) => {
    await updateRoute(record.id, { enabled: !record.enabled });
    loadData();
  };

  const openEdit = (record: RouteConfig) => {
    setEditingRoute(record);
    const mapping = typeof record.field_mapping === 'string'
      ? JSON.parse(record.field_mapping || '{}')
      : record.field_mapping;
    form.setFieldsValue({
      ...record,
      field_mapping: Object.entries(mapping).map(([feishu, param]) => ({ feishu, param })),
    });
    setModalOpen(true);
  };

  const openCreate = () => {
    setEditingRoute(null);
    form.resetFields();
    setModalOpen(true);
  };

  const columns = [
    { title: 'Handler', dataIndex: 'handler_name', key: 'handler' },
    {
      title: '飞书表 ID', dataIndex: 'feishu_table_id', key: 'table',
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v?.slice(0, 12)}...</span>,
    },
    {
      title: '平台', dataIndex: 'platform', key: 'platform',
      render: (v: string) => <Tag color={platformColors[v]}>{platformLabels[v] || v}</Tag>,
    },
    { title: '目标群', dataIndex: 'group_id', key: 'group' },
    {
      title: '状态', dataIndex: 'enabled', key: 'enabled',
      render: (v: boolean, record: RouteConfig) => (
        <Switch size="small" checked={v} onChange={() => handleToggle(record)} />
      ),
    },
    {
      title: '操作', key: 'actions',
      render: (_: unknown, record: RouteConfig) => (
        <Space size="small">
          <a onClick={() => openEdit(record)}>编辑</a>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#ff5252' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ color: '#fff', margin: 0, fontSize: 22 }}>任务路由配置</h2>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '4px 0 0', fontSize: 13 }}>管理飞书事件到钉钉/企微的路由规则</p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建路由</Button>
      </div>

      <GlassCard>
        <div className="glass">
          <Table
            dataSource={routes}
            columns={columns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </div>
      </GlassCard>

      <Modal
        title={editingRoute ? '编辑路由' : '新建路由'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingRoute(null); form.resetFields(); }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="handler_name" label="Handler" rules={[{ required: true }]}>
            <Select placeholder="选择 Handler">
              {handlers.map(h => <Select.Option key={h} value={h}>{h}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="feishu_table_id" label="飞书表 ID" rules={[{ required: true }]}>
            <Input placeholder="tbl_xxx" />
          </Form.Item>
          <Form.Item name="platform" label="触达平台" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="dingtalk">钉钉</Select.Option>
              <Select.Option value="wecom">企微</Select.Option>
              <Select.Option value="both">双平台</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="group_id" label="目标群 ID" rules={[{ required: true }]}>
            <Input placeholder="group_xxx" />
          </Form.Item>
          <Form.List name="field_mapping">
            {(fields, { add, remove }) => (
              <>
                <div style={{ marginBottom: 8, fontWeight: 500 }}>字段映射</div>
                {fields.map(({ key, name, ...rest }) => (
                  <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item {...rest} name={[name, 'feishu']} style={{ margin: 0 }}>
                      <Input placeholder="飞书字段" />
                    </Form.Item>
                    <span>→</span>
                    <Form.Item {...rest} name={[name, 'param']} style={{ margin: 0 }}>
                      <Input placeholder="任务参数" />
                    </Form.Item>
                    <a onClick={() => remove(name)}>删除</a>
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add()} block>+ 添加映射</Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
}
