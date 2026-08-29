import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  FileWarning,
  TrendingDown,
  Scale,
  DollarSign,
  BookOpen,
  RefreshCw,
  Info,
  CheckCircle2,
  ShieldCheck,
  Building,
  Activity,
  Layers,
} from 'lucide-react';
import { financialService } from '../../services/financialService';
import { RiskAnalysisResponse, RiskItem } from '../../types/financial';

interface RiskAnalysisSectionProps {
  reportId: string;
  companyName?: string;
  onOpenCitation?: (page: number) => void;
}

export const RiskAnalysisSection: React.FC<RiskAnalysisSectionProps> = ({
  reportId,
  companyName,
  onOpenCitation,
}) => {
  const [data, setData] = useState<RiskAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'REPORTED' | 'INDICATOR'>('ALL');

  const fetchRisks = async () => {
    if (!reportId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await financialService.getRiskAnalysis(reportId);
      setData(res);
    } catch (err: any) {
      console.warn('Could not fetch risk analysis:', err);
      setError('Risk analysis could not be retrieved.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRisks();
  }, [reportId]);

  const reportedList = data?.reported_risks || [];
  const indicatorList = data?.financial_indicators || [];
  const allList = [...reportedList, ...indicatorList];

  const displayedList =
    activeFilter === 'REPORTED'
      ? reportedList
      : activeFilter === 'INDICATOR'
      ? indicatorList
      : allList;

  const highCount = allList.filter((r) => r.severity?.toLowerCase() === 'high').length;
  const mediumCount = allList.filter((r) => r.severity?.toLowerCase() === 'medium').length;

  const renderSeverityBadge = (severity?: string) => {
    const sev = (severity || 'medium').toLowerCase();
    if (sev === 'high') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
          <AlertTriangle className="w-3 h-3" />
          <span>High Severity</span>
        </span>
      );
    }
    if (sev === 'medium') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
          <FileWarning className="w-3 h-3" />
          <span>Medium Severity</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
        <Info className="w-3 h-3" />
        <span>Low / Informational</span>
      </span>
    );
  };

  const renderCategoryBadge = (category: string) => {
    const isReported = category.toLowerCase().includes('reported');
    return (
      <span
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-extrabold ${
          isReported
            ? 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20'
            : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20'
        }`}
      >
        {isReported ? <Building className="w-3 h-3" /> : <Activity className="w-3 h-3" />}
        <span>{category}</span>
      </span>
    );
  };

  return (
    <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800/80 pb-5">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs font-bold">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Financial Risk & Red Flag Analyzer</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Risks & Red Flags: {data?.company_name || companyName || 'Corporate Filing'}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Factual risks explicitly disclosed by management and key financial vulnerability indicators.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {highCount > 0 && (
            <span className="px-3 py-1 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs font-bold">
              {highCount} High Priority
            </span>
          )}
          <button
            onClick={fetchRisks}
            disabled={loading}
            className="px-3.5 py-2 rounded-2xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
            title="Re-analyze financial risks"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Analyzing...' : 'Re-Analyze Risks'}</span>
          </button>
        </div>
      </div>

      {/* Executive Risk Summary */}
      {data?.risk_summary && (
        <div className="p-4 sm:p-5 rounded-2xl bg-rose-500/5 dark:bg-rose-950/20 border border-rose-500/20 text-xs sm:text-sm leading-relaxed text-slate-800 dark:text-slate-200 space-y-1">
          <div className="flex items-center gap-2 font-bold text-rose-700 dark:text-rose-400 text-xs uppercase tracking-wider">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Executive Risk Overview</span>
          </div>
          <p className="text-slate-700 dark:text-slate-300 pt-0.5">{data.risk_summary}</p>
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
        <button
          onClick={() => setActiveFilter('ALL')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeFilter === 'ALL'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
          }`}
        >
          All Risks ({allList.length})
        </button>

        <button
          onClick={() => setActiveFilter('REPORTED')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
            activeFilter === 'REPORTED'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
          }`}
        >
          <Building className="w-3.5 h-3.5" />
          <span>Reported Risks ({reportedList.length})</span>
        </button>

        <button
          onClick={() => setActiveFilter('INDICATOR')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
            activeFilter === 'INDICATOR'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Financial Indicators / Observations ({indicatorList.length})</span>
        </button>
      </div>

      {/* Risks Grid */}
      {displayedList.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
          {displayedList.map((risk, idx) => (
            <div
              key={idx}
              className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between space-y-4"
            >
              {/* Badges & Title */}
              <div className="space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {renderCategoryBadge(risk.category)}
                    {renderSeverityBadge(risk.severity)}
                  </div>

                  {risk.page_number && risk.page_number > 0 && (
                    <button
                      type="button"
                      onClick={() => onOpenCitation?.(risk.page_number!)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-500/50 text-slate-700 dark:text-slate-300 font-bold text-[10px] transition-colors cursor-pointer"
                      title={`View Source on Page ${risk.page_number}`}
                    >
                      <BookOpen className="w-3 h-3 text-emerald-500" />
                      <span>Page {risk.page_number}</span>
                    </button>
                  )}
                </div>

                <h3 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white leading-snug">
                  {risk.title}
                </h3>

                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {risk.explanation}
                </p>
              </div>

              {/* Supporting Financial Evidence */}
              {risk.supporting_evidence && (
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                    Supporting Financial Evidence • {risk.section || 'Filing Disclosures'}
                  </span>
                  <p className="text-[11px] font-medium text-slate-800 dark:text-slate-200 leading-relaxed font-mono">
                    {risk.supporting_evidence}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 text-center rounded-2xl bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-xs">
          {loading ? 'Analyzing report for disclosed risks...' : 'No specific high-severity risks identified in this category.'}
        </div>
      )}

      {/* Grounding & Non-Investment Disclaimer */}
      <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[11px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
          <span>Factual Grounding • Strict separation between reported management risks and financial indicators.</span>
        </span>
        <span className="text-[10px] italic text-slate-500 dark:text-slate-400">
          Disclaimer: This analysis does not provide investment or financial trading recommendations.
        </span>
      </div>
    </div>
  );
};

export default RiskAnalysisSection;
