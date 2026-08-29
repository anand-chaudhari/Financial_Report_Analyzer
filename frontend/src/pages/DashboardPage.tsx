import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useReportContext } from '../context/ReportContext';
import { StatCard } from '../components/StatCard';
import { ReportCard } from '../components/ReportCard';
import { EmptyState } from '../components/EmptyState';
import { toTitleCase } from '../utils/formatters';
import {
  FileText,
  CheckCircle2,
  Zap,
  UploadCloud,
  Bot,
  Sparkles,
  Search,
  BookOpen,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { reports, deleteReport } = useReportContext();

  const [selectedFilter, setSelectedFilter] = useState<'All' | '10-K' | '10-Q' | 'Earnings' | 'Annual'>('All');
  const [searchQuery, setSearchQuery] = useState('');

  const rawName = user?.displayName || user?.email?.split('@')[0] || 'Analyst';
  const userName = toTitleCase(rawName);

  const filteredReports = reports.filter((r) => {
    const type = r.filingType || '10-K';
    const matchesFilter = selectedFilter === 'All' || type === selectedFilter;
    const company = r.companyName || r.company_name || r.filename;
    const ticker = r.ticker || '';
    const name = r.fileName || r.filename;
    const matchesSearch =
      company.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
      name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const totalPagesCount = reports.reduce((acc, r) => acc + (r.pageCount || r.total_pages || 0), 0);

  return (
    <div className="space-y-8 animate-fade-in w-full min-w-0">
      {/* Welcome Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
        <div className="relative z-10 space-y-2 max-w-2xl min-w-0">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Document Intelligence Active</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight truncate">
            Welcome back, {userName}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
            Upload corporate filings, 10-Ks, or earnings reports to extract key metrics, compare quarters, and chat with your AI analyst.
          </p>
        </div>

        <div className="relative z-10 flex flex-wrap items-center gap-3">
          <button
            onClick={() => navigate('/upload')}
            className="px-5 py-3 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2 cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Filing PDF</span>
          </button>
          <Link
            to="/analyst"
            className="px-5 py-3 rounded-2xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold text-xs transition-colors flex items-center gap-2"
          >
            <Bot className="w-4 h-4 text-emerald-500" />
            <span>Ask AI Analyst</span>
          </Link>
        </div>
      </div>

      {/* Productized Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <StatCard
          title="Total Reports"
          value={reports.length.toString()}
          subtitle="Indexed in Workspace"
          icon={FileText}
          color="emerald"
        />
        <StatCard
          title="Processed Reports"
          value={reports.filter((r) => r.status === 'completed' || r.status === 'ready' || r.status === 'uploaded').length.toString()}
          subtitle="100% Fully Indexed"
          icon={CheckCircle2}
          color="blue"
        />
        <StatCard
          title="Pages Analyzed"
          value={totalPagesCount.toString()}
          subtitle="Automated Text & Table Extraction"
          icon={BookOpen}
          color="indigo"
        />
        <StatCard
          title="AI Index Status"
          value="Active"
          subtitle={reports.length > 0 ? "Workspace Index Ready" : "Indexed Storage: Ready"}
          icon={Zap}
          color="violet"
        />
      </div>

      {/* Recent Reports Section */}
      <div className="space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Uploaded Financial Reports
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Access your corporate filings and financial documents
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search report name or company..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all w-48 sm:w-64"
              />
            </div>
          </div>
        </div>

        {/* Reports Grid */}
        {filteredReports.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredReports.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                onAnalyze={() => navigate(`/analyst?doc=${report.id}`)}
                onDelete={() => deleteReport(report.id)}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No Financial Reports Uploaded Yet"
            description="Upload your first corporate 10-K, 10-Q, or earnings report PDF to extract financial insights and perform Q&A with your AI analyst."
            actionLabel="Upload PDF Filing"
            onAction={() => navigate('/upload')}
            icon={UploadCloud}
          />
        )}
      </div>
    </div>
  );
};
