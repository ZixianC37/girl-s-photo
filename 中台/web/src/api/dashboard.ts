import client from './client';
import type { TaskInstance } from './tasks';

export interface DashboardStats {
  active_routes: number;
  registered_handlers: number;
  today_tasks: number;
  error_rate: number;
  recent_tasks: TaskInstance[];
}

export const getStats = () => client.get<DashboardStats>('/api/dashboard/stats').then(r => r.data);
