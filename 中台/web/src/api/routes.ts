import client from './client';

export interface RouteConfig {
  id: number;
  handler_name: string;
  feishu_table_id: string;
  platform: string;
  group_id: string;
  field_mapping: Record<string, string> | string;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export const listRoutes = () => client.get<RouteConfig[]>('/api/routes').then(r => r.data);
export const createRoute = (data: Partial<RouteConfig>) => client.post('/api/routes', data).then(r => r.data);
export const updateRoute = (id: number, data: Partial<RouteConfig>) => client.put(`/api/routes/${id}`, data).then(r => r.data);
export const deleteRoute = (id: number) => client.delete(`/api/routes/${id}`).then(r => r.data);
