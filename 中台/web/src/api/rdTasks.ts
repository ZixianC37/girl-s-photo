import client from './client';

export interface DeliverableSpec {
  name: string;
  type: string;
  count: number;
}

export interface RDSubTask {
  id?: number;
  title: string;
  description?: string;
  assignees: string[];
  group_id: string;
  platform: string;
  deadline?: string;
  deliverables: DeliverableSpec[];
  sort_order: number;
  status?: string;
  task_instance_id?: number;
  progress?: { total_participants: number; confirmed: number; submitted: number };
}

export interface RDTask {
  id: number;
  title: string;
  description: string;
  status: string;
  created_at: string;
  sub_task_count?: number;
  sub_tasks?: RDSubTask[];
}

export const listRDTasks = () => client.get<RDTask[]>('/api/rd-tasks').then(r => r.data);
export const getRDTask = (id: number) => client.get<RDTask>(`/api/rd-tasks/${id}`).then(r => r.data);
export const createRDTask = (data: {
  title: string;
  description?: string;
  sub_tasks?: RDSubTask[];
  template_id?: number;
  stage_overrides?: Record<string, any>;
}) => client.post<RDTask>('/api/rd-tasks', data).then(r => r.data);
export const deleteRDTask = (id: number) => client.delete(`/api/rd-tasks/${id}`).then(r => r.data);

export const startRDTask = (id: number) =>
  client.post(`/api/rd-tasks/${id}/start`).then(r => r.data);

export const advanceRDTask = (id: number, stageIndex: number) =>
  client.post(`/api/rd-tasks/${id}/advance`, { stage_index: stageIndex }).then(r => r.data);

export const reworkRDTaskStage = (id: number, stageIndex: number, reason?: string) =>
  client.post(`/api/rd-tasks/${id}/rework`, { stage_index: stageIndex, reason }).then(r => r.data);
