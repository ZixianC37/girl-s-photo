import client from './client';

export interface UserMapping {
  id: number;
  feishu_user_id: string | null;
  dingtalk_user_id: string | null;
  wecom_user_id: string | null;
  phone: string | null;
  name: string | null;
  sync_status: 'matched' | 'unmatched';
}

export interface UserListResponse {
  items: UserMapping[];
  total: number;
  page: number;
  page_size: number;
}

export const listUsers = (params?: { status?: string; search?: string; page?: number; page_size?: number }) =>
  client.get<UserListResponse>('/api/users', { params }).then(r => r.data);
export const updateUser = (id: number, data: Partial<UserMapping>) => client.put(`/api/users/${id}`, data).then(r => r.data);
export const syncUsers = () => client.post('/api/users/sync').then(r => r.data);
