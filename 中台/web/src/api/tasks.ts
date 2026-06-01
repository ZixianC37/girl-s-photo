import client from './client';

export interface TaskInstance {
  id: number;
  handler_name: string;
  feishu_record_id: string;
  platform: string;
  group_id: string;
  status: string;
  deadline: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TaskParticipant {
  id: number;
  feishu_user_id: string;
  platform_user_id: string | null;
  role: string;
  status: string;
  file_count: number;
  submitted_at: string | null;
}

export interface TaskDetail extends TaskInstance {
  participants: TaskParticipant[];
}

export interface TaskListResponse {
  items: TaskInstance[];
  total: number;
  page: number;
  page_size: number;
}

export const listTasks = (params?: { status?: string; handler?: string; page?: number; page_size?: number }) =>
  client.get<TaskListResponse>('/api/tasks', { params }).then(r => r.data);
export const getTaskDetail = (id: number) => client.get<TaskDetail>(`/api/tasks/${id}`).then(r => r.data);
