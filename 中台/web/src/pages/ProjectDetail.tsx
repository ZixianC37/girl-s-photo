import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, Button, Tag, Spin, message, Descriptions, Space } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import { getProject, startProject, advanceProject, reworkStage, type RDProject, type SubTask } from '../api/projects';
import ProjectTimeline from './ProjectTimeline';
import WorkshopScene from '../components/workshop/WorkshopScene';
import type { SubTaskData } from '../components/workshop/types';

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿', active: '进行中', paused: '已暂停', completed: '已完成',
  pending: '待开始', dispatched: '已派发', rework: '返工中', blocked: '已阻塞',
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
  const [selectedMember, setSelectedMember] = useState<string | null>(null);

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

  const stages = project?.sub_tasks || [];

  const subTaskData: SubTaskData[] = useMemo(() =>
    stages.map((s: SubTask) => ({
      id: s.id,
      title: s.title || s.stage_name || `子任务${s.sort_order + 1}`,
      status: s.status,
      sort_order: s.sort_order ?? s.stage_index,
      assignees: s.assignees,
      deliverables: s.deliverables,
    })),
    [stages]
  );

  if (loading) return <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>;
  if (!project) return <div>项目不存在</div>;

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
                projectName={project.name}
                subTasks={subTaskData}
                selectedMember={selectedMember}
                onMemberSelect={setSelectedMember}
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
