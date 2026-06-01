import client from './client';

// --- Sub-task definition types ---

export interface DeliverableCollectionRule {
  name: string;
  format: 'image' | 'video' | 'document' | 'any';
  required_count: number;
  description?: string;
}

export interface ReminderConfig {
  first_delay_hours: number;
  interval_hours: number;
  escalation_delay_hours: number;
  max_retries: number;
}

export interface SubTaskDef {
  title: string;
  description: string;
  assignees: string[];
  deliverable_rules: DeliverableCollectionRule[];
  reminder_config?: ReminderConfig;
}

// --- Template types ---

export interface PipelineTemplate {
  id: number;
  name: string;
  description: string;
  sub_tasks: SubTaskDef[];
  created_at: string;
  updated_at: string;
}

// --- API functions ---

export const listTemplates = () =>
  client.get<PipelineTemplate[]>('/api/templates').then(r => r.data);

export const getTemplate = (id: number) =>
  client.get<PipelineTemplate>(`/api/templates/${id}`).then(r => r.data);

export const createTemplate = (data: { name: string; description?: string; sub_tasks: SubTaskDef[] }) =>
  client.post<PipelineTemplate>('/api/templates', data).then(r => r.data);

export const updateTemplate = (id: number, data: { name?: string; description?: string; sub_tasks?: SubTaskDef[] }) =>
  client.put<PipelineTemplate>(`/api/templates/${id}`, data).then(r => r.data);

export const deleteTemplate = (id: number) =>
  client.delete(`/api/templates/${id}`).then(r => r.data);

export const cloneTemplate = (id: number) =>
  client.post<PipelineTemplate>(`/api/templates/${id}/clone`).then(r => r.data);
