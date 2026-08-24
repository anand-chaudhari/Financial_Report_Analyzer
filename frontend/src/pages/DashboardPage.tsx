import React, { useState, useEffect } from 'react';
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
  AlertCircle,
  Loader2,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { reports, uploadReport, deleteReport, fetchReports } = useReportContext();

  const [selectedFilter, setSelectedFilter] = useState<'All' | '10-K' | '10-Q' | 'Earnings' | 'Annual'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState(1);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);

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

  useEffect(() => {
    let interval: any;
    if (uploading) {
      setUploadStep(1);
      interval = setInterval(() => {
        setUploadStep((prev) => (prev < 3 ? prev + 1 : prev));
      }, 6000);
    }
    return () => clearInterval(interval);
  }, [uploading]);

  const handleModalUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploading(true);
      setUploadError(null);
      setUploadSuccessMsg(null);

      try {
        const res = await uploadReport(file);
        setUploading(false);
        setUploadSuccessMsg(`Successfully uploaded & indexed "${res.fileName || res.filename}"!`);
        await fetchReports();
        setTimeout(() => {
          setUploadSuccessMsg(null);
          setUploadModalOpen(false);
        }, 1600);
      } catch (err: any) {
        setUploading(false);
        await fetchReports();
        setUploadError(err?.message || 'Failed to upload report PDF. Please try again.');
      }
    }
  };

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
            onClick={() => setUploadModalOpen(true)}
            className="px-5 py-3 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2 cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Filing</span>
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
          subtitle={reports.length > 0 ? "Workspace Index Ready" : "Indexed Storage: 0 MB / 500 MB"}
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
            onAction={() => setUploadModalOpen(true)}
            icon={UploadCloud}
          />
        )}
      </div>

      {/* Upload Modal with Productized Progress Steps */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl space-y-6 relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    Upload Financial Report
                  </h3>
                  <p className="text-xs text-slate-500">PDF filing up to 25MB</p>
                </div>
              </div>
              {!uploading && (
                <button
                  onClick={() => setUploadModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-sm font-bold p-1 cursor-pointer"
                >
                  ✕
                </button>
              )}
            </div>

            {uploadError && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2.5">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            {uploadSuccessMsg && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{uploadSuccessMsg}</span>
              </div>
            )}

            <div className="p-8 border-2 border-dashed border-slate-300 dark:border-slate-800 rounded-2xl text-center space-y-4 bg-slate-50/50 dark:bg-slate-950/50">
              {uploading ? (
                <div className="py-8 space-y-5">
                  <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
                    <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin" />
                    <Loader2 className="w-7 h-7 text-emerald-500 animate-spin" />
                  </div>

                  <div className="space-y-1.5">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                      Processing & Analyzing PDF Filing...
                    </h4>
                    <p className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold animate-pulse">
                      {uploadStep === 1 && '• Step 1: Deep document parsing & extracting financial tables...'}
                      {uploadStep === 2 && '• Step 2: Section chunking & generating semantic index...'}
                      {uploadStep === 3 && '• Step 3: Storing workspace intelligence index...'}
                    </p>
                  </div>

                  <div className="w-full bg-slate-200 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full transition-all duration-1000 rounded-full"
                      style={{ width: uploadStep === 1 ? '35%' : uploadStep === 2 ? '70%' : '95%' }}
                    />
                  </div>
                </div>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center mx-auto">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-900 dark:text-white">
                      Select your financial report PDF
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Extracts tables, footnote details, and page citations
                    </p>
                  </div>
                  <label className="inline-block px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl cursor-pointer transition-colors shadow-md shadow-emerald-500/20">
                    <span>Browse PDF File</span>
                    <input
                      type="file"
                      accept="application/pdf"
                      className="hidden"
                      onChange={handleModalUpload}
                    />
                  </label>
                </>
              )}
            </div>

            {!uploading && (
              <div className="flex justify-end">
                <button
                  onClick={() => setUploadModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-500 hover:text-slate-900 dark:hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
