import client from './client';

export const listHandlers = () => client.get<string[]>('/api/handlers').then(r => r.data);
