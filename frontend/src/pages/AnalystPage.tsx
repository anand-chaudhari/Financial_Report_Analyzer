import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import { chatService, WebSourceItem } from '../services/chatService';
import {
  conversationService,
  ConversationItem,
  SourceMetadata,
} from '../services/conversationService';
import { PdfSplitViewer } from '../components/pdf/PdfSplitViewer';
import { exportToExcel, exportToPdfBrief, exportToPresentationDeck } from '../services/exportService';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { RenameModal } from '../components/common/RenameModal';
import {
  UserMessage,
  AssistantMessage,
} from '../components/chat';
import {
  Bot,
  Send,
  UploadCloud,
  FileCheck,
  RefreshCw,
  Trash2,
  BookOpen,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  MessageSquare,
  Plus,
  Edit3,
  Square,
  Download,
  FileSpreadsheet,
  Printer,
  Presentation,
  Columns,
  Globe,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  X,
  Sparkles,
  CornerDownLeft,
  Search,
} from 'lucide-react';

export interface MessageUIItem {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  pages?: number[];
  sections?: string[];
  sources?: SourceMetadata[];
  web_sources?: WebSourceItem[];
  market_data?: Record<string, any>;
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
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [messages, setMessages] = useState<MessageUIItem[]>([]);
  const [isPdfSplitOpen, setIsPdfSplitOpen] = useState<boolean>(false);
  const [splitHighlightSource, setSplitHighlightSource] = useState<SourceMetadata | null>(null);
  const [showExportMenu, setShowExportMenu] = useState<boolean>(false);
  const [searchMode, setSearchMode] = useState<'auto' | 'on' | 'off' | 'web_only'>('auto');

  // Sidebar Layout State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);

