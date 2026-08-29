import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  RefreshCw,
  Sparkles,
  ArrowRightLeft,
} from 'lucide-react';
import { financialService } from '../../services/financialService';
import { FinancialOverviewData } from '../../types/financial';
import { FinancialKpiGrid } from './FinancialKpiGrid';
import { YearOverYearComparisonSection } from './YearOverYearComparisonSection';
import { RiskAnalysisSection } from './RiskAnalysisSection';

interface FinancialOverviewSectionProps {
  reportId: string;
  companyName?: string;
  financialYear?: string;
  onOpenCitation?: (page: number) => void;
}

export const FinancialOverviewSection: React.FC<FinancialOverviewSectionProps> = ({
  reportId,
  companyName,
  financialYear,
  onOpenCitation,
}) => {
  const [data, setData] = useState<FinancialOverviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    if (!reportId) return;
    setLoading(true);
    setError(null);
    try {
      const overview = await financialService.getFinancialOverview(reportId);
      setData(overview);
    } catch (err: any) {
      console.warn('Could not fetch financial overview:', err);
      setError('Financial overview extraction is processing or not available.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, [reportId]);

  const p1 = data?.reporting_periods?.[0] || 'FY2025';
  const p2 = data?.reporting_periods?.[1] || 'FY2026';

  return (
    <div className="space-y-6">
      {/* Header & Refresh Toolbar */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800/80 pb-5">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Grounded Financial Intelligence</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Financial Overview: {data?.company_name || companyName || 'Corporate Filing'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Multi-period financial reporting ({p1} vs {p2}) strictly verified from uploaded filing context.
            </p>
          </div>

          <button
            onClick={fetchOverview}
            disabled={loading}
            className="self-start sm:self-auto px-4 py-2.5 rounded-2xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
            title="Re-extract financial overview"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Extracting...' : 'Refresh Overview'}</span>
          </button>
        </div>

        {/* Narrative Summary if available */}
        {data?.executive_overview && (
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            {data.executive_overview}
          </div>
        )}

        {/* Feature 3: Financial KPI Dashboard Cards Grid */}
        <FinancialKpiGrid data={data} onOpenCitation={onOpenCitation} />
      </div>

      {/* Feature 4: Year-over-Year (YoY) Financial Comparison Section */}
      <YearOverYearComparisonSection data={data} onOpenCitation={onOpenCitation} />

      {/* Feature 6: Financial Risk & Red Flag Analyzer */}
      <RiskAnalysisSection
        reportId={reportId}
        companyName={data?.company_name || companyName}
        onOpenCitation={onOpenCitation}
      />
    </div>
  );
};

export default FinancialOverviewSection;
