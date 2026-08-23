import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  MOCK_REPORTS,
  MOCK_CONVERSATIONS,
  MOCK_STATS,
  MockReport,
} from '../utils/mockData';
import { StatCard } from '../components/StatCard';
import { ReportCard } from '../components/ReportCard';
import { EmptyState } from '../components/EmptyState';
import {
  FileText,
  CheckCircle2,
  HelpCircle,
  Zap,
  UploadCloud,
  Bot,
  BarChart3,
  ArrowRight,
  Sparkles,
  Search,
  Filter,
  FileSpreadsheet,
  Clock,
  BookOpen,
  Plus,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [reports, setReports] = useState<MockReport[]>(MOCK_REPORTS);
  const [selectedFilter, setSelectedFilter] = useState<'All' | '10-K' | '10-Q' | 'Earnings' | 'Annual'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const filterOptions: Array<'All' | '10-K' | '10-Q' | 'Earnings' | 'Annual'> = [
    'All',
    '10-K',
    '10-Q',
    'Earnings',
    'Annual',
  ];

  const filteredReports = reports.filter((r) => {
    const matchesFilter = selectedFilter === 'All' || r.filingType === selectedFilter;
    const matchesSearch =
      r.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.filename.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleSimulateUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploading(true);
      setUploadSuccess(null);

      setTimeout(() => {
        const newReport: MockReport = {
          id: `rep_${Date.now()}`,
          filename: file.name,
          company: file.name.replace('.pdf', '').replace(/_/g, ' '),
          ticker: 'CUSTOM',
          filingType: '10-Q',
          uploadDate: new Date().toISOString(),
          totalPages: 48,
          fileSize: file.size,
          status: 'ready',
          revenue: '$12.4B',
          growth: '+8.2%',
          tags: ['Custom Upload', 'Auto-Indexed'],
        };

        setReports((prev) => [newReport, ...prev]);
        setUploading(false);
        setUploadSuccess(`Successfully uploaded and indexed "${file.name}"!`);
        setTimeout(() => {
          setUploadSuccess(null);
          setUploadModalOpen(false);
        }, 1800);
      }, 1500);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in w-full">
      {/* Welcome Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
        <div className="relative z-10 space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Financial Copilot Active</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Welcome back, {user?.displayName || 'Financial Analyst'}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-2xl leading-relaxed">
            Query multi-page 10-Ks, inspect revenue trajectories, and extract verified citations with sub-second AI retrieval.
          </p>
        </div>

        {/* Action Triggers */}
        <div className="relative z-10 flex flex-wrap items-center gap-3">
          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs sm:text-sm shadow-md transition-all cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Report</span>
          </button>
          <button
            onClick={() => navigate('/analyst')}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold text-xs sm:text-sm border border-slate-200 dark:border-slate-700 transition-all cursor-pointer"
          >
            <Bot className="w-4 h-4 text-emerald-500" />
            <span>Ask AI Analyst</span>
          </button>
        </div>

        {/* Ambient subtle glow */}
        <div className="absolute right-0 top-0 w-80 h-80 bg-emerald-500/5 dark:bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Total Reports"
          value={reports.length}
          change={MOCK_STATS.totalReportsChange}
          changeType="positive"
          description="In your workspace library"
          icon={FileText}
          iconColor="emerald"
        />
        <StatCard
          title="Reports Processed"
          value={`${reports.filter((r) => r.status === 'ready').length} / ${reports.length}`}
          change="100% indexed"
          changeType="positive"
          description="Ready for semantic query"
          icon={CheckCircle2}
          iconColor="cyan"
        />
        <StatCard
          title="Questions Asked"
          value={MOCK_STATS.questionsAsked}
          change={MOCK_STATS.questionsChange}
          changeType="positive"
          description="Across all indexed filings"
          icon={HelpCircle}
          iconColor="indigo"
        />
        <StatCard
          title="Avg Retrieval Speed"
          value={MOCK_STATS.avgRetrievalTime}
          change="Sub-second"
          changeType="neutral"
          description="Vector chunk similarity"
          icon={Zap}
          iconColor="amber"
        />
      </div>

      {/* Quick Actions Bar */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Quick Actions
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex flex-col items-start p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 hover:bg-slate-100/80 dark:hover:bg-slate-900 transition-all text-left cursor-pointer group"
          >
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 mb-2 group-hover:scale-105 transition-transform">
              <UploadCloud className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-900 dark:text-slate-100">Upload PDF Filing</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Parse 10-K, 10-Q or Earnings</span>
          </button>

          <button
            onClick={() => navigate('/analyst')}
            className="flex flex-col items-start p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 hover:bg-slate-100/80 dark:hover:bg-slate-900 transition-all text-left cursor-pointer group"
          >
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 mb-2 group-hover:scale-105 transition-transform">
              <Bot className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-900 dark:text-slate-100">Ask AI Analyst</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Query balance sheet & notes</span>
          </button>

          <button
            onClick={() => navigate('/analytics')}
            className="flex flex-col items-start p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 hover:bg-slate-100/80 dark:hover:bg-slate-900 transition-all text-left cursor-pointer group"
          >
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 mb-2 group-hover:scale-105 transition-transform">
              <BarChart3 className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-900 dark:text-slate-100">Financial Visualizer</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Automated charts & ratios</span>
          </button>

          <button
            onClick={() => navigate('/history')}
            className="flex flex-col items-start p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 hover:bg-slate-100/80 dark:hover:bg-slate-900 transition-all text-left cursor-pointer group"
          >
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 mb-2 group-hover:scale-105 transition-transform">
              <FileSpreadsheet className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-900 dark:text-slate-100">Conversation History</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Review verified citations</span>
          </button>
        </div>
      </div>

      {/* Main Content Layout: Left (Recent Reports), Right (Recent Conversations) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Recent Reports */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Recent Reports</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Indexed financial filings ready for AI retrieval and financial extraction
              </p>
            </div>

            <Link
              to="/reports"
              className="text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1 self-start sm:self-auto"
            >
              <span>View all ({reports.length})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Filters and Search */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
            {/* Filter pills */}
            <div className="flex items-center gap-1.5 p-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-x-auto">
              {filterOptions.map((opt) => (
                <button
                  key={opt}
                  onClick={() => setSelectedFilter(opt)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer whitespace-nowrap ${
                    selectedFilter === opt
                      ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/25'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>

            {/* Quick search */}
            <div className="relative flex-1 max-w-xs">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Filter company, ticker..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          {/* Reports Grid */}
          {filteredReports.length === 0 ? (
            <EmptyState
              title="No reports match your filter"
              description="Try selecting a different filing type or clearing the search query."
              actionLabel="Clear Filters"
              onAction={() => {
                setSelectedFilter('All');
                setSearchQuery('');
              }}
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {filteredReports.slice(0, 4).map((report) => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>
          )}
        </div>

        {/* Right 1 Col: Recent Conversations */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Recent AI Queries</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Ground-truth citations & answers
              </p>
            </div>
            <Link
              to="/history"
              className="text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1"
            >
              <span>History</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {MOCK_CONVERSATIONS.map((conv) => (
              <div
                key={conv.id}
                onClick={() => navigate(`/reports/${conv.reportId}`)}
                className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 transition-all cursor-pointer shadow-xs space-y-2.5 group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-bold text-[10px] border border-emerald-500/20">
                      {conv.ticker}
                    </span>
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate max-w-[130px]">
                      {conv.reportName}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400">{conv.timestamp}</span>
                </div>

                <p className="text-xs font-bold text-slate-900 dark:text-slate-100 line-clamp-2 leading-snug group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                  "{conv.question}"
                </p>

                <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                  {conv.answer}
                </p>

                {/* Citations Preview */}
                <div className="pt-1 flex items-center gap-1.5 text-[10px] text-emerald-700 dark:text-emerald-400 font-semibold">
                  <BookOpen className="w-3 h-3" />
                  <span>Cited: Page {conv.citations.map((c) => c.page_number).join(', ')}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-5 animate-scale-up">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">Upload Financial Report</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">PDF documents up to 50MB</p>
                </div>
              </div>
              <button
                onClick={() => setUploadModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-sm font-bold p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Drop area */}
            <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-emerald-500 rounded-2xl p-8 text-center space-y-3 bg-slate-50 dark:bg-slate-950 transition-colors">
              {uploading ? (
                <div className="space-y-3 py-4">
                  <div className="w-10 h-10 border-3 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin mx-auto" />
                  <div className="text-xs font-bold text-slate-800 dark:text-slate-200">
                    Extracting pages & indexing embeddings...
                  </div>
                  <p className="text-[11px] text-slate-500">Generating citation vectors in ChromaDB</p>
                </div>
              ) : uploadSuccess ? (
                <div className="space-y-2 py-4 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="w-10 h-10 mx-auto" />
                  <div className="text-xs font-bold">{uploadSuccess}</div>
                </div>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">
                      Choose a PDF report or drag it here
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 block">
                      Supports 10-K, 10-Q, 8-K, Annual Reports & Earnings Press Releases
                    </span>
                  </div>
                  <label className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer transition-all">
                    <span>Browse Files</span>
                    <input
                      type="file"
                      accept="application/pdf"
                      className="hidden"
                      onChange={handleSimulateUpload}
                    />
                  </label>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
