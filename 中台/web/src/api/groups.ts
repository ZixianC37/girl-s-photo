import client from './client';

export interface GroupMapping {
  id: number;
  name: string;
  group_id: string;
  platform: string;
}

export const listGroups = () => client.get<GroupMapping[]>('/api/groups').then(r => r.data);
export const createGroup = (data: { name: string; group_id: string; platform: string }) => client.post('/api/groups', data).then(r => r.data);
export const deleteGroup = (id: number) => client.delete(`/api/groups/${id}`).then(r => r.data);
