import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  ShieldCheck,
  AlertCircle,
  BookOpen,
  RefreshCw,
  Sparkles,
  Layers,
  Percent,
  Coins,
  Scale,
  Building2,
} from 'lucide-react';
import { financialService } from '../../services/financialService';
import { FinancialOverviewData, OverviewMetricItem } from '../../types/financial';

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

  const renderValueCell = (val?: string) => {
    if (!val || val.toLowerCase().includes('not available') || val.trim() === '') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400 dark:text-slate-500 italic">
          <AlertCircle className="w-3 h-3" />
          <span>Not available in the report</span>
        </span>
      );
    }
    return <span className="font-bold text-slate-900 dark:text-white text-xs sm:text-sm">{val}</span>;
  };

  const renderGrowthBadge = (growth?: string) => {
    if (!growth || growth.toLowerCase().includes('not available') || growth.trim() === '') {
      return <span className="text-slate-400 text-xs italic">N/A</span>;
    }

    const isPositive = growth.startsWith('+') || (!growth.startsWith('-') && !growth.toLowerCase().includes('decline'));
    const isNegative = growth.startsWith('-') || growth.toLowerCase().includes('decrease');

    return (
      <span
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-extrabold ${
          isPositive
            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
            : isNegative
            ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
        }`}
      >
        {isPositive && <TrendingUp className="w-3 h-3" />}
        {isNegative && <TrendingDown className="w-3 h-3" />}
        <span>{growth}</span>
      </span>
    );
  };

  const p1 = data?.reporting_periods?.[0] || 'FY2025';
  const p2 = data?.reporting_periods?.[1] || 'FY2026';

  const metricsTable: { key: string; label: string; item?: OverviewMetricItem; icon: any }[] = [
    { key: 'rev', label: 'Revenue from Operations', item: data?.revenue, icon: DollarSign },
    { key: 'prof', label: 'Net Profit (PAT)', item: data?.net_profit, icon: TrendingUp },
    { key: 'eps', label: 'Earnings Per Share (EPS)', item: data?.eps, icon: Percent },
    { key: 'assets', label: 'Total Assets', item: data?.total_assets, icon: Building2 },
    { key: 'liab', label: 'Total Liabilities', item: data?.total_liabilities, icon: Scale },
    { key: 'equity', label: 'Shareholders Equity / Net Worth', item: data?.equity, icon: Coins },
    { key: 'cf', label: 'Operating Cash Flow', item: data?.cash_flow, icon: Layers },
  ];

  return (
    <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800/80 pb-5">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Grounded Financial Overview</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Financial Overview: {data?.company_name || companyName || 'Corporate Filing'}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Automated multi-period extraction ({p1} vs {p2}) strictly verified from uploaded filing context.
          </p>
        </div>

        <button
          onClick={fetchOverview}
          disabled={loading}
          className="self-start sm:self-auto px-3.5 py-2 rounded-2xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
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

      {/* Comparative Multi-Period Financial Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/90 dark:bg-slate-800/90 border-b border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200">
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px]">Financial Metric</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px] text-slate-600 dark:text-slate-300">{p1}</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px] text-emerald-600 dark:text-emerald-400">{p2}</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px]">YoY Growth / Variance</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px]">Source Reference</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900/60">
            {metricsTable.map((row) => {
              const Icon = row.icon;
              const item = row.item;
              return (
                <tr key={row.key} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="font-bold text-slate-900 dark:text-slate-100 text-xs sm:text-sm">{row.label}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">{renderValueCell(item?.fy2025_value)}</td>
                  <td className="px-4 py-3.5 whitespace-nowrap">{renderValueCell(item?.fy2026_value)}</td>
                  <td className="px-4 py-3.5 whitespace-nowrap">{renderGrowthBadge(item?.growth)}</td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    {item?.page_number && item.page_number > 0 ? (
                      <button
                        type="button"
                        onClick={() => onOpenCitation?.(item.page_number!)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-500/50 text-slate-700 dark:text-slate-300 font-bold text-[10px] transition-colors cursor-pointer"
                        title={`View Page ${item.page_number}`}
                      >
                        <BookOpen className="w-3 h-3 text-emerald-500" />
                        <span>Page {item.page_number}</span>
                      </button>
                    ) : (
                      <span className="text-slate-400 text-[10px]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Important Financial Ratios Section */}
      {data?.important_ratios && data.important_ratios.length > 0 && (
        <div className="pt-2 space-y-3">
          <div className="flex items-center gap-2">
            <Percent className="w-4 h-4 text-emerald-500" />
            <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              Reported Financial Ratios
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.important_ratios.map((ratio, idx) => (
              <div
                key={idx}
                className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{ratio.name}</span>
                  {ratio.page_number && (
                    <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                      Page {ratio.page_number}
                    </span>
                  )}
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-extrabold text-slate-900 dark:text-white">
                    {renderValueCell(ratio.fy2026_value || ratio.fy2025_value)}
                  </span>
                  {renderGrowthBadge(ratio.growth)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grounding & Integrity Footer Badge */}
      <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span>Strictly Grounded • Unreported values displayed as &quot;Not available in the report&quot; without invention.</span>
        </span>
      </div>
    </div>
  );
};

export default FinancialOverviewSection;
