import apiClient from './api';
import { ApiResponse, ChatQueryRequest, ChatQueryResponse, ChatMessage } from '../types';

export const chatService = {
  async sendQuery(payload: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
    const response = await apiClient.post<ApiResponse<ChatQueryResponse>>('/chat/query', payload);
    return response.data;
  },

  async getHistory(reportId: string): Promise<ApiResponse<{ report_id: string; messages: ChatMessage[] }>> {
    const response = await apiClient.get<ApiResponse<{ report_id: string; messages: ChatMessage[] }>>(
      `/chat/${reportId}/history`
    );
    return response.data;
  },

  async clearHistory(reportId: string): Promise<ApiResponse<any>> {
    const response = await apiClient.delete<ApiResponse<any>>(`/chat/${reportId}/history`);
    return response.data;
  },
};
