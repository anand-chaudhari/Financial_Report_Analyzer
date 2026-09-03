import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import { chatService } from '../services/chatService';
import { conversationService, ConversationItem, SourceMetadata } from '../services/conversationService';
import { PdfSplitViewer } from '../components/pdf/PdfSplitViewer';
import { exportToExcel, exportToPdfBrief, exportToPresentationDeck } from '../services/exportService';
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
  Eye,
  X,
  BookOpen,
  ChevronRight,
  ChevronDown,
  ShieldCheck,
  FileCheck,
  CornerDownLeft,
  MessageSquare,
  Plus,
  Edit3,
  Square,
  FileText,
  Download,
  FileSpreadsheet,
  Printer,
  Presentation,
  Columns,
} from 'lucide-react';

interface MessageUIItem {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  pages?: number[];
  sections?: string[];
  sources?: SourceMetadata[];
}

/**
 * Deduplicates citations by page_number + section name
 */
const getDeduplicatedSources = (sources?: SourceMetadata[]): SourceMetadata[] => {
  if (!sources || sources.length === 0) return [];
  const seen = new Set<string>();
  const unique: SourceMetadata[] = [];

  for (const src of sources) {
    const page = src.page_number;
    const sec = (src.section || 'General Section').trim();
    const key = `${page}_${sec.toLowerCase()}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(src);
    }
  }
  return unique;
};

import { RichMarkdownRenderer } from '../components/common/RichMarkdownRenderer';

/**
 * Compact, collapsible Citations Accordion Component with deduplicated tags
 */
const CitationsAccordion: React.FC<{
  sources: SourceMetadata[];
  onOpenModal: (s: SourceMetadata) => void;
}> = ({ sources, onOpenModal }) => {
  const [expanded, setExpanded] = useState(true);
  const uniqueSources = getDeduplicatedSources(sources);

  if (uniqueSources.length === 0) return null;

  return (
    <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800/60 space-y-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-[10px] font-extrabold text-slate-500 dark:text-slate-400 uppercase tracking-wider hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors cursor-pointer"
      >
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span>Verified Citations ({uniqueSources.length})</span>
        </span>
        <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
          <span>{expanded ? 'Collapse' : 'Expand'}</span>
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </span>
      </button>

      {expanded && (
        <div className="flex flex-wrap gap-2 items-center animate-fade-in pt-1">
          {uniqueSources.map((src, idx) => (
            <button
              key={`${src.page_number}_${idx}`}
              onClick={() => onOpenModal(src)}
              className="px-2.5 py-1 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 hover:bg-emerald-500/5 text-slate-700 dark:text-slate-300 transition-all text-[11px] font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs group"
            >
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold text-[10px]">
                Page {src.page_number}
              </span>
              <span className="truncate max-w-[140px]">{src.section || 'Report Section'}</span>
              <Eye className="w-3 h-3 text-slate-400 group-hover:text-emerald-500 flex-shrink-0" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

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
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [activeSourceModal, setActiveSourceModal] = useState<SourceMetadata | null>(null);
  const [isPdfSplitOpen, setIsPdfSplitOpen] = useState<boolean>(false);
  const [splitHighlightSource, setSplitHighlightSource] = useState<SourceMetadata | null>(null);
  const [showExportMenu, setShowExportMenu] = useState<boolean>(false);

  // Rename Conversation Modal state
  const [editingConvModal, setEditingConvModal] = useState<ConversationItem | null>(null);
  const [editTitleInput, setEditTitleInput] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleOpenSourceModal = (s: SourceMetadata) => {
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

  useEffect(() => {
    if (!selectedReportId && reports.length > 0) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  const activeReport = reports.find((r) => r.id === selectedReportId || r.documentId === selectedReportId);

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

  // Load messages when activeConversationId changes (history load ONLY)
  const loadConversationMessages = useCallback(async (convId: string) => {
    setIsLoadingHistory(true);
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
      } else {
        setMessages([]);
      }
    } catch (err: any) {
      console.warn('Error loading conversation messages:', err);
      // Clean up stale query param if conversation is not found
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
  }, [setSearchParams]);

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
  }, [messages, isGenerating]);

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
    if (!promptText.trim() || isGenerating) return;

    const userPrompt = promptText.trim();

    const userMsg: MessageUIItem = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: userPrompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
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

      // Live POST /api/chat call with abort signal
      const resData = await chatService.sendChat({
        conversation_id: activeConversationId || undefined,
        document_id: selectedReportId || activeReport?.id || activeReport?.documentId || 'doc_unknown',
        question: userPrompt,
        conversation_history: historyForBackend,
      }, controller.signal);

      if (resData && resData.answer) {
        const newConvId = resData.conversationId || activeConversationId;
        if (newConvId && !activeConversationId) {
          setActiveConversationId(newConvId);
          setSearchParams({ doc: selectedReportId, conv: newConvId });
        } else if (newConvId && activeConversationId !== newConvId) {
          setActiveConversationId(newConvId);
          setSearchParams({ doc: selectedReportId, conv: newConvId });
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
        setIsGenerating(false);
        abortControllerRef.current = null;
        await loadConversations();
      } else {
        throw new Error('Invalid response from AI Analyst service.');
      }
    } catch (err: any) {
      abortControllerRef.current = null;
      setIsGenerating(false);
      if (err?.name === 'CanceledError' || err?.name === 'AbortError' || err?.code === 'ERR_CANCELED') {
        console.log('Response generation cancelled by user.');
        return;
      }
      console.error('API /api/chat error:', err);
      // Show user-friendly error in the chat stream itself
      const errMsg: MessageUIItem = {
        id: `err_${Date.now()}`,
        sender: 'assistant',
        text: `⚠️ I couldn’t generate an answer at this moment. Please try again or rephrase your question.\n\n*Technical detail: ${err?.response?.data?.detail || err?.message || 'Connection failed.'}*`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errMsg]);
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
    e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
  };

  // Sanitize a metadata string — strips raw tuple/object artifacts like {(...), }
  const sanitizeMeta = (val: any): string => {
    if (!val) return '';
    const s = String(val);
    // Remove surrounding set/tuple artifacts like {(...), } or {"value"}
    return s.replace(/^\{\(?|\)?\,?\}$/g, '').replace(/^["']|["']$/g, '').trim();
  };

  const reportTitle = sanitizeMeta(activeReport?.companyName || activeReport?.company_name || activeReport?.filename || 'Report');

  return (
    <div className="flex flex-col lg:flex-row gap-6 max-w-7xl mx-auto w-full min-w-0 pb-6 animate-fade-in">
      {/* LEFT PANEL: Report Details, History & Compact Prompts */}
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
              <div className="flex justify-between items-start gap-2">
                <span className="text-slate-500 text-[11px] flex-shrink-0">Company:</span>
                <span className="font-bold text-slate-900 dark:text-white text-right text-[11px] leading-snug" title={sanitizeMeta(activeReport.companyName || activeReport.company_name)}>
                  {sanitizeMeta(activeReport.companyName || activeReport.company_name)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 text-[11px]">Fiscal Period:</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {sanitizeMeta(activeReport.financialYear || activeReport.fiscal_period)}
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

        {/* Conversation History Sidebar with Enhanced Active Badge */}
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

          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {conversations.length > 0 ? (
              conversations.map((c) => {
                const isActive = c.conversationId === activeConversationId;
                return (
                  <div
                    key={c.conversationId}
                    onClick={() => handleSelectConversation(c)}
                    className={`p-3.5 rounded-2xl border text-xs transition-all cursor-pointer flex items-center justify-between group relative overflow-hidden ${
                      isActive
                        ? 'bg-emerald-500/15 border-2 border-emerald-500 text-emerald-950 dark:text-emerald-100 font-extrabold shadow-sm'
                        : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 hover:border-slate-300 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="min-w-0 pr-2 space-y-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-xs font-bold">{c.title}</p>
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

        {/* Compact Suggested Prompts (Hidden when conversation active) */}
        {messages.length === 0 && (
          <div className="p-4 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2 animate-fade-in">
            <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
              <span>Suggested Prompts</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendQuery(q)}
                  className="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-950 hover:bg-emerald-500/10 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/30 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-all text-left cursor-pointer"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
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
            {/* Split PDF Viewer Toggle Button */}
            <button
              onClick={() => setIsPdfSplitOpen(!isPdfSplitOpen)}
              className={`px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                isPdfSplitOpen
                  ? 'bg-emerald-500 text-slate-950 border-emerald-400 font-extrabold shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 hover:bg-emerald-500/10 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
              }`}
              title="Toggle Live In-Document PDF Split View"
            >
              <Columns className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{isPdfSplitOpen ? 'Hide PDF Split' : 'PDF Split View'}</span>
            </button>

            {/* Export Suite Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-emerald-500/10 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
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
                        conversationHistory: messages.map((m) => ({ role: m.sender, content: m.text, sources: m.sources })),
                      });
                    }}
                    className="w-full px-4 py-2.5 text-left text-slate-700 dark:text-slate-200 hover:bg-emerald-500/10 hover:text-emerald-600 flex items-center gap-2 font-medium"
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
                        conversationHistory: messages.map((m) => ({ role: m.sender, content: m.text, sources: m.sources })),
                      });
                    }}
                    className="w-full px-4 py-2.5 text-left text-slate-700 dark:text-slate-200 hover:bg-blue-500/10 hover:text-blue-600 flex items-center gap-2 font-medium"
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
                    className="w-full px-4 py-2.5 text-left text-slate-700 dark:text-slate-200 hover:bg-purple-500/10 hover:text-purple-600 flex items-center gap-2 font-medium"
                  >
                    <Presentation className="w-4 h-4 text-purple-500" />
                    <span>Board Slide Deck (.json)</span>
                  </button>
                </div>
              )}
            </div>

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

        {/* Live Side-by-Side Flex Container */}
        <div className="flex flex-col lg:flex-row gap-4 min-h-[460px] items-stretch flex-1">
          {/* Left Column: Messages Stream & Bottom Input */}
          <div className="flex-1 flex flex-col min-w-0 space-y-4">
            {/* Conversation Message Stream with Distinct User/AI Separation */}
            <div className="flex-1 min-h-[460px] max-h-[620px] overflow-y-auto p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
              {messages.length > 0 ? (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3.5 ${
                      msg.sender === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {msg.sender === 'assistant' && (
                      <div className="w-9 h-9 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0 border border-emerald-500/20 shadow-xs">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`p-4 sm:p-5 rounded-2xl text-xs space-y-3 leading-relaxed shadow-sm min-w-0 ${
                        msg.sender === 'user'
                          ? 'bg-emerald-600 dark:bg-emerald-600 text-white rounded-tr-none max-w-xl ml-auto'
                          : 'bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none max-w-3xl w-full'
                      }`}
                    >
                      {/* Message Header/Sender Title */}
                      <div className="flex items-center justify-between gap-2 border-b pb-2 border-emerald-500/30 dark:border-slate-800/80">
                        <span className="font-extrabold text-[11px] uppercase tracking-wider opacity-90">
                          {msg.sender === 'user' ? 'You' : 'FinSight AI Analyst'}
                        </span>
                        <span className="text-[10px] opacity-75">{msg.timestamp}</span>
                      </div>

                      {/* Message Body with Interactive Markdown & Citation Badges */}
                      <div className="text-xs sm:text-sm font-normal leading-relaxed">
                        {msg.sender === 'assistant' ? (
                          <RichMarkdownRenderer
                            content={msg.text}
                            sources={msg.sources}
                            onOpenSourceModal={(s) => handleOpenSourceModal(s)}
                          />
                        ) : (
                          <div className="whitespace-pre-wrap">{msg.text}</div>
                        )}
                      </div>

                      {/* AI Response Sources & Action Toolbar */}
                      {msg.sender === 'assistant' && (
                        <div className="space-y-3">
                          {/* Compact Deduplicated Citations Accordion */}
                          {msg.sources && msg.sources.length > 0 && (
                            <CitationsAccordion
                              sources={msg.sources}
                              onOpenModal={(s) => handleOpenSourceModal(s)}
                            />
                          )}

                          {/* Action Toolbar: Copy & Regenerate */}
                          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200/40 dark:border-slate-800/40">
                            <button
                              onClick={() => handleCopyText(msg.id, msg.text)}
                              className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 flex items-center gap-1 cursor-pointer transition-colors text-[11px] font-semibold"
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
                              disabled={isGenerating}
                              className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 flex items-center gap-1 cursor-pointer transition-colors disabled:opacity-50 text-[11px] font-semibold"
                              title="Regenerate AI answer"
                            >
                              <RefreshCw className="w-3 h-3" />
                              <span>Regenerate</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    {msg.sender === 'user' && (
                      <div className="w-9 h-9 rounded-2xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center flex-shrink-0 shadow-xs">
                        <User className="w-4 h-4" />
                      </div>
                    )}
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
              {isGenerating && (
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

              <div ref={messagesEndRef} />
            </div>

            {/* BOTTOM PANEL: Single-Line Truncated Input & Solid Contrast Send / Stop Button */}
            <div className="p-3 sm:p-4 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-lg space-y-2">
              <div className="flex items-center gap-2.5">
                <div className="flex-1 min-w-0">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    placeholder={
                      selectedReportId
                        ? `Ask a question about ${reportTitle}...`
                        : 'Upload a report PDF to begin AI Q&A...'
                    }
                    value={queryText}
                    onChange={handleTextareaInput}
                    onKeyDown={handleTextareaKeyDown}
                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl text-xs sm:text-sm font-medium text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all resize-none min-h-[46px] truncate"
                  />
                </div>
                {isGenerating ? (
                  <button
                    onClick={handleStopResponse}
                    className="px-5 py-3 rounded-2xl bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-rose-600/20 flex-shrink-0 h-[46px]"
                    title="Stop generating AI response"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                    <span>Stop</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleSendQuery(queryText)}
                    disabled={!queryText.trim()}
                    className="px-5 py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:opacity-60 text-white font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-emerald-600/20 flex-shrink-0 h-[46px]"
                  >
                    <span>Send</span>
                    <Send className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              <div className="flex items-center justify-between px-2 text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                  <CornerDownLeft className="w-3 h-3" /> Press Enter to send, Shift+Enter for new line
                </span>
                <span>Grounded AI Intelligence • Verified Page Citations</span>
              </div>
            </div>
          </div>

          {/* Right Panel: Interactive In-Document PDF Split View */}
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
