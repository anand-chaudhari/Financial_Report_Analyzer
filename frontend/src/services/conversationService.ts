import apiClient from './api';

export interface SourceMetadata {
  page_number: number;
  section: string;
  document_name: string;
  snippet?: string;
  similarity_score?: number;
}

export interface MessageItem {
  messageId: string;
  conversationId: string;
  userId: string;
  role: 'user' | 'assistant';
  content: string;
  sources: SourceMetadata[];
  createdAt: string;
}

export interface ConversationItem {
  conversationId: string;
  userId: string;
  documentId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages?: MessageItem[];
}

export const conversationService = {
  async getConversations(documentId?: string): Promise<ConversationItem[]> {
    try {
      const url = documentId ? `/conversations?document_id=${documentId}` : '/conversations';
      const response = await apiClient.get<any>(url);
      const resData = response.data;
      return resData.data || resData || [];
    } catch (err) {
      console.warn('Could not fetch conversations from backend:', err);
      return [];
    }
  },

  async createConversation(documentId: string, title?: string): Promise<ConversationItem> {
    const response = await apiClient.post<any>('/conversations', {
      documentId,
      title: title || 'New Financial Analysis',
    });
    const resData = response.data;
    return resData.data || resData;
  },

  async getConversation(conversationId: string): Promise<ConversationItem> {
    const response = await apiClient.get<any>(`/conversations/${conversationId}`);
    const resData = response.data;
    return resData.data || resData;
  },

  async renameConversation(conversationId: string, title: string): Promise<ConversationItem> {
    const response = await apiClient.patch<any>(`/conversations/${conversationId}`, { title });
    const resData = response.data;
    return resData.data || resData;
  },

  async deleteConversation(conversationId: string): Promise<boolean> {
    try {
      await apiClient.delete(`/conversations/${conversationId}`);
      return true;
    } catch (err) {
      console.warn('Failed to delete conversation from backend:', err);
      return false;
    }
  },
};
