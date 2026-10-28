import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import { ReportCard } from '../components/ReportCard';
import { EmptyState } from '../components/EmptyState';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { RenameModal } from '../components/common/RenameModal';
import { Search, UploadCloud, FileText, AlertCircle } from 'lucide-react';
import { ReportItem } from '../types/report';

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate();
  const { reports, deleteReport, renameReport } = useReportContext();

  const [selectedFilter, setSelectedFilter] = useState<'All' | '10-K' | '10-Q' | 'Earnings' | 'Annual'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [reportToDelete, setReportToDelete] = useState<ReportItem | null>(null);
  const [reportToRename, setReportToRename] = useState<ReportItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const filterOptions: Array<'All' | '10-K' | '10-Q' | 'Earnings' | 'Annual'> = useMemo(
    () => ['All', '10-K', '10-Q', 'Earnings', 'Annual'],
    []
  );

  const filteredReports = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return reports.filter((r) => {
      const type = r.filingType || '10-K';
      const matchesFilter = selectedFilter === 'All' || type === selectedFilter;
      if (!matchesFilter) return false;
      if (!q) return true;
      const company = (r.companyName || r.company_name || r.filename || '').toLowerCase();
      const ticker = (r.ticker || '').toLowerCase();
      const name = (r.fileName || r.filename || '').toLowerCase();
      return company.includes(q) || ticker.includes(q) || name.includes(q);
    });
  }, [reports, selectedFilter, searchQuery]);

  const handleConfirmDelete = useCallback(async () => {
    if (!reportToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteReport(reportToDelete.id);
      setReportToDelete(null);
    } catch (err: any) {
      setDeleteError(err?.message || 'Failed to delete report. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  }, [reportToDelete, deleteReport]);

  return (
    <div className="space-y-6 animate-fade-in w-full min-w-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Financial Reports Library
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Manage your uploaded corporate filings and vector index storage
          </p>
        </div>

        <button
          onClick={() => navigate('/upload')}
          className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center gap-2 cursor-pointer self-start sm:self-auto"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Upload Filing PDF</span>
        </button>
      </div>

      {deleteError && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 flex items-center justify-between text-rose-700 dark:text-rose-400 text-xs animate-shake">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{deleteError}</span>
          </div>
          <button
            onClick={() => setDeleteError(null)}
            className="text-xs font-bold hover:underline cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          {filterOptions.map((opt) => (
            <button
              key={opt}
              onClick={() => setSelectedFilter(opt)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                selectedFilter === opt
                  ? 'bg-emerald-500 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {opt}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search report name or ticker..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
          />
        </div>
      </div>

      {/* Reports Library Grid */}
      {filteredReports.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredReports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              onAnalyze={() => navigate(`/analyst?doc=${report.id}`)}
              onDelete={() => setReportToDelete(report)}
              onRename={() => setReportToRename(report)}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No Reports Found"
          description={
            searchQuery || selectedFilter !== 'All'
              ? 'No financial reports match your selected search query or filter.'
              : 'Your workspace library is currently empty. Upload your first financial filing PDF to start.'
          }
          actionLabel="Upload PDF Filing"
          onAction={() => navigate('/upload')}
          icon={FileText}
        />
      )}

      {/* Confirmation Modal for Document Deletion */}
      <ConfirmModal
        isOpen={!!reportToDelete}
        title="Delete Financial Report"
        description={`Are you sure you want to delete "${reportToDelete?.companyName || reportToDelete?.fileName || 'this filing'}"? This action permanently removes stored files, vector embeddings, and all generated AI analysis.`}
        confirmLabel="Delete Report"
        cancelLabel="Cancel"
        isDanger
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) setReportToDelete(null);
        }}
      />

      {/* Modal for Document Renaming */}
      <RenameModal
        isOpen={!!reportToRename}
        initialName={reportToRename?.companyName || reportToRename?.fileName || ''}
        onConfirm={async (newName) => {
          if (reportToRename) {
            await renameReport(reportToRename.id, newName);
          }
        }}
        onClose={() => setReportToRename(null)}
      />
    </div>
  );
};
