import client from './client';

export interface SubTask {
  id: number;
  project_id: number;
  stage_index: number;
  stage_name: string;
  title: string;
  description: string;
  assignees: string;
  group_id: string;
  platform: string;
  deadline: string | null;
  deliverables: string;
  status: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface RDProject {
  id: number;
  name: string;
  description: string;
  template_id: number;
  stages_snapshot: string;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  sub_tasks?: SubTask[];
}

export const listProjects = (params?: { status?: string }) =>
  client.get<RDProject[]>('/api/projects', { params }).then(r => r.data);

export const getProject = (id: number) =>
  client.get<RDProject>(`/api/projects/${id}`).then(r => r.data);

export const createProject = (data: {
  name: string;
  description?: string;
  template_id?: number;
  sub_tasks?: {
    title: string;
    description?: string;
    assignees?: string[];
    deliverable_rules?: { name: string; format: string; required_count: number; description?: string }[];
    reminder_config?: { first_delay_hours: number; interval_hours: number; escalation_delay_hours: number; max_retries: number };
  }[];
}) => client.post<RDProject>('/api/projects', data).then(r => r.data);

export const startProject = (id: number) =>
  client.post<RDProject>(`/api/projects/${id}/start`).then(r => r.data);

export const advanceProject = (id: number, stageIndex: number) =>
  client.post<RDProject>(`/api/projects/${id}/advance`, { stage_index: stageIndex }).then(r => r.data);

export const reworkStage = (id: number, stageIndex: number, reason?: string) =>
  client.post<RDProject>(`/api/projects/${id}/rework`, { stage_index: stageIndex, reason }).then(r => r.data);

export const patchProjectStatus = (id: number, status: string) =>
  client.patch<RDProject>(`/api/projects/${id}`, { status }).then(r => r.data);

export const deleteProject = (id: number) =>
  client.delete(`/api/projects/${id}`).then(r => r.data);
