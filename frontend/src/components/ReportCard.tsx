import React from 'react';
import { useNavigate } from 'react-router-dom';
import { MockReport } from '../utils/mockData';
import { formatBytes, formatDate } from '../utils/formatters';
import {
  FileText,
  CheckCircle2,
  Clock,
  ArrowRight,
  BarChart3,
  Bot,
  Building2,
  AlertCircle,
} from 'lucide-react';

interface ReportCardProps {
  report: MockReport;
  onDelete?: (id: string) => void;
}

export const ReportCard: React.FC<ReportCardProps> = ({ report, onDelete }) => {
  const navigate = useNavigate();

  const getFilingBadgeColor = (type: MockReport['filingType']) => {
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
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            Ready
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30">
            <Clock className="w-3 h-3 animate-spin" />
            Processing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/30">
            <AlertCircle className="w-3 h-3" />
            Error
          </span>
        );
    }
  };

  return (
    <div className="group relative bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 rounded-2xl p-5 transition-all duration-200 flex flex-col justify-between shadow-sm hover:shadow-md">
      <div>
        {/* Header: Ticker, Company, Filing Type & Status */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs tracking-wider flex-shrink-0 group-hover:scale-105 transition-transform">
              {report.ticker || 'DOC'}
            </div>
            <div className="overflow-hidden">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate" title={report.company}>
                  {report.company}
                </h3>
                <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${getFilingBadgeColor(report.filingType)}`}>
                  {report.filingType}
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5" title={report.filename}>
                {report.filename}
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

        {/* Tags */}
        {report.tags && report.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {report.tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[10px] font-medium text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer Info & Action buttons */}
      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-2">
          <span>{report.totalPages} pages</span>
          <span>•</span>
          <span>{formatBytes(report.fileSize)}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => navigate(`/analytics?report=${report.id}`)}
            title="View Visual Analytics"
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-400 hover:bg-cyan-50 dark:hover:bg-cyan-500/10 transition-colors cursor-pointer"
          >
            <BarChart3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => navigate(`/reports/${report.id}`)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs font-bold transition-all cursor-pointer"
          >
            <Bot className="w-3.5 h-3.5" />
            <span>Ask AI</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};
