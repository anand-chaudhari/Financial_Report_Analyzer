import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ReportItem } from '../types/report';
import { formatBytes, formatDate } from '../utils/formatters';
import {
  FileText,
  CheckCircle2,
  Clock,
  ArrowRight,
  BarChart3,
  Bot,
  Trash2,
  AlertCircle,
  Sparkles,
} from 'lucide-react';

interface ReportCardProps {
  report: ReportItem;
  onAnalyze?: () => void;
  onDelete?: () => void;
}

export const ReportCard: React.FC<ReportCardProps> = ({ report, onAnalyze, onDelete }) => {
  const navigate = useNavigate();

  const company = report.companyName || report.company_name || report.filename || 'Financial Report';
  const name = report.fileName || report.filename || 'Filing.pdf';
  const ticker = report.ticker || company.substring(0, 4).toUpperCase();
  const filingType = report.filingType || '10-K';
  const pages = report.pageCount || report.total_pages || 1;
  const size = report.fileSize || report.file_size || 0;
  const uploadedDate = report.uploadedAt || report.uploaded_at || new Date().toISOString();

  const getFilingBadgeColor = (type: string) => {
    switch (type) {
      case '10-K':
        return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
      case '10-Q':
        return 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border-cyan-500/30';
      case 'Earnings':
        return 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/30';
      default:
        return 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-500/30';
    }
  };

  const renderStatus = () => {
    switch (report.status) {
      case 'completed':
      case 'ready':
      case 'uploaded':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 flex-shrink-0">
            <CheckCircle2 className="w-3 h-3" />
            Ready
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30 flex-shrink-0">
            <Clock className="w-3 h-3 animate-spin" />
            Processing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/30 flex-shrink-0">
            <AlertCircle className="w-3 h-3" />
            Failed
          </span>
        );
    }
  };

  return (
    <div className="group relative bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 rounded-2xl p-5 transition-all duration-200 flex flex-col justify-between shadow-sm hover:shadow-md min-w-0">
      <div>
        {/* Header: Ticker, Company, Filing Type & Status */}
        <div className="flex items-start justify-between gap-3 min-w-0">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs tracking-wider flex-shrink-0 group-hover:scale-105 transition-transform">
              {ticker}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 min-w-0 flex-wrap">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate min-w-0" title={company}>
                  {company}
                </h3>
                <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border flex-shrink-0 ${getFilingBadgeColor(filingType)}`}>
                  {filingType}
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5" title={name}>
                {name}
              </p>
            </div>
          </div>
          {renderStatus()}
        </div>

        {/* Financial Highlights if available */}
        {report.revenue && (
          <div className="mt-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-[10px] text-slate-500 dark:text-slate-400 block font-medium">Revenue</span>
              <span className="font-bold text-slate-900 dark:text-slate-100">{report.revenue}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 dark:text-slate-400 block font-medium">YoY Growth</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">{report.growth}</span>
            </div>
          </div>
        )}

        {/* Date & Period */}
        <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
          <span>Period: <strong className="text-slate-600 dark:text-slate-300">{report.financialYear || report.fiscal_period || 'FY2024'}</strong></span>
          <span>Uploaded: {formatDate(uploadedDate)}</span>
        </div>
      </div>

      {/* Footer Info & Action buttons */}
      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 gap-2">
        <div className="flex items-center gap-1.5 min-w-0 truncate">
          <span className="truncate">{pages} pages</span>
          {size > 0 && (
            <>
              <span>•</span>
              <span className="truncate">{formatBytes(size)}</span>
            </>
          )}
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {onDelete && (
            <button
              onClick={onDelete}
              title="Delete Document"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={() => navigate(`/reports/${report.id}/summary`)}
            title="View AI Grounded Summary"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold transition-all cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
            <span>Summary</span>
          </button>
          <button
            onClick={onAnalyze || (() => navigate(`/analyst?doc=${report.id}`))}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs font-bold transition-all cursor-pointer"
          >
            <Bot className="w-3.5 h-3.5" />
            <span>Ask AI</span>
          </button>
        </div>
      </div>
    </div>
  );
};
