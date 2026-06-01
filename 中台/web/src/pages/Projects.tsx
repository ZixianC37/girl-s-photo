import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Tag, Row, Col, Modal, message, Statistic } from 'antd';
import { PlusOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import {
  listProjects, startProject, patchProjectStatus, deleteProject,
  type RDProject,
} from '../api/projects';

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
  const [loading, setLoading] = useState(true);

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

  useEffect(() => { fetchProjects(); }, []);

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
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/projects/new')}>
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
    </div>
  );
}
