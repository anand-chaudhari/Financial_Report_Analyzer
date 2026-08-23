import apiClient from './api';
import { ApiResponse, ChatQueryRequest, ChatQueryResponse, ChatMessage } from '../types';

export interface DirectChatRequest {
  document_id: string;
  question: string;
  conversation_history?: Array<{ sender: string; text: string }>;
}

export interface DirectChatResponse {
  answer: string;
  sources: string[];
  pages: number[];
  sections: string[];
  retrieved_chunks: Array<{
    chunk_id?: string;
    text: string;
    page_number?: number;
    section?: string;
    similarity_score?: number;
  }>;
}

export const chatService = {
  async sendChat(payload: DirectChatRequest): Promise<DirectChatResponse> {
    // Direct POST /api/chat endpoint
    const response = await apiClient.post<DirectChatResponse>('/chat', payload);
    return response.data;
  },

  async sendQuery(payload: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
    // Envelope POST /api/v1/chat/query endpoint
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
