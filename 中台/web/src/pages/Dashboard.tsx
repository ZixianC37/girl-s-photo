import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Row, Col, Card, Statistic, Spin, message, Tag, Empty, Button } from 'antd';
import {
  AppstoreOutlined, CheckCircleOutlined, WarningOutlined,
  PlusOutlined, EyeOutlined, DownOutlined, UpOutlined,
} from '@ant-design/icons';
import { GlassCard } from '../components/GlassCard';
import WorkshopScene from '../components/workshop/WorkshopScene';
import { listProjects, getProject, type RDProject, type SubTask } from '../api/projects';
import { listAnomalies } from '../api/anomalies';
import { listTemplates } from '../api/templates';
import { STATUS_COLORS } from '../components/workshop/types';

// Preview scale: card ~350px wide / scene 960px ≈ 0.365
const PREVIEW_SCALE = 0.365;
const PREVIEW_HEIGHT = Math.ceil(540 * PREVIEW_SCALE);

const tasksCache = new Map<number, SubTask[]>();

export default function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<RDProject[]>([]);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [templateCount, setTemplateCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [tasksMap, setTasksMap] = useState<Map<number, SubTask[]>>(new Map());

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

  const togglePreview = useCallback(async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    if (!tasksCache.has(id) && !tasksMap.has(id)) {
      try {
        const proj = await getProject(id);
        const tasks = proj.sub_tasks || [];
        tasksCache.set(id, tasks);
        setTasksMap(prev => new Map(prev).set(id, tasks));
      } catch {
        message.error('加载任务数据失败');
        return;
      }
    }
    setExpandedId(id);
  }, [expandedId, tasksMap]);

  const activeProjects = projects.filter(p => p.status === 'active');
  const completedProjects = projects.filter(p => p.status === 'completed');

  return (
    <div style={{ padding: 24 }}>
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
            <Statistic title="任务模板" value={templateCount}
              prefix={<AppstoreOutlined />} valueStyle={{ color: '#722ed1' }} />
          </GlassCard>
        </Col>
      </Row>

      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>活跃项目</h3>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/templates')}>
            新建项目
          </Button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
        ) : activeProjects.length === 0 ? (
          <Empty description="暂无活跃项目，从模板创建一个吧" />
        ) : (
          <Row gutter={[16, 16]}>
            {activeProjects.map(p => {
              const subTasks = p.sub_tasks || [];
              const completedCount = subTasks.filter(s => s.status === 'completed').length;
              const totalCount = subTasks.length;
              const progress = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
              const currentSub = subTasks.find(s => s.status === 'dispatched' || s.status === 'active');
              const isExpanded = expandedId === p.id;
              const previewTasks = tasksMap.get(p.id) || tasksCache.get(p.id) || [];

              return (
                <Col xs={24} sm={12} md={8} key={p.id}>
                  <div style={{
                    background: 'linear-gradient(135deg, rgba(24,144,255,0.1), rgba(114,46,209,0.05))',
                    border: '1px solid rgba(24,144,255,0.3)',
                    borderRadius: 8,
                    overflow: 'hidden',
                  }}>
                    <Card
                      hoverable
                      bordered={false}
                      onClick={() => navigate(`/projects/${p.id}`)}
                      style={{ background: 'transparent', cursor: 'pointer' }}
                      bodyStyle={{ paddingBottom: 8 }}
                    >
                      {/* Mini pipeline preview */}
                      {subTasks.length > 0 && (
                        <div style={{ marginBottom: 12 }}>
                          <svg viewBox={`0 0 ${Math.max(200, subTasks.length * 36)} 30`} style={{ width: '100%', height: 30 }}>
                            {subTasks.map((s, i) => {
                              const x = subTasks.length <= 1 ? 100 : 15 + (170 / (subTasks.length - 1)) * i;
                              const color = STATUS_COLORS[s.status] || '#555';
                              return (
                                <g key={s.id || i}>
                                  {i < subTasks.length - 1 && (
                                    <line
                                      x1={x} y1={15}
                                      x2={subTasks.length <= 1 ? 100 : 15 + (170 / (subTasks.length - 1)) * (i + 1)}
                                      y2={15}
                                      stroke={s.status === 'completed' ? '#52c41a' : '#333'}
                                      strokeWidth={2}
                                    />
                                  )}
                                  <circle cx={x} cy={15} r={5} fill={color} />
                                  <text x={x} y={28} textAnchor="middle" fill="#777" fontSize={5}>
                                    {(s.title || '').slice(0, 4)}
                                  </text>
                                </g>
                              );
                            })}
                          </svg>
                        </div>
                      )}

                      <Card.Meta
                        title={
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>{p.name}</span>
                            <Tag color="processing">进行中</Tag>
                          </div>
                        }
                        description={
                          <div>
                            {subTasks.length > 0 ? (
                              <>
                                <div style={{ marginBottom: 4 }}>
                                  当前：{currentSub?.title || '-'}
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
                                  {completedCount}/{totalCount} 子任务 ({progress}%)
                                </div>
                              </>
                            ) : (
                              <div style={{ fontSize: 13, color: '#999' }}>点击查看工作坊场景</div>
                            )}
                          </div>
                        }
                      />
                    </Card>

                    {/* Preview toggle */}
                    <div
                      onClick={(e) => togglePreview(p.id, e)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                        padding: '6px 0', cursor: 'pointer',
                        borderTop: '1px solid rgba(24,144,255,0.15)',
                        color: isExpanded ? '#1890ff' : 'rgba(255,255,255,0.45)',
                        fontSize: 12, userSelect: 'none',
                        transition: 'color 0.2s, background 0.2s',
                        background: isExpanded ? 'rgba(24,144,255,0.08)' : 'transparent',
                      }}
                    >
                      <EyeOutlined />
                      <span>预览工作坊</span>
                      {isExpanded ? <UpOutlined style={{ fontSize: 10 }} /> : <DownOutlined style={{ fontSize: 10 }} />}
                    </div>

                    {/* Collapsible preview */}
                    <div style={{
                      maxHeight: isExpanded ? PREVIEW_HEIGHT + 8 : 0,
                      overflow: 'hidden',
                      transition: 'max-height 0.35s ease',
                      background: '#1a1a2a',
                    }}>
                      {isExpanded && previewTasks.length > 0 && (
                        <div style={{
                          width: 960,
                          height: 540,
                          transform: `scale(${PREVIEW_SCALE})`,
                          transformOrigin: 'top left',
                        }}>
                          <WorkshopScene
                            projectName={p.name}
                            subTasks={previewTasks.map(st => ({
                              id: st.id,
                              title: st.title,
                              status: st.status,
                              sort_order: st.sort_order,
                              assignees: st.assignees,
                              deliverables: st.deliverables,
                            }))}
                          />
                        </div>
                      )}
                      {isExpanded && previewTasks.length === 0 && (
                        <div style={{
                          height: PREVIEW_HEIGHT,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: 'rgba(255,255,255,0.3)', fontSize: 13,
                        }}>
                          暂无任务数据
                        </div>
                      )}
                    </div>
                  </div>
                </Col>
              );
            })}
          </Row>
        )}
      </GlassCard>
    </div>
  );
}
