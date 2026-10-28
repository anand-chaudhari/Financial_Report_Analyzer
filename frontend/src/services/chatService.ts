import apiClient from './api';
import { ApiResponse, ChatQueryRequest, ChatQueryResponse, ChatMessage } from '../types';
import { API_BASE_URL } from '../utils/constants';
import { auth } from '../firebase/config';
import { getIdToken } from 'firebase/auth';

export interface WebSourceItem {
  title: string;
  snippet: string;
  url: string;
  date?: string;
  publisher?: string;
}

export interface DirectChatRequest {
  document_id?: string;
  documentId?: string;
  conversation_id?: string;
  conversationId?: string;
  question: string;
  conversation_history?: Array<{ sender?: string; role?: string; text?: string; content?: string }>;
  use_web_search?: boolean;
  useWebSearch?: boolean;
  search_mode?: 'auto' | 'on' | 'off';
  searchMode?: 'auto' | 'on' | 'off';
}

export interface DirectChatResponse {
  conversationId?: string;
  messageId?: string;
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
  web_sources?: WebSourceItem[];
  market_data?: Record<string, any>;
}

export const chatService = {
  async sendChat(payload: DirectChatRequest, signal?: AbortSignal): Promise<DirectChatResponse> {
    const response = await apiClient.post<DirectChatResponse>('/chat', payload, { signal });
    return response.data;
  },

  async streamChat(
    payload: DirectChatRequest,
    onToken: (token: string, accumulated: string) => void,
    onStart?: (meta: Partial<DirectChatResponse>) => void,
    signal?: AbortSignal
  ): Promise<DirectChatResponse> {
    let accumulated = '';
    let meta: Partial<DirectChatResponse> = {
      sources: [],
      pages: [],
      sections: [],
      web_sources: [],
    };

    try {
      const user = auth.currentUser;
      const token = user ? await getIdToken(user, false) : '';

      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
        signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Stream request failed with status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      const processLine = (line: string) => {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) return;

        const rawData = trimmed.replace(/^data:\s*/, '');
        if (rawData === '[DONE]') return;

        try {
          const data = JSON.parse(rawData);
          if (data.type === 'start') {
            meta = {
              ...meta,
              sources: data.sources || [],
              pages: data.pages || [],
              sections: data.sections || [],
              web_sources: data.web_sources || [],
              market_data: data.market_data,
              conversationId: data.conversationId,
            };
            if (onStart) onStart(meta);
          } else if (data.type === 'token') {
            const tokenStr = typeof data.content === 'string' ? data.content : '';
            if (tokenStr) {
              accumulated += tokenStr;
              onToken(tokenStr, accumulated);
            }
          } else if (data.type === 'done') {
            meta = {
              ...meta,
              answer: data.full_answer || accumulated,
              sources: data.sources || meta.sources,
              pages: data.pages || meta.pages,
              sections: data.sections || meta.sections,
              web_sources: data.web_sources || meta.web_sources,
              market_data: data.market_data || meta.market_data,
              conversationId: data.conversationId || meta.conversationId,
            };
          } else if (data.type === 'error') {
            throw new Error(data.error || 'Server stream error');
          }
        } catch (pErr) {
          // If JSON parse failed, could be an error or split token; do not crash entire generator
          if (pErr instanceof Error && pErr.message.includes('Server stream error')) {
            throw pErr;
          }
          console.debug('SSE JSON parse skipped for chunk:', rawData);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // Flush any remaining characters in decoder
          buffer += decoder.decode();
          if (buffer.trim()) {
            processLine(buffer);
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        // Handle both CRLF and LF
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || '';

        for (const line of lines) {
          processLine(line);
        }
      }

      return {
        answer: meta.answer || accumulated,
        sources: meta.sources || [],
        pages: meta.pages || [],
        sections: meta.sections || [],
        retrieved_chunks: [],
        web_sources: meta.web_sources || [],
        market_data: meta.market_data,
        conversationId: meta.conversationId,
      };
    } catch (streamErr: any) {
      // 1. If cancellation requested, never fall back to standard HTTP
      if (signal?.aborted || streamErr?.name === 'AbortError' || streamErr?.code === 'ERR_CANCELED') {
        throw streamErr;
      }

      // 2. If tokens were already received, do not fall back (prevents duplicate assistant text)
      if (accumulated && accumulated.length > 0) {
        console.warn('Stream interrupted after receiving tokens, returning accumulated output:', streamErr);
        return {
          answer: meta.answer || accumulated,
          sources: meta.sources || [],
          pages: meta.pages || [],
          sections: meta.sections || [],
          retrieved_chunks: [],
          web_sources: meta.web_sources || [],
          market_data: meta.market_data,
          conversationId: meta.conversationId,
        };
      }

      // 3. Seamlessly fallback to standard HTTP if stream failed before any tokens
      console.warn('Stream failed before any tokens received, falling back to standard endpoint:', streamErr);
      return await this.sendChat(payload, signal);
    }
  },

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

export default chatService;
