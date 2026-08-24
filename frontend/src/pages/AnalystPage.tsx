import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import { chatService } from '../services/chatService';
import { conversationService, ConversationItem, SourceMetadata } from '../services/conversationService';
import {
  Bot,
  Send,
  User,
  Sparkles,
  UploadCloud,
  CheckCircle2,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  AlertCircle,
  Eye,
  X,
  BookOpen,
  ChevronRight,
  ShieldCheck,
  Layers,
  Calendar,
  Building2,
  FileCheck,
  CornerDownLeft,
  MessageSquare,
  Plus,
  Edit3,
  Clock,
} from 'lucide-react';
import { formatBytes } from '../utils/formatters';

interface MessageUIItem {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  pages?: number[];
  sections?: string[];
  sources?: SourceMetadata[];
}

export const AnalystPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const docIdParam = searchParams.get('doc');
  const convIdParam = searchParams.get('conv');
  const { reports } = useReportContext();

  const [selectedReportId, setSelectedReportId] = useState<string>(docIdParam || (reports[0]?.id ?? ''));
  const [activeConversationId, setActiveConversationId] = useState<string | null>(convIdParam || null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [queryText, setQueryText] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageUIItem[]>([]);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [activeSourceModal, setActiveSourceModal] = useState<SourceMetadata | null>(null);

  // Rename Conversation Modal state
  const [editingConvModal, setEditingConvModal] = useState<ConversationItem | null>(null);
  const [editTitleInput, setEditTitleInput] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!selectedReportId && reports.length > 0) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  const activeReport = reports.find((r) => r.id === selectedReportId || r.documentId === selectedReportId);

  // Load User Conversations for selected report
  const loadConversations = useCallback(async () => {
    const list = await conversationService.getConversations(selectedReportId);
    setConversations(list);

    if (convIdParam && !activeConversationId) {
      const match = list.find((c) => c.conversationId === convIdParam);
      if (match) {
        setActiveConversationId(match.conversationId);
      }
    }
  }, [selectedReportId, convIdParam, activeConversationId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load messages when activeConversationId changes
  const loadConversationMessages = useCallback(async (convId: string) => {
    setLoading(true);
    setErrorState(null);
    try {
      const conv = await conversationService.getConversation(convId);
      if (conv && conv.messages) {
        const mapped: MessageUIItem[] = conv.messages.map((m) => ({
          id: m.messageId,
          sender: m.role as 'user' | 'assistant',
          text: m.content,
          timestamp: new Date(m.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          sources: m.sources,
          pages: m.sources ? Array.from(new Set(m.sources.map((s) => s.page_number))) : [],
          sections: m.sources ? Array.from(new Set(m.sources.map((s) => s.section))) : [],
        }));
        setMessages(mapped);
      }
    } catch (err: any) {
      console.warn('Error loading conversation messages:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeConversationId) {
      loadConversationMessages(activeConversationId);
    }
  }, [activeConversationId, loadConversationMessages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const suggestedQuestions = [
    "What was the company's revenue?",
    "What was the net profit?",
    "What were the major risks?",
    "Summarize the management discussion.",
    "Why did expenses increase?",
    "What are the key financial highlights?",
  ];

  const handleStartNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setErrorState(null);
    setSearchParams(selectedReportId ? { doc: selectedReportId } : {});
  };

  const handleSelectConversation = (conv: ConversationItem) => {
    setActiveConversationId(conv.conversationId);
    if (conv.documentId) {
      setSelectedReportId(conv.documentId);
    }
    setSearchParams({ doc: conv.documentId || selectedReportId, conv: conv.conversationId });
  };

  const handleSendQuery = async (promptText: string) => {
    if (!promptText.trim() || loading) return;

    setErrorState(null);
    const userPrompt = promptText.trim();

    const userMsg: MessageUIItem = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: userPrompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setQueryText('');
    setLoading(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const historyForBackend = messages.slice(-6).map((m) => ({
        sender: m.sender,
        text: m.text,
      }));

      // Live POST /api/chat call saving user question & AI response
      const resData = await chatService.sendChat({
        conversation_id: activeConversationId || undefined,
        document_id: selectedReportId || activeReport?.id || activeReport?.documentId || 'doc_unknown',
        question: userPrompt,
        conversation_history: historyForBackend,
      });

      if (resData && resData.answer) {
        if (resData.conversationId && !activeConversationId) {
          setActiveConversationId(resData.conversationId);
          setSearchParams({ doc: selectedReportId, conv: resData.conversationId });
        }

        const fileName = activeReport?.fileName || activeReport?.filename || 'Financial_Report.pdf';
        const pageList = resData.pages || [];
        const sectionList = resData.sections || [];
        const chunks = resData.retrieved_chunks || [];

        const structuredSources: SourceMetadata[] = [];

        if (chunks.length > 0) {
          chunks.forEach((c: any) => {
            structuredSources.push({
              page_number: c.page_number || 1,
              section: c.section || 'Financial Statement',
              document_name: c.file_name || fileName,
              snippet: c.text,
              similarity_score: c.similarity_score,
            });
          });
        } else if (pageList.length > 0) {
          pageList.forEach((pg, idx) => {
            structuredSources.push({
              page_number: pg,
              section: sectionList[idx] || sectionList[0] || 'Item 7. MD&A',
              document_name: fileName,
              snippet: resData.sources?.[idx] || '',
            });
          });
        }

        const aiMsg: MessageUIItem = {
          id: resData.messageId || `ai_${Date.now()}`,
          sender: 'assistant',
          text: resData.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          pages: pageList,
          sections: sectionList,
          sources: structuredSources,
        };

        setMessages((prev) => [...prev, aiMsg]);
        setLoading(false);
        await loadConversations();
      } else {
        throw new Error('Invalid response from AI Analyst service.');
      }
    } catch (err: any) {
      console.error('API /api/chat error:', err);
      setLoading(false);
      const errDetail = err?.response?.data?.detail || err?.message || 'Failed to connect to AI Analyst backend service.';
      setErrorState(errDetail);
    }
  };

  const handleCopyText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(id);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  const handleRegenerate = () => {
    const lastUserMessage = [...messages].reverse().find((m) => m.sender === 'user');
    if (lastUserMessage) {
      handleSendQuery(lastUserMessage.text);
    }
  };

  const handleClearConversation = async () => {
    if (activeConversationId) {
      await conversationService.deleteConversation(activeConversationId);
      await loadConversations();
      handleStartNewConversation();
    } else {
      setMessages([]);
      setErrorState(null);
    }
  };

  const handleDeleteConv = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await conversationService.deleteConversation(convId);
    await loadConversations();
    if (activeConversationId === convId) {
      handleStartNewConversation();
    }
  };

  const handleRenameConvSubmit = async () => {
    if (editingConvModal && editTitleInput.trim()) {
      await conversationService.renameConversation(editingConvModal.conversationId, editTitleInput.trim());
      setEditingConvModal(null);
      setEditTitleInput('');
      await loadConversations();
    }
  };

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendQuery(queryText);
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQueryText(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 max-w-7xl mx-auto w-full min-w-0 pb-6 animate-fade-in">
      {/* LEFT PANEL: Report Details & Persistent Conversation History */}
      <div className="w-full lg:w-80 flex-shrink-0 space-y-4">
        {/* Selected Report Card */}
        <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-slate-900 dark:text-white tracking-tight">
                Target Report
              </h2>
              <p className="text-[11px] text-slate-500">Selected Filing Metadata</p>
            </div>
          </div>

          {/* Selector */}
          <div className="space-y-1.5">
            {reports.length > 0 ? (
              <select
                value={selectedReportId}
                onChange={(e) => {
                  setSelectedReportId(e.target.value);
                  handleStartNewConversation();
                }}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs font-bold text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 truncate cursor-pointer shadow-sm"
              >
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.companyName || r.company_name || r.filename} ({r.financialYear || r.fiscal_period || 'PDF'})
                  </option>
                ))}
              </select>
            ) : (
              <button
                onClick={() => navigate('/upload')}
                className="w-full px-4 py-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-colors"
              >
                <UploadCloud className="w-4 h-4" />
                <span>Upload PDF Filing</span>
              </button>
            )}
          </div>

          {activeReport && (
            <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500 text-[11px]">Company:</span>
                <span className="font-bold text-slate-900 dark:text-white truncate max-w-[130px]">
                  {activeReport.companyName || activeReport.company_name}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 text-[11px]">Fiscal Period:</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {activeReport.financialYear || activeReport.fiscal_period}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 text-[11px]">Page Count:</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  {activeReport.pageCount || activeReport.total_pages} Pages
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 text-[11px]">Analysis Status:</span>
                <span className="font-bold text-emerald-500 text-[10px] uppercase">100% Indexed</span>
              </div>
            </div>
          )}
        </div>

        {/* Conversation History Sidebar */}
        <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-emerald-500" />
              <h3 className="text-xs font-extrabold text-slate-900 dark:text-white uppercase tracking-wider">
                Analyst History
              </h3>
            </div>
            <button
              onClick={handleStartNewConversation}
              className="px-2.5 py-1 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Chat</span>
            </button>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {conversations.length > 0 ? (
              conversations.map((c) => {
                const isActive = c.conversationId === activeConversationId;
                return (
                  <div
                    key={c.conversationId}
                    onClick={() => handleSelectConversation(c)}
                    className={`p-3 rounded-2xl border text-xs transition-all cursor-pointer flex items-center justify-between group ${
                      isActive
                        ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-300 font-bold'
                        : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 hover:border-slate-300 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="min-w-0 pr-2 space-y-0.5">
                      <p className="truncate text-xs font-semibold">{c.title}</p>
                      <p className="text-[10px] text-slate-400 font-normal">
                        {new Date(c.updatedAt).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingConvModal(c);
                          setEditTitleInput(c.title);
                        }}
                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-white"
                        title="Rename conversation"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteConv(c.conversationId, e)}
                        className="p-1 text-slate-400 hover:text-rose-500"
                        title="Delete conversation"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-4 text-center text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
                No past conversations for this report. Ask a question below to start!
              </div>
            )}
          </div>
        </div>

        {/* Suggested Prompts */}
        <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
            <span>Suggested Prompts</span>
          </div>
          <div className="space-y-1.5">
            {suggestedQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSendQuery(q)}
                className="w-full p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 hover:bg-emerald-500/10 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/30 text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-all text-left flex items-center justify-between group cursor-pointer"
              >
                <span className="line-clamp-2">{q}</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-500 flex-shrink-0 ml-1" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* CENTER PANEL: Conversation Stream & Output Area */}
      <div className="flex-1 flex flex-col min-w-0 space-y-4">
        {/* Top Header & Actions Bar */}
        <div className="p-4 sm:p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex-shrink-0">
              <Bot className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-base font-extrabold text-slate-900 dark:text-white tracking-tight truncate">
                AI Financial Analyst
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                {activeConversationId ? 'Continuing analysis thread' : 'New Analysis Thread'} • Grounded Q&A
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {messages.length > 0 && (
              <button
                onClick={handleClearConversation}
                className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-rose-500/10 text-slate-600 dark:text-slate-300 hover:text-rose-600 border border-slate-200 dark:border-slate-700 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
                title="Clear current conversation"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Delete Thread</span>
              </button>
            )}
          </div>
        </div>

        {/* Conversation Message Stream */}
        <div className="flex-1 min-h-[460px] max-h-[620px] overflow-y-auto p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
          {messages.length > 0 ? (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3.5 max-w-3xl ${
                  msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''
                }`}
              >
                <div
                  className={`w-9 h-9 rounded-2xl flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-sm ${
                    msg.sender === 'user'
                      ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900'
                      : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                  }`}
                >
                  {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                <div
                  className={`p-4 sm:p-5 rounded-2xl text-xs space-y-3 leading-relaxed shadow-sm w-full min-w-0 ${
                    msg.sender === 'user'
                      ? 'bg-slate-900 dark:bg-slate-800 text-white rounded-tr-none max-w-xl ml-auto'
                      : 'bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none'
                  }`}
                >
                  {/* Message Body */}
                  <div className="whitespace-pre-wrap text-xs sm:text-sm font-normal">
                    {msg.text}
                  </div>

                  {/* AI Response Sources & Action Toolbar */}
                  {msg.sender === 'assistant' && (
                    <div className="pt-3 border-t border-slate-200/60 dark:border-slate-800/60 space-y-3">
                      {/* Clickable Source Cards */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-1">
                            <ShieldCheck className="w-3 h-3 text-emerald-500" />
                            <span>Verified Citations & Sources (Click to View Snippet):</span>
                          </span>

                          <div className="flex flex-wrap gap-2">
                            {msg.sources.map((src, idx) => (
                              <button
                                key={idx}
                                onClick={() => setActiveSourceModal(src)}
                                className="px-3 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 hover:bg-emerald-500/5 text-slate-700 dark:text-slate-300 transition-all text-[11px] font-semibold flex items-center gap-2 cursor-pointer shadow-sm group"
                              >
                                <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold text-[10px]">
                                  Page {src.page_number}
                                </span>
                                <span className="truncate max-w-[120px]">{src.section}</span>
                                <Eye className="w-3 h-3 text-slate-400 group-hover:text-emerald-500 flex-shrink-0" />
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Action Toolbar: Copy & Regenerate */}
                      <div className="flex items-center justify-between pt-1 text-[11px]">
                        <span className="text-slate-400 text-[10px]">{msg.timestamp}</span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleCopyText(msg.id, msg.text)}
                            className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 flex items-center gap-1 cursor-pointer transition-colors"
                            title="Copy formatted answer"
                          >
                            {copiedMsgId === msg.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-500" />
                                <span className="text-emerald-500 font-bold">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>

                          <button
                            onClick={handleRegenerate}
                            disabled={loading}
                            className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 flex items-center gap-1 cursor-pointer transition-colors disabled:opacity-50"
                            title="Regenerate AI answer"
                          >
                            <RefreshCw className="w-3 h-3" />
                            <span>Regenerate</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="py-20 text-center space-y-3">
              <Bot className="w-14 h-14 text-slate-300 dark:text-slate-700 mx-auto" />
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Start AI Financial Analysis
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Ask any question about your selected financial report. Questions, answers, and citations are saved to your analyst workspace.
              </p>
            </div>
          )}

          {/* Typing Indicator */}
          {loading && (
            <div className="flex gap-3 max-w-xl">
              <div className="w-9 h-9 rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center flex-shrink-0 border border-emerald-500/20">
                <Bot className="w-4 h-4 animate-pulse text-emerald-500" />
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-500 flex items-center gap-3">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  Analyzing report context & generating answer...
                </span>
              </div>
            </div>
          )}

          {/* Error State Display */}
          {errorState && (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{errorState}</span>
              </div>
              <button
                onClick={handleRegenerate}
                className="px-3 py-1 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-700 dark:text-rose-300 font-bold text-xs flex items-center gap-1 cursor-pointer transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry</span>
              </button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* BOTTOM PANEL: Multiline Input & Send Controls */}
        <div className="p-3 sm:p-4 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-lg space-y-2">
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder={
                selectedReportId
                  ? `Ask anything about ${activeReport?.companyName || activeReport?.company_name || 'this report'}...`
                  : 'Upload a financial report PDF to begin Q&A...'
              }
              value={queryText}
              onChange={handleTextareaInput}
              onKeyDown={handleTextareaKeyDown}
              className="flex-1 px-4 py-2.5 bg-transparent text-xs sm:text-sm font-medium text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none resize-none min-h-[44px]"
            />
            <button
              onClick={() => handleSendQuery(queryText)}
              disabled={!queryText.trim() || loading}
              className="px-5 py-3 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 disabled:opacity-40 text-white font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-emerald-500/20 flex-shrink-0 h-[44px]"
            >
              <span>Send</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center justify-between px-2 text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <CornerDownLeft className="w-3 h-3" /> Press Enter to send, Shift+Enter for new line
            </span>
            <span>Grounded AI Intelligence • Verified Page Citations</span>
          </div>
        </div>
      </div>

      {/* SOURCE CITATION MODAL */}
      {activeSourceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-2xl w-full shadow-2xl space-y-4 relative">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Verified Source Citation
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    {activeSourceModal.document_name} • Page {activeSourceModal.page_number}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setActiveSourceModal(null)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
              <div className="flex items-center justify-between text-slate-500 text-[11px]">
                <span>Section: <strong className="text-slate-900 dark:text-white">{activeSourceModal.section}</strong></span>
                {activeSourceModal.similarity_score !== undefined && (
                  <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 font-bold text-[10px]">
                    {(activeSourceModal.similarity_score * 100).toFixed(1)}% Match Score
                  </span>
                )}
              </div>

              <div className="p-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-200/60 dark:border-slate-800 text-slate-800 dark:text-slate-200 text-xs leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap font-mono">
                {activeSourceModal.snippet || 'Full extracted page text snippet available.'}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setActiveSourceModal(null)}
                className="px-4 py-2 rounded-xl bg-emerald-600 text-white font-bold text-xs cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RENAME CONVERSATION MODAL */}
      {editingConvModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4 relative">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Rename Conversation Thread
            </h3>
            <input
              type="text"
              value={editTitleInput}
              onChange={(e) => setEditTitleInput(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              placeholder="Enter new conversation title..."
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditingConvModal(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-semibold text-xs cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleRenameConvSubmit}
                disabled={!editTitleInput.trim()}
                className="px-4 py-2 rounded-xl bg-emerald-600 text-white font-bold text-xs cursor-pointer disabled:opacity-50"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
