export type SubTaskStatus = 'pending' | 'dispatched' | 'active' | 'completed' | 'rework' | 'blocked';

export const STATUS_COLORS: Record<string, string> = {
  pending: '#555',
  dispatched: '#1890ff',
  active: '#13c2c2',
  completed: '#52c41a',
  rework: '#fa8c16',
  blocked: '#ff4d4f',
};

export const STATUS_LABELS: Record<string, string> = {
  pending: '待开始',
  dispatched: '已派发',
  active: '进行中',
  completed: '已完成',
  rework: '返工中',
  blocked: '已阻塞',
};

export interface SubTaskData {
  id: number;
  title: string;
  status: string;
  sort_order: number;
  assignees: string;
  deliverables: string;
}
