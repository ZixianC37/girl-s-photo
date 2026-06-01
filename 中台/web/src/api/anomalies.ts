import client from './client';

export interface Anomaly {
  id: number;
  type: string;
  severity: string;
  project_id: number;
  project_name: string | null;
  stage_name: string;
  stage_index: number;
  assignees: string[];
  status: string;
  created_at: string;
  updated_at: string;
}

export const listAnomalies = (params?: { project_id?: number; severity?: string }) =>
  client.get<Anomaly[]>('/api/anomalies', { params }).then(r => r.data);

export const resolveAnomaly = (id: number, action: string, data?: Record<string, unknown>) =>
  client.patch<Anomaly>(`/api/anomalies/${id}`, { action, data }).then(r => r.data);
