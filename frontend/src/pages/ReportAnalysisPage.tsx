import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useTheme } from '../hooks/useTheme';
import { reportService } from '../services/reportService';
import { financialService } from '../services/financialService';
import { ReportDetail, FinancialSummary, FinancialChartData } from '../types';
import { CitationBadge } from '../components/CitationBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { formatBytes } from '../utils/formatters';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
} from 'recharts';
import {
  ArrowLeft,
  FileText,
  Send,
  Sparkles,
  Bot,
  User,
  BarChart2,
  Trash2,
  TrendingUp,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { FinancialOverviewSection } from '../components/financial/FinancialOverviewSection';

export const ReportAnalysisPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const { theme } = useTheme();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [chartData, setChartData] = useState<FinancialChartData | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'charts' | 'summary'>('chat');
  const [inputQuery, setInputQuery] = useState('');
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const { messages, loading: chatLoading, sendQuery, clearChat } = useChat(reportId || '');

  useEffect(() => {
    if (!reportId) return;

    reportService.getReportDetail(reportId).then((res) => {
      if (res.success && res.data) setReport(res.data);
    });

    financialService.getSummary(reportId).then((res) => {
      if (res.success && res.data) setSummary(res.data);
    });

    financialService.getChartData(reportId).then((res) => {
      if (res.success && res.data) setChartData(res.data);
    });
  }, [reportId]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chatLoading]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;
    sendQuery(inputQuery);
    setInputQuery('');
  };

  const chartTheme = {
    grid: theme === 'dark' ? '#334155' : '#e2e8f0',
    axis: theme === 'dark' ? '#94a3b8' : '#64748b',
    tooltipBg: theme === 'dark' ? '#0f172a' : '#ffffff',
    tooltipBorder: theme === 'dark' ? '#334155' : '#cbd5e1',
    tooltipText: theme === 'dark' ? '#f8fafc' : '#0f172a',
  };

  return (
    <div className="space-y-6 animate-fade-in w-full">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="p-2.5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-slate-300 dark:hover:border-slate-700 transition-all duration-200 shadow-sm cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <span className="truncate max-w-xs sm:max-w-md">{report?.filename || 'Financial Report Analysis'}</span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {report?.total_pages || 0} Pages • {report?.file_size ? formatBytes(report.file_size) : ''} • AI Intelligence Active
            </p>
          </div>
        </div>

        {/* Tab Switcher Pills */}
        <div className="flex items-center p-1 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-inner self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === 'chat'
                ? 'bg-gradient-to-r from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-950/20 dark:shadow-emerald-950'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            <span>AI Assistant</span>
          </button>
          <button
            onClick={() => setActiveTab('charts')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === 'charts'
                ? 'bg-gradient-to-r from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-950/20 dark:shadow-emerald-950'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <BarChart2 className="w-3.5 h-3.5" />
            <span>Visual Charts</span>
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === 'summary'
                ? 'bg-gradient-to-r from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-950/20 dark:shadow-emerald-950'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Executive Summary</span>
          </button>
        </div>
      </div>

      {/* Main Tab Content */}
      {activeTab === 'chat' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chat Window */}
          <div className="lg:col-span-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl flex flex-col h-[650px] shadow-sm dark:shadow-glass overflow-hidden">
            {/* Chat header */}
            <div className="px-6 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-300">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <Sparkles className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>Interactive Financial Assistant</span>
              </div>
              <button
                onClick={clearChat}
                className="text-xs text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 flex items-center gap-1.5 px-2.5 py-1 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear History</span>
              </button>
            </div>

            {/* Messages Feed */}
            <div className="flex-1 p-6 overflow-y-auto space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shadow-inner">
                    <Bot className="w-7 h-7" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">Ask Anything About This Report</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
                      Questions are answered strictly using verified document contents and cited with exact source page numbers.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-center pt-2 max-w-lg">
                    {[
                      'What is the total revenue and YoY growth?',
                      'What are the primary risk factors disclosed?',
                      'What is the net profit margin and EPS?',
                      'Summarize cash flows from operating activities.',
                    ].map((sample) => (
                      <button
                        key={sample}
                        onClick={() => sendQuery(sample)}
                        className="px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 text-left transition-all hover:border-emerald-500/40 cursor-pointer"
                      >
                        "{sample}"
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-3 animate-fade-in ${
                      msg.sender === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {msg.sender !== 'user' && (
                      <div className="w-9 h-9 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0 shadow-sm">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}
                    <div
                      className={`max-w-2xl rounded-3xl p-5 text-sm leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-gradient-to-r from-emerald-600 to-teal-500 text-white rounded-br-none shadow-md shadow-emerald-950/20 dark:shadow-emerald-950/40'
                          : 'bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-none shadow-sm'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>

                      {/* Render Citations if present */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3.5 pt-3 border-t border-slate-200 dark:border-slate-800">
                          <span className="text-[11px] font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider block mb-2">
                            Verified Source Pages:
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {msg.citations.map((c, cIdx) => (
                              <CitationBadge key={cIdx} citation={c} />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    {msg.sender === 'user' && (
                      <div className="w-9 h-9 rounded-2xl bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                ))
              )}
              {chatLoading && <LoadingSpinner size="sm" label="Analyzing document & generating verified response..." />}
              <div ref={chatBottomRef} />
            </div>

            {/* Input Bar */}
            <form onSubmit={handleSendMessage} className="p-3.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  placeholder="Ask a question about revenue, operating margin, debt, or cash flows..."
                  className="flex-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-2xl px-4 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all shadow-sm"
                />
                <button
                  type="submit"
                  disabled={chatLoading || !inputQuery.trim()}
                  className="px-5 py-3 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 disabled:opacity-40 text-white rounded-2xl font-bold flex items-center justify-center transition-all shadow-md cursor-pointer"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </form>
          </div>

          {/* Quick Info Sidebar */}
          <div className="space-y-4">
            <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl space-y-3.5 shadow-sm dark:shadow-glass">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Document Overview
              </h3>
              <div className="text-xs space-y-2.5 text-slate-700 dark:text-slate-300">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Status:</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400 uppercase">{report?.status}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Total Pages:</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-100">{report?.total_pages} pages</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Citations:</span>
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">Enabled</span>
                </div>
              </div>
            </div>

            <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl space-y-2.5 shadow-sm dark:shadow-glass">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-300">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>Verification Guardrails</span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                Answers are synthesized purely from verified document snippets with source page citations.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Visual Charts Tab */}
      {activeTab === 'charts' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue Chart */}
            <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl space-y-4 shadow-sm dark:shadow-glass">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>Revenue Performance ({chartData?.company_name || 'Report'})</span>
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData?.revenue_chart || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.5} />
                    <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                    <YAxis stroke={chartTheme.axis} fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: chartTheme.tooltipBg,
                        borderColor: chartTheme.tooltipBorder,
                        borderRadius: '12px',
                        color: chartTheme.tooltipText,
                        boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                      }}
                    />
                    <Bar dataKey="value" fill="#10b981" radius={[6, 6, 0, 0]} name="Revenue ($M)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Net Income Trend */}
            <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl space-y-4 shadow-sm dark:shadow-glass">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                <span>Net Income Trajectory</span>
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData?.net_income_chart || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.5} />
                    <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                    <YAxis stroke={chartTheme.axis} fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: chartTheme.tooltipBg,
                        borderColor: chartTheme.tooltipBorder,
                        borderRadius: '12px',
                        color: chartTheme.tooltipText,
                        boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                      }}
                    />
                    <Line type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={3} dot={{ r: 4, fill: '#06b6d4' }} name="Net Income ($M)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Key Financial Ratios */}
          {chartData?.key_ratios && chartData.key_ratios.length > 0 && (
            <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl shadow-sm dark:shadow-glass space-y-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Key Financial Ratios & Metrics</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                {chartData.key_ratios.map((ratio, rIdx) => (
                  <div key={rIdx} className="p-5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-inner">
                    <span className="text-xs text-slate-500 dark:text-slate-400 block font-medium">{ratio.name}</span>
                    <span className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1 block">{ratio.value}</span>
                    {ratio.description && (
                      <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5 block leading-relaxed">{ratio.description}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* CFO Summary Tab */}
      {activeTab === 'summary' && (
        <div className="p-6 sm:p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl space-y-6 shadow-sm dark:shadow-glass">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Executive Performance Summary</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Synthesized from key financial statement sections and disclosures.
            </p>
          </div>

          <div className="prose dark:prose-invert max-w-none text-sm text-slate-800 dark:text-slate-200 leading-relaxed bg-slate-50 dark:bg-slate-950 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-inner">
            {summary?.executive_summary || 'Executive summary is being prepared...'}
          </div>

          {summary?.key_highlights && summary.key_highlights.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">
                Key Performance Highlights
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {summary.key_highlights.map((item, idx) => (
                  <div key={idx} className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {reportId && (
            <div className="pt-2">
              <FinancialOverviewSection
                reportId={reportId}
                companyName={report?.company_name}
                financialYear={report?.fiscal_period}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
