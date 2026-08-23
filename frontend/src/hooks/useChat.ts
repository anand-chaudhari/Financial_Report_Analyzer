import { useState, useEffect, useCallback } from 'react';
import { ChatMessage, Citation } from '../types';
import { chatService } from '../services/chatService';

export const useChat = (reportId: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    if (!reportId) return;
    try {
      const response = await chatService.getHistory(reportId);
      if (response.success && response.data?.messages) {
        setMessages(response.data.messages);
      }
    } catch (err: any) {
      console.warn('Could not fetch chat history:', err);
    }
  }, [reportId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const sendQuery = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: ChatMessage = {
      sender: 'user',
      content: question,
      citations: [],
      is_grounded: true,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const response = await chatService.sendQuery({
        report_id: reportId,
        question,
      });

      if (response.success && response.data) {
        const assistantMsg: ChatMessage = {
          sender: 'assistant',
          content: response.data.answer,
          citations: response.data.citations || [],
          is_grounded: response.data.is_grounded,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to generate answer');
      const errorMsg: ChatMessage = {
        sender: 'system',
        content: 'Error: Could not retrieve answer from AI service. Please verify backend connection.',
        citations: [],
        is_grounded: false,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      await chatService.clearHistory(reportId);
      setMessages([]);
    } catch (err: any) {
      setError(err?.message || 'Failed to clear chat');
    }
  };

  return {
    messages,
    loading,
    error,
    sendQuery,
    clearChat,
    fetchHistory,
  };
};
