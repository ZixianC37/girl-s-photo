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

  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
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
