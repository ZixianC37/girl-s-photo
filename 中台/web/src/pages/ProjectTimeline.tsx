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
          {i < stages.length - 1 && (
            <div style={{
              position: 'absolute', left: 7, top: 24, bottom: 0, width: 2,
              background: s.status === 'completed' ? '#52c41a' : 'rgba(255,255,255,0.2)',
            }} />
          )}
          <div style={{
            position: 'absolute', left: 0, top: 6,
            width: 16, height: 16, borderRadius: '50%',
            background: s.status === 'completed' ? '#52c41a' :
              s.status === 'dispatched' ? '#1890ff' :
              s.status === 'rework' ? '#ff4d4f' : '#666',
          }} />
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
