import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import { chatService } from '../services/chatService';
import {
  Bot,
  Send,
  User,
  Sparkles,
  FileText,
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
} from 'lucide-react';
import { formatBytes } from '../utils/formatters';

interface SourceItem {
  page_number: number;
  section: string;
  document_name: string;
  snippet?: string;
  similarity_score?: number;
}

interface MessageItem {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  pages?: number[];
  sections?: string[];
  sources?: SourceItem[];
  retrieved_chunks?: Array<any>;
}

export const AnalystPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const docIdParam = searchParams.get('doc');
  const { reports } = useReportContext();

  const [selectedReportId, setSelectedReportId] = useState<string>(docIdParam || (reports[0]?.id ?? ''));
  const [queryText, setQueryText] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [activeSourceModal, setActiveSourceModal] = useState<SourceItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!selectedReportId && reports.length > 0) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  const activeReport = reports.find((r) => r.id === selectedReportId || r.documentId === selectedReportId);

  // Auto-scroll to bottom of chat
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

  const handleSendQuery = async (promptText: string) => {
    if (!promptText.trim() || loading) return;

    setErrorState(null);
    const userPrompt = promptText.trim();

    const userMsg: MessageItem = {
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

      // Direct live API connection to POST /api/chat
      const resData = await chatService.sendChat({
        document_id: selectedReportId || activeReport?.id || activeReport?.documentId || 'doc_unknown',
        question: userPrompt,
        conversation_history: historyForBackend,
      });

      if (resData && resData.answer) {
        // Construct structured source cards
        const fileName = activeReport?.fileName || activeReport?.filename || 'Financial_Report.pdf';
        const pageList = resData.pages || [];
        const sectionList = resData.sections || [];
        const chunks = resData.retrieved_chunks || [];

        const structuredSources: SourceItem[] = [];

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

        const aiMsg: MessageItem = {
          id: `ai_${Date.now()}`,
          sender: 'assistant',
          text: resData.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          pages: pageList,
          sections: sectionList,
          sources: structuredSources,
          retrieved_chunks: chunks,
        };

        setMessages((prev) => [...prev, aiMsg]);
        setLoading(false);
      } else {
        throw new Error('Invalid or empty response returned from AI Analyst engine.');
      }
    } catch (err: any) {
      console.error('API /api/chat request error:', err);
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

  const handleClearConversation = () => {
    setMessages([]);
    setErrorState(null);
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
      {/* LEFT PANEL: Selected Report Information & Details */}
      <div className="w-full lg:w-80 flex-shrink-0 space-y-4">
        <div className="p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
          <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-slate-900 dark:text-white tracking-tight">
                Selected Report
              </h2>
              <p className="text-[11px] text-slate-500">Document Metadata & Vector Status</p>
            </div>
          </div>

          {/* Report Selector Dropdown */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Target Report File
            </label>
            {reports.length > 0 ? (
              <select
                value={selectedReportId}
                onChange={(e) => {
                  setSelectedReportId(e.target.value);
                  setErrorState(null);
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
                <span>Upload PDF First</span>
              </button>
            )}
          </div>

          {/* Detailed Metadata Breakdown */}
          {activeReport ? (
            <div className="space-y-3 pt-1">
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 space-y-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-1.5 text-[11px]">
                    <Building2 className="w-3.5 h-3.5" /> Company:
                  </span>
                  <span className="font-bold text-slate-900 dark:text-white truncate max-w-[140px]">
                    {activeReport.companyName || activeReport.company_name || 'Corporate Entity'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-1.5 text-[11px]">
                    <Calendar className="w-3.5 h-3.5" /> Fiscal Period:
                  </span>
                  <span className="font-bold text-slate-900 dark:text-white">
                    {activeReport.financialYear || activeReport.fiscal_period || 'FY2024'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-1.5 text-[11px]">
                    <BookOpen className="w-3.5 h-3.5" /> Page Count:
                  </span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">
                    {activeReport.pageCount || activeReport.total_pages || 1} Pages
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-1.5 text-[11px]">
                    <Layers className="w-3.5 h-3.5" /> File Size:
                  </span>
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    {formatBytes(activeReport.fileSize || activeReport.file_size || 1024 * 500)}
                  </span>
                </div>
              </div>

              {/* Status Badge */}
              <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs font-bold flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  <span>Processing Status</span>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-[10px] font-extrabold uppercase tracking-wider">
                  Indexed
                </span>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-500">
              No report selected. Upload a PDF filing to start.
            </div>
          )}
        </div>

        {/* Suggested Financial Questions */}
        <div className="p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-500" />
            <h3 className="text-xs font-extrabold text-slate-900 dark:text-white uppercase tracking-wider">
              Suggested Prompts
            </h3>
          </div>
          <div className="space-y-2">
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
                AI Analyst Conversation
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                Grounded Q&A via POST /api/chat with Groq LLM & ChromaDB page sources
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
                <span className="hidden sm:inline">Clear Chat</span>
              </button>
            )}
          </div>
        </div>

        {/* Conversation Message Stream */}
        <div className="flex-1 min-h-[440px] max-h-[600px] overflow-y-auto p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
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
                AI Analyst Conversation Ready
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Ask any question about your selected financial report or click one of the suggested prompts on the left.
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
                  Querying POST /api/chat with Groq LLM & ChromaDB page embeddings...
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
            <span>Grounded Q&A • Groq Llama-3.3 70B & ChromaDB</span>
          </div>
        </div>
      </div>

      {/* SOURCE CITATION MODAL / DRAWER */}
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
    </div>
  );
};