  // Modals state
  const [activeSourceModal, setActiveSourceModal] = useState<SourceMetadata | null>(null);
  const [editingConvModal, setEditingConvModal] = useState<ConversationItem | null>(null);
  const [confirmModalState, setConfirmModalState] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    targetId?: string;
    isThreadClear?: boolean;
  }>({
    isOpen: false,
    title: '',
    description: '',
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const skipNextHistoryLoadRef = useRef<boolean>(false);

  // Ensure active report is identified
  useEffect(() => {
    if (!selectedReportId && reports.length > 0) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  const activeReport = reports.find(
    (r) => r.id === selectedReportId || r.documentId === selectedReportId
  );

  // Clean up any streaming generator on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  const handleOpenSourceCitation = (s: SourceMetadata) => {
    setSplitHighlightSource(s);
    setIsPdfSplitOpen(true);
    setActiveSourceModal(s);
  };

  const handleStopResponse = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsGenerating(false);
  };

  // Load User Conversations for selected report
  const loadConversations = useCallback(async () => {
    if (!selectedReportId) return;
    try {
      const list = await conversationService.getConversations(selectedReportId);
      setConversations(list);

      if (convIdParam && !activeConversationId) {
        const match = list.find((c) => c.conversationId === convIdParam);
        if (match) {
          setActiveConversationId(match.conversationId);
        }
      }
    } catch (err) {
      console.warn('Could not load conversations:', err);
    }
  }, [selectedReportId, convIdParam, activeConversationId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load messages when activeConversationId changes
  const loadConversationMessages = useCallback(
    async (convId: string) => {
      setIsLoadingHistory(true);
      try {
        const conv = await conversationService.getConversation(convId);
        if (conv && conv.messages) {
          const mapped: MessageUIItem[] = conv.messages.map((m) => ({
            id: m.messageId,
            sender: m.role as 'user' | 'assistant',
            text: m.content,
            timestamp: new Date(m.createdAt).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            }),
            sources: m.sources,
            pages: m.sources ? Array.from(new Set(m.sources.map((s) => s.page_number))) : [],
            sections: m.sources ? Array.from(new Set(m.sources.map((s) => s.section))) : [],
          }));
          setMessages(mapped);
        } else {
          setMessages([]);
        }
      } catch (err: any) {
        console.warn('Error loading conversation messages:', err);
        if (err?.response?.status === 404) {
          setActiveConversationId(null);
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.delete('conv');
            return next;
          });
          setMessages([]);
        }
      } finally {
        setIsLoadingHistory(false);
      }
    },
    [setSearchParams]
  );

  useEffect(() => {
    if (!activeConversationId) return;
    if (skipNextHistoryLoadRef.current || isGenerating) {
      skipNextHistoryLoadRef.current = false;
      return;
    }
    loadConversationMessages(activeConversationId);
  }, [activeConversationId, isGenerating, loadConversationMessages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const suggestedQuestions = [
    "What was the company's total revenue?",
    "What was the net profit and operating margin?",
    "What were the major operational and financial risks?",
    "Summarize the management discussion & analysis (MD&A).",
    "Why did expenses increase year-over-year?",
    "What are the key balance sheet and cash flow highlights?",
  ];

  const handleStartNewConversation = () => {
    skipNextHistoryLoadRef.current = false;
    setActiveConversationId(null);
    setMessages([]);
    setIsMobileSidebarOpen(false);
    setSearchParams(selectedReportId ? { doc: selectedReportId } : {});
  };

  const handleSelectConversation = (conv: ConversationItem) => {
    skipNextHistoryLoadRef.current = false;
    setActiveConversationId(conv.conversationId);
    if (conv.documentId) {
      setSelectedReportId(conv.documentId);
    }
    setIsMobileSidebarOpen(false);
    setSearchParams({ doc: conv.documentId || selectedReportId, conv: conv.conversationId });
  };

  const handleSendQuery = async (promptText: string) => {
    if (!promptText.trim() || isGenerating) return;

    skipNextHistoryLoadRef.current = true;
    const userPrompt = promptText.trim();

    const userMsg: MessageUIItem = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: userPrompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const assistantMsgId = `ai_${Date.now()}`;
    const initialAiMsg: MessageUIItem = {
      id: assistantMsgId,
      sender: 'assistant',
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      sources: [],
      pages: [],
      sections: [],
    };

    setMessages((prev) => [...prev, userMsg, initialAiMsg]);
    setQueryText('');
    setIsGenerating(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const historyForBackend = messages.slice(-6).map((m) => ({
        sender: m.sender,
        text: m.text,
      }));

      const fileName = activeReport?.fileName || activeReport?.filename || 'Financial_Report.pdf';

      const isExplicitWebOnly =
        searchMode === 'web_only' ||
        Boolean(userPrompt.toLowerCase().includes('@websearch') || userPrompt.toLowerCase().includes('@web'));
      const effectiveSearchMode: 'auto' | 'on' | 'off' | 'web_only' = isExplicitWebOnly ? 'web_only' : searchMode;

      const resData = await chatService.streamChat(
        {
          conversation_id: activeConversationId || undefined,
          document_id: selectedReportId || activeReport?.id || activeReport?.documentId || 'doc_unknown',
          question: userPrompt,
          conversation_history: historyForBackend,
          search_mode: effectiveSearchMode,
          use_web_search: effectiveSearchMode === 'on' || effectiveSearchMode === 'web_only',
        },
        (_token, accumulated) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantMsgId ? { ...m, text: accumulated } : m))
          );
        },
        (meta) => {
          if (meta.conversationId && !activeConversationId) {
            setActiveConversationId(meta.conversationId);
            setSearchParams({ doc: selectedReportId, conv: meta.conversationId });
          }

          const pageList = meta.pages || [];
          const sectionList = meta.sections || [];
          const structuredSources: SourceMetadata[] = [];
          pageList.forEach((pg, idx) => {
            structuredSources.push({
              page_number: pg,
              section: sectionList[idx] || sectionList[0] || 'Report Section',
              document_name: fileName,
              snippet: meta.sources?.[idx] || '',
            });
          });

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    sources: structuredSources.length > 0 ? structuredSources : m.sources,
                    pages: pageList.length > 0 ? pageList : m.pages,
                    sections: sectionList.length > 0 ? sectionList : m.sections,
                    web_sources: meta.web_sources || m.web_sources,
                    market_data: meta.market_data || m.market_data,
                  }
                : m
            )
          );
        },
        controller.signal
      );

      if (resData) {
        const newConvId = resData.conversationId || activeConversationId;
        if (newConvId && activeConversationId !== newConvId) {
          setActiveConversationId(newConvId);
          setSearchParams({ doc: selectedReportId, conv: newConvId });
        }

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

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  text: resData.answer || m.text,
                  sources: structuredSources.length > 0 ? structuredSources : m.sources,
                  pages: pageList.length > 0 ? pageList : m.pages,
                  sections: sectionList.length > 0 ? sectionList : m.sections,
                  web_sources: resData.web_sources || m.web_sources,
                  market_data: resData.market_data || m.market_data,
                }
              : m
          )
        );
        setIsGenerating(false);
        abortControllerRef.current = null;
        await loadConversations();
      }
    } catch (err: any) {
      abortControllerRef.current = null;
      setIsGenerating(false);
      if (err?.name === 'CanceledError' || err?.name === 'AbortError' || err?.code === 'ERR_CANCELED') {
        console.log('Response generation cancelled by user.');
        return;
      }
      console.error('Chat error:', err);
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id === assistantMsgId && !m.text.trim()) {
            return {
              ...m,
              text: `⚠️ I encountered a temporary issue generating an answer. Please retry or adjust your question.\n\n*Error details: ${
                err?.response?.data?.detail || err?.message || 'Network connection interrupted.'
              }*`,
            };
          }
          return m;
        })
      );
    }
  };

  const handleRegenerate = () => {
    const lastUserMessage = [...messages].reverse().find((m) => m.sender === 'user');
    if (lastUserMessage) {
      handleSendQuery(lastUserMessage.text);
    }
  };

  // Delete Handlers with Confirmation Modals
  const promptDeleteConversation = (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmModalState({
      isOpen: true,
      title: 'Delete Conversation Thread',
      description: 'Are you sure you want to delete this analyst conversation? All messages, citations, and questions in this thread will be permanently removed.',
      targetId: convId,
      isThreadClear: false,
    });
  };

  const promptClearCurrentThread = () => {
    setConfirmModalState({
      isOpen: true,
      title: 'Clear Current Conversation',
      description: 'Are you sure you want to clear the active conversation? This will delete the thread from your history.',
      targetId: activeConversationId || undefined,
      isThreadClear: true,
    });
  };

  const handleConfirmDelete = async () => {
    const targetId = confirmModalState.targetId;
    setConfirmModalState({ isOpen: false, title: '', description: '' });

    if (targetId) {
      await conversationService.deleteConversation(targetId);
      await loadConversations();
      if (activeConversationId === targetId) {
        handleStartNewConversation();
      }
    } else {
      setMessages([]);
    }
  };

  const handleRenameConvSubmit = async (newName: string) => {
    if (editingConvModal && newName.trim()) {
      await conversationService.renameConversation(editingConvModal.conversationId, newName.trim());
      setEditingConvModal(null);
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
    const val = e.target.value;
    setQueryText(val);
    if ((val.toLowerCase().includes('@websearch') || val.toLowerCase().includes('@web')) && searchMode !== 'web_only') {
      setSearchMode('web_only');
    }
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  const sanitizeMeta = (val: any): string => {
    if (!val) return '';
    const s = String(val);
    return s.replace(/^\{\(?|\)?\,?\}$/g, '').replace(/^["']|["']$/g, '').trim();
  };

  const reportTitle = sanitizeMeta(
    activeReport?.companyName || activeReport?.company_name || activeReport?.filename || 'Financial Report'
  );

  return (
    <div className="flex flex-col lg:flex-row gap-5 max-w-7xl mx-auto w-full min-w-0 pb-6 animate-fade-in relative">
      {/* MOBILE SIDEBAR BACKDROP */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-xs lg:hidden animate-fade-in"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* LEFT SIDEBAR: Report Card, History & Navigation */}
      <div
        className={`fixed lg:static top-0 bottom-0 left-0 z-40 lg:z-auto w-80 max-w-[85vw] lg:max-w-none bg-white dark:bg-slate-900 lg:bg-transparent p-5 lg:p-0 shadow-2xl lg:shadow-none flex flex-col space-y-4 overflow-y-auto transition-transform duration-300 ease-in-out ${
          isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        } ${isSidebarCollapsed ? 'lg:hidden' : 'lg:flex lg:w-80 flex-shrink-0'}`}
      >
        {/* Mobile Header Close */}
        <div className="flex lg:hidden items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-emerald-500" />
            <span className="font-extrabold text-sm text-slate-900 dark:text-white">Workspace Sidebar</span>
          </div>
          <button
            onClick={() => setIsMobileSidebarOpen(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Selected Report Card */}
        <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-extrabold text-slate-900 dark:text-white tracking-tight">
                  Target Report
                </h2>
                <p className="text-[11px] text-slate-500">Selected Filing Context</p>
              </div>
            </div>
            <button
              onClick={() => setIsSidebarCollapsed(true)}
              className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              title="Collapse sidebar to maximize chat"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* Report Dropdown Selector */}
          <div className="space-y-1.5">
            {reports.length > 0 ? (
              <select
                value={selectedReportId}
                onChange={(e) => {
                  setSelectedReportId(e.target.value);
                  handleStartNewConversation();
                }}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs font-bold text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 truncate cursor-pointer shadow-xs"
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
              <div className="flex justify-between items-start gap-2">
                <span className="text-slate-500 text-[11px] flex-shrink-0">Company:</span>
                <span
                  className="font-bold text-slate-900 dark:text-white text-right text-[11px] leading-snug"
                  title={reportTitle}
                >
                  {reportTitle}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 text-[11px]">Fiscal Period:</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {sanitizeMeta(activeReport.financialYear || activeReport.fiscal_period || 'Annual Report')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 text-[11px]">Page Count:</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  {activeReport.pageCount || activeReport.total_pages || 'Complete'} Pages
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 text-[11px]">Analysis Status:</span>
                <span className="inline-flex items-center gap-1 font-bold text-emerald-500 text-[10px] uppercase">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  100% Indexed
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Conversation History Section */}
        <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3 flex-1 flex flex-col min-h-[280px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-emerald-500" />
              <h3 className="text-xs font-extrabold text-slate-900 dark:text-white uppercase tracking-wider">
                Analyst History
              </h3>
            </div>
            <button
              onClick={handleStartNewConversation}
              className="px-2.5 py-1 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Chat</span>
            </button>
          </div>

          <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1 flex-1">
            {conversations.length > 0 ? (
              conversations.map((c) => {
                const isActive = c.conversationId === activeConversationId;
                return (
                  <div
                    key={c.conversationId}
                    onClick={() => handleSelectConversation(c)}
                    className={`p-3 rounded-2xl border text-xs transition-all cursor-pointer flex items-center justify-between group relative overflow-hidden ${
                      isActive
                        ? 'bg-emerald-500/15 border-2 border-emerald-500 text-emerald-950 dark:text-emerald-100 font-extrabold shadow-xs'
                        : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 hover:border-slate-300 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="min-w-0 pr-2 space-y-1">
                      <div className="flex items-center gap-1.5">
                        <p className="truncate text-xs font-bold">{c.title || 'Analysis Thread'}</p>
                        {isActive && (
                          <span className="px-1.5 py-0.2 rounded-full bg-emerald-600 text-white text-[9px] font-black uppercase tracking-wider flex-shrink-0">
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-slate-400 font-normal">
                        {new Date(c.updatedAt).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingConvModal(c);
                        }}
                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-white cursor-pointer"
                        title="Rename conversation"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => promptDeleteConversation(c.conversationId, e)}
                        className="p-1 text-slate-400 hover:text-rose-500 cursor-pointer"
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
      </div>

      {/* CENTER / MAIN CHAT WORKSPACE */}
      <div className="flex-1 flex flex-col min-w-0 space-y-4">
        {/* Main Chat Header */}
        <div className="p-3.5 sm:p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            {/* Mobile Sidebar Hamburger Button */}
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 cursor-pointer flex-shrink-0"
              title="Open Reports & History Drawer"
            >
              <Menu className="w-4 h-4" />
            </button>

            {/* Desktop Expand Sidebar button if collapsed */}
            {isSidebarCollapsed && (
              <button
                onClick={() => setIsSidebarCollapsed(false)}
                className="hidden lg:flex p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 cursor-pointer flex-shrink-0"
                title="Expand reports sidebar"
              >
                <PanelLeftOpen className="w-4 h-4" />
              </button>
            )}

            <div className="p-2 sm:p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex-shrink-0">
              <Bot className="w-5 h-5" />
            </div>

            <div className="min-w-0">
              <h1 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white tracking-tight truncate">
                AI Financial Analyst
              </h1>
              <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 truncate">
                {activeConversationId ? 'Active analysis thread' : 'New Q&A Session'} • {reportTitle}
              </p>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            {/* Split PDF Viewer Toggle Button */}
            <button
              onClick={() => setIsPdfSplitOpen(!isPdfSplitOpen)}
              className={`px-2.5 sm:px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                isPdfSplitOpen
                  ? 'bg-emerald-500 text-slate-950 border-emerald-400 font-extrabold shadow-xs'
                  : 'bg-slate-100 dark:bg-slate-800 hover:bg-emerald-500/10 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
              }`}
              title="Toggle Live In-Document PDF Split View"
            >
              <Columns className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{isPdfSplitOpen ? 'Hide PDF' : 'PDF Split View'}</span>
            </button>

            {/* Export Suite Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="px-2.5 sm:px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-emerald-500/10 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
                title="Institutional Export Suite"
              >
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Export</span>
                <ChevronDown className="w-3 h-3 text-slate-400" />
              </button>

              {showExportMenu && (
                <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl py-2 z-50 animate-fade-in text-xs">
                  <button
                    onClick={() => {
                      setShowExportMenu(false);
                      exportToExcel({
                        companyName: activeReport?.companyName || 'Corporate Filing',
                        financialYear: activeReport?.financialYear || 'FY2026',
                        conversationHistory: messages.map((m) => ({
                          role: m.sender,
                          content: m.text,
                          sources: m.sources,
                        })),
                      });
                    }}
                    className="w-full px-4 py-2.5 text-left text-slate-700 dark:text-slate-200 hover:bg-emerald-500/10 hover:text-emerald-600 flex items-center gap-2 font-medium cursor-pointer"
                  >
                    <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
                    <span>Export Excel Model (.csv)</span>
                  </button>

                  <button
                    onClick={() => {
                      setShowExportMenu(false);
                      exportToPdfBrief({
                        companyName: activeReport?.companyName || 'Corporate Filing',
                        financialYear: activeReport?.financialYear || 'FY2026',
                        summaryText: messages.find((m) => m.sender === 'assistant')?.text || '',
                        conversationHistory: messages.map((m) => ({
                          role: m.sender,
                          content: m.text,
                          sources: m.sources,
                        })),
                      });
                    }}
                    className="w-full px-4 py-2.5 text-left text-slate-700 dark:text-slate-200 hover:bg-blue-500/10 hover:text-blue-600 flex items-center gap-2 font-medium cursor-pointer"
                  >
                    <Printer className="w-4 h-4 text-blue-500" />
                    <span>CFO Executive Brief (PDF)</span>
                  </button>

                  <button
                    onClick={() => {
                      setShowExportMenu(false);
                      exportToPresentationDeck({
                        companyName: activeReport?.companyName || 'Corporate Filing',
                        financialYear: activeReport?.financialYear || 'FY2026',
                        summaryText: messages.find((m) => m.sender === 'assistant')?.text || '',
                      });
                    }}
                    className="w-full px-4 py-2.5 text-left text-slate-700 dark:text-slate-200 hover:bg-purple-500/10 hover:text-purple-600 flex items-center gap-2 font-medium cursor-pointer"
                  >
                    <Presentation className="w-4 h-4 text-purple-500" />
                    <span>Board Slide Deck (.json)</span>
                  </button>
                </div>
              )}
            </div>

            {/* Clear / Delete Current Thread Button */}
            {messages.length > 0 && (
              <button
                onClick={promptClearCurrentThread}
                className="px-2.5 sm:px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-rose-500/10 text-slate-600 dark:text-slate-300 hover:text-rose-600 border border-slate-200 dark:border-slate-700 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
                title="Clear current conversation"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Delete Thread</span>
              </button>
            )}
          </div>
        </div>

        {/* Live Side-by-Side Area (Chat Stream + Optional PDF Viewer) */}
        <div className="flex flex-col lg:flex-row gap-4 min-h-[480px] items-stretch flex-1">
          {/* Main Message Stream Column */}
          <div className="flex-1 flex flex-col min-w-0 space-y-4">
            {/* Message Stream Scroll Area */}
            <div className="flex-1 min-h-[460px] max-h-[640px] overflow-y-auto p-4 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
              {messages.length > 0 ? (
                messages.map((msg, index) => {
                  const isLast = index === messages.length - 1;
                  if (msg.sender === 'user') {
                    return (
                      <UserMessage
                        key={msg.id}
                        id={msg.id}
                        text={msg.text}
                        timestamp={msg.timestamp}
                      />
                    );
                  }
                  return (
                    <AssistantMessage
                      key={msg.id}
                      id={msg.id}
                      text={msg.text}
                      timestamp={msg.timestamp}
                      sources={msg.sources}
                      web_sources={msg.web_sources}
                      market_data={msg.market_data}
                      isGenerating={isGenerating}
                      isLastAssistant={isLast}
                      onOpenPdfCitation={handleOpenSourceCitation}
                      onRegenerate={handleRegenerate}
                      onStop={handleStopResponse}
                    />
                  );
                })
              ) : (
                /* Empty Chat Welcome State with Interactive Prompts */
                <div className="py-12 sm:py-16 text-center space-y-4 max-w-xl mx-auto animate-fade-in">
                  <div className="w-14 h-14 rounded-3xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/20 shadow-sm">
                    <Bot className="w-7 h-7" />
                  </div>
                  <div>
                    <h2 className="text-base sm:text-lg font-black text-slate-900 dark:text-white">
                      FinSight AI Financial Analyst
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto leading-relaxed">
                      Ask any targeted financial, strategic, or regulatory question regarding{' '}
                      <strong className="text-slate-800 dark:text-slate-200">{reportTitle}</strong>.
                      Answers are strictly grounded with page-level citations.
                    </p>
                  </div>

                  <div className="pt-3 text-left space-y-2">
                    <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5 px-1">
                      <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Suggested Prompts for this filing:</span>
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {suggestedQuestions.map((q, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendQuery(q)}
                          className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 hover:bg-emerald-500/10 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/30 text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-all text-left cursor-pointer flex items-center justify-between group shadow-2xs"
                        >
                          <span className="truncate pr-1">{q}</span>
                          <Send className="w-3 h-3 text-slate-400 group-hover:text-emerald-500 flex-shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* ANCHORED CHAT COMPOSER */}
            <div className="p-3 sm:p-4 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-lg space-y-2.5">
              {/* Search Mode Pill Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                <div className="flex items-center gap-1 p-1 rounded-2xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 shadow-xs">
                  <div className="flex items-center gap-1 px-2 text-[11px] font-bold text-slate-500 dark:text-slate-400">
                    <Globe className="w-3.5 h-3.5 text-blue-500" />
                    <span>Search Mode:</span>
                  </div>

                  {/* AUTO Mode (Default) */}
                  <button
                    type="button"
                    onClick={() => setSearchMode('auto')}
                    className={`px-2.5 py-1 rounded-xl text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                      searchMode === 'auto'
                        ? 'bg-emerald-600 text-white shadow-xs shadow-emerald-500/25 ring-1 ring-emerald-500'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                    title="Automatic: Intelligently detects market quotes & live financial events when needed."
                  >
                    <span>⚡ Auto</span>
                  </button>

                  {/* ON Mode */}
                  <button
                    type="button"
                    onClick={() => setSearchMode('on')}
                    className={`px-2.5 py-1 rounded-xl text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                      searchMode === 'on'
                        ? 'bg-blue-600 text-white shadow-xs shadow-blue-500/25 ring-1 ring-blue-500'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                    title="Always ON: Forces live web discovery and external source verification."
                  >
                    <span>🌐 On</span>
                  </button>

                  {/* OFF Mode */}
                  <button
                    type="button"
                    onClick={() => setSearchMode('off')}
                    className={`px-2.5 py-1 rounded-xl text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                      searchMode === 'off'
                        ? 'bg-slate-700 text-white shadow-xs ring-1 ring-slate-600'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                    title="Strictly OFF: RAG answers strictly from uploaded document filing."
                  >
                    <span>🔒 Off</span>
                  </button>

                  {/* WEB SEARCH ONLY Mode (@websearch) */}
                  <button
                    type="button"
                    onClick={() => {
                      setSearchMode('web_only');
                      if (!queryText.toLowerCase().includes('@websearch')) {
                        setQueryText((prev) => `@websearch ${prev.replace(/@websearch\s*/gi, '').trim()}`.trimStart());
                      }
                      if (textareaRef.current) textareaRef.current.focus();
                    }}
                    className={`px-2.5 py-1 rounded-xl text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                      searchMode === 'web_only'
                        ? 'bg-purple-600 text-white shadow-xs shadow-purple-500/25 ring-1 ring-purple-500'
                        : 'text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 hover:bg-purple-500/10'
                    }`}
                    title="@websearch Mode: Bypasses local PDF RAG and answers exclusively using live AI + Web Search."
                  >
                    <span>🚀 @websearch</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 hidden lg:inline font-medium">
                    {searchMode === 'auto' && '⚡ Auto: Automatically detects market quotes & live financial news'}
                    {searchMode === 'on' && '🌐 On: External web search enabled for this turn'}
                    {searchMode === 'off' && '🔒 Off: Document-only mode; web discovery disabled'}
                    {searchMode === 'web_only' && '🚀 @websearch: Local RAG bypassed; responses generated exclusively via live web search'}
                  </span>

                  {searchMode !== 'web_only' && !queryText.toLowerCase().includes('@websearch') && (
                    <button
                      type="button"
                      onClick={() => {
                        setSearchMode('web_only');
                        setQueryText((prev) => `@websearch ${prev}`.trimStart());
                        if (textareaRef.current) textareaRef.current.focus();
                      }}
                      className="px-2 py-0.5 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/60 border border-purple-200 dark:border-purple-800/80 text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer"
                      title="Click to insert @websearch into prompt"
                    >
                      <Sparkles className="w-2.5 h-2.5" />
                      <span>Use @websearch</span>
                    </button>
                  )}
                </div>
              </div>

              {/* @websearch Active Notice Badge */}
              {(searchMode === 'web_only' || queryText.toLowerCase().includes('@websearch')) && (
                <div className="flex items-center justify-between px-3 py-1.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-700 dark:text-purple-300 text-xs font-semibold animate-fade-in">
                  <div className="flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 animate-pulse" />
                    <span><strong>@websearch Mode Active:</strong> Answers exclusively using live AI + Web Search (Local PDF RAG is bypassed).</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSearchMode('auto');
                      setQueryText((prev) => prev.replace(/@websearch\s*/gi, '').replace(/@web\s*/gi, '').trim());
                    }}
                    className="text-[10px] text-purple-600 dark:text-purple-400 hover:underline cursor-pointer font-bold"
                  >
                    Switch to Auto
                  </button>
                </div>
              )}

              {/* Multiline Input & Solid Action Button */}
              <div className="flex items-end gap-2.5">
                <div className="flex-1 min-w-0">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    placeholder={
                      searchMode === 'web_only' || queryText.toLowerCase().includes('@websearch')
                        ? 'Web Search Mode active: Ask any company, live stock quote, or market question...'
                        : selectedReportId
                        ? `Ask a financial question about ${reportTitle}... (or type @websearch for web search)`
                        : 'Upload or select a report to begin analysis... (or type @websearch to search web)'
                    }
                    value={queryText}
                    onChange={handleTextareaInput}
                    onKeyDown={handleTextareaKeyDown}
                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl text-xs sm:text-sm font-medium text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all resize-none min-h-[46px]"
                  />
                </div>

                {isGenerating ? (
                  <button
                    type="button"
                    onClick={handleStopResponse}
                    className="px-4 sm:px-5 py-3 rounded-2xl bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-rose-600/20 flex-shrink-0 h-[46px]"
                    title="Stop generating response"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                    <span>Stop</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleSendQuery(queryText)}
                    disabled={!queryText.trim()}
                    className="px-4 sm:px-5 py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:opacity-60 text-white font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-emerald-600/20 flex-shrink-0 h-[46px]"
                    title="Send message (Enter)"
                  >
                    <span>Send</span>
                    <Send className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Bottom Instructions / Disclaimer */}
              <div className="flex items-center justify-between px-2 text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                  <CornerDownLeft className="w-3 h-3" /> Press Enter to send, Shift+Enter for new line
                </span>
                <span className="hidden sm:inline">Grounded AI Analysis • Page Citations • Type @websearch for Web-Only Search</span>
              </div>
            </div>
          </div>

          {/* Right Panel: Interactive PDF Split View */}
          {isPdfSplitOpen && (
            <PdfSplitViewer
              documentId={activeReport?.id || ''}
              fileName={activeReport?.fileName || activeReport?.companyName || 'Financial Filing.pdf'}
              storageUrl={activeReport?.storageUrl}
              highlightSource={splitHighlightSource}
              onClose={() => setIsPdfSplitOpen(false)}
            />
          )}
        </div>
      </div>

      {/* CONFIRM DELETE MODAL */}
      <ConfirmModal
        isOpen={confirmModalState.isOpen}
        title={confirmModalState.title}
        description={confirmModalState.description}
        confirmLabel="Delete Thread"
        cancelLabel="Keep Conversation"
        isDanger={true}
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmModalState({ isOpen: false, title: '', description: '' })}
      />

      {/* RENAME CONVERSATION MODAL */}
      {editingConvModal && (
        <RenameModal
          isOpen={Boolean(editingConvModal)}
          initialName={editingConvModal.title || ''}
          onConfirm={handleRenameConvSubmit}
          onClose={() => setEditingConvModal(null)}
        />
      )}

      {/* SOURCE CITATION DETAIL MODAL (Fallback preview) */}
      {activeSourceModal && !isPdfSplitOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs animate-fade-in">
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
                <span>
                  Section: <strong className="text-slate-900 dark:text-white">{activeSourceModal.section}</strong>
                </span>
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

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setActiveSourceModal(null);
                  setIsPdfSplitOpen(true);
                }}
                className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-bold text-xs cursor-pointer"
              >
                Open in Split View
              </button>
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
    </div>
  );
};

export default AnalystPage;
