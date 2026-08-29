import React, { useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  DollarSign,
  PieChart,
  Percent,
  Building2,
  Scale,
  Coins,
  Layers,
  Sparkles,
  BookOpen,
  ArrowRightLeft,
  ShieldCheck,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { FinancialOverviewData, OverviewMetricItem } from '../../types/financial';
import { useTheme } from '../../hooks/useTheme';

interface YearOverYearComparisonSectionProps {
  data?: FinancialOverviewData | null;
  onOpenCitation?: (page: number) => void;
}

interface ComputedYoYRow {
  key: string;
  metric: string;
  previousYear: string;
  currentYear: string;
  change: string;
  changePercent: string;
  isPositive: boolean | null;
  pageNumber?: number;
  icon: any;
  chartPrev?: number;
  chartCurr?: number;
  unit?: string;
}

// Utility to parse numeric values from financial strings (e.g. "₹12,450 Cr", "$45.2M", "14.50", "12.4%")
function extractNumber(val?: string): number | null {
  if (!val || val.toLowerCase().includes('not available') || val.toLowerCase().includes('n/a')) {
    return null;
  }
  const clean = val.replace(/[^0-9.-]/g, '');
  const num = parseFloat(clean);
  return isNaN(num) ? null : num;
}

// Utility to extract prefix symbol (e.g. ₹, $)
function extractPrefix(val?: string): string {
  if (!val) return '';
  if (val.includes('₹')) return '₹';
  if (val.includes('$')) return '$';
  if (val.includes('€')) return '€';
  if (val.includes('£')) return '£';
  return '';
}

export const YearOverYearComparisonSection: React.FC<YearOverYearComparisonSectionProps> = ({
  data,
  onOpenCitation,
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const p1 = data?.reporting_periods?.[0] || 'Previous Year';
  const p2 = data?.reporting_periods?.[1] || 'Current Year';

  const rows: ComputedYoYRow[] = useMemo(() => {
    const rawMetrics: { key: string; label: string; item?: OverviewMetricItem; icon: any }[] = [
      { key: 'rev', label: 'Revenue from Operations', item: data?.revenue, icon: DollarSign },
      { key: 'profit', label: 'Net Profit (PAT)', item: data?.net_profit, icon: TrendingUp },
      { key: 'eps', label: 'Earnings Per Share (EPS)', item: data?.eps, icon: Percent },
      { key: 'assets', label: 'Total Assets', item: data?.total_assets, icon: Building2 },
      { key: 'liab', label: 'Total Liabilities', item: data?.total_liabilities, icon: Scale },
      { key: 'equity', label: 'Shareholders Equity / Net Worth', item: data?.equity, icon: Coins },
      { key: 'cf', label: 'Operating Cash Flow', item: data?.cash_flow, icon: Layers },
    ];

    // Add any important ratios
    if (data?.important_ratios && data.important_ratios.length > 0) {
      data.important_ratios.forEach((r, idx) => {
        rawMetrics.push({
          key: `ratio_${idx}`,
          label: r.name,
          item: r,
          icon: Percent,
        });
      });
    }

    return rawMetrics.map((rm) => {
      const item = rm.item;
      const prevStr = item?.fy2025_value && !item.fy2025_value.toLowerCase().includes('not available')
        ? item.fy2025_value
        : 'N/A';

      const currStr = item?.fy2026_value && !item.fy2026_value.toLowerCase().includes('not available')
        ? item.fy2026_value
        : 'N/A';

      const prevNum = extractNumber(prevStr);
      const currNum = extractNumber(currStr);
      const prefix = extractPrefix(currStr) || extractPrefix(prevStr);
      const unit = item?.unit || '';

      let change = 'N/A';
      let changePercent = item?.growth && !item.growth.toLowerCase().includes('not available') ? item.growth : 'N/A';
      let isPositive: boolean | null = null;

      if (currNum !== null && prevNum !== null) {
        const diff = currNum - prevNum;
        const sign = diff >= 0 ? '+' : '';
        change = `${sign}${prefix}${diff.toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit ? ' ' + unit : ''}`;

        if (prevNum !== 0) {
          const pct = (diff / Math.abs(prevNum)) * 100;
          changePercent = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
        }
        isPositive = diff >= 0;
      } else if (changePercent !== 'N/A') {
        isPositive = changePercent.startsWith('+') || (!changePercent.startsWith('-') && !changePercent.toLowerCase().includes('decline'));
      }

      return {
        key: rm.key,
        metric: rm.label,
        previousYear: prevStr,
        currentYear: currStr,
        change,
        changePercent,
        isPositive,
        pageNumber: item?.page_number,
        icon: rm.icon,
        chartPrev: prevNum !== null ? prevNum : undefined,
        chartCurr: currNum !== null ? currNum : undefined,
        unit,
      };
    });
  }, [data]);

  // Chart data for metrics with valid numbers
  const chartData = useMemo(() => {
    return rows
      .filter((r) => r.chartPrev !== undefined && r.chartCurr !== undefined)
      .map((r) => ({
        name: r.metric.length > 18 ? r.metric.substring(0, 16) + '…' : r.metric,
        fullName: r.metric,
        [p1]: r.chartPrev,
        [p2]: r.chartCurr,
      }));
  }, [rows, p1, p2]);

  const chartTheme = {
    grid: isDark ? '#1e293b' : '#f1f5f9',
    axis: isDark ? '#64748b' : '#94a3b8',
    tooltipBg: isDark ? '#0f172a' : '#ffffff',
    tooltipBorder: isDark ? '#334155' : '#e2e8f0',
    tooltipText: isDark ? '#f8fafc' : '#0f172a',
  };

  return (
    <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800/80 pb-5">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold">
            <ArrowRightLeft className="w-3.5 h-3.5" />
            <span>Year-over-Year (YoY) Financial Comparison</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Compare Years: {p1} vs {p2}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Factual variance and percentage delta calculated directly from verified report statements.
          </p>
        </div>

        {data?.currency && (
          <div className="self-start sm:self-auto px-3.5 py-1.5 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold">
            Currency: <span className="text-emerald-600 dark:text-emerald-400">{data.currency}</span>
          </div>
        )}
      </div>

      {/* Visual YoY Comparison Bar Chart if data available */}
      {chartData.length > 0 && (
        <div className="p-5 rounded-2xl bg-slate-50/70 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-500" />
              <span>Comparative Statement Trajectory ({p1} vs {p2})</span>
            </h3>
          </div>
          <div className="h-64 sm:h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.6} />
                <XAxis dataKey="name" stroke={chartTheme.axis} fontSize={11} interval={0} angle={-15} textAnchor="end" />
                <YAxis stroke={chartTheme.axis} fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartTheme.tooltipBg,
                    borderColor: chartTheme.tooltipBorder,
                    borderRadius: '12px',
                    color: chartTheme.tooltipText,
                    boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey={p1} fill="#64748b" radius={[4, 4, 0, 0]} name={`${p1} (Prior)`} />
                <Bar dataKey={p2} fill="#10b981" radius={[4, 4, 0, 0]} name={`${p2} (Current)`} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Responsive YoY Financial Comparison Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/90 dark:bg-slate-800/90 border-b border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200">
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px]">Metric</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px] text-slate-600 dark:text-slate-300">Previous Year ({p1})</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px] text-emerald-600 dark:text-emerald-400">Current Year ({p2})</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px]">Change (Absolute)</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px]">Change % (YoY)</th>
              <th className="px-4 py-3.5 font-bold uppercase tracking-wider text-[11px]">Source Reference</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900/60">
            {rows.map((row) => {
              const Icon = row.icon;
              return (
                <tr key={row.key} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors">
                  {/* Metric Name */}
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="font-bold text-slate-900 dark:text-slate-100 text-xs sm:text-sm">
                        {row.metric}
                      </span>
                    </div>
                  </td>

                  {/* Previous Year */}
                  <td className="px-4 py-3.5 whitespace-nowrap font-medium text-slate-700 dark:text-slate-300">
                    {row.previousYear === 'N/A' ? (
                      <span className="text-slate-400 italic text-[11px]">N/A</span>
                    ) : (
                      row.previousYear
                    )}
                  </td>

                  {/* Current Year */}
                  <td className="px-4 py-3.5 whitespace-nowrap font-bold text-slate-900 dark:text-white">
                    {row.currentYear === 'N/A' ? (
                      <span className="text-slate-400 italic text-[11px]">N/A</span>
                    ) : (
                      row.currentYear
                    )}
                  </td>

                  {/* Absolute Change */}
                  <td className="px-4 py-3.5 whitespace-nowrap font-semibold">
                    {row.change === 'N/A' ? (
                      <span className="text-slate-400 italic text-[11px]">N/A</span>
                    ) : (
                      <span className={row.isPositive === true ? 'text-emerald-600 dark:text-emerald-400' : row.isPositive === false ? 'text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-300'}>
                        {row.change}
                      </span>
                    )}
                  </td>

                  {/* Percentage Change */}
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    {row.changePercent === 'N/A' ? (
                      <span className="text-slate-400 italic text-[11px]">N/A</span>
                    ) : (
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-extrabold ${
                          row.isPositive === true
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                            : row.isPositive === false
                            ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                        }`}
                      >
                        {row.isPositive === true && <TrendingUp className="w-3 h-3" />}
                        {row.isPositive === false && <TrendingDown className="w-3 h-3" />}
                        {row.isPositive === null && <Minus className="w-3 h-3" />}
                        <span>{row.changePercent}</span>
                      </span>
                    )}
                  </td>

                  {/* Citation Reference */}
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    {row.pageNumber && row.pageNumber > 0 ? (
                      <button
                        type="button"
                        onClick={() => onOpenCitation?.(row.pageNumber!)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-500/50 text-slate-700 dark:text-slate-300 font-bold text-[10px] transition-colors cursor-pointer"
                        title={`View Page ${row.pageNumber}`}
                      >
                        <BookOpen className="w-3 h-3 text-emerald-500" />
                        <span>Page {row.pageNumber}</span>
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

      {/* Grounding & Integrity Note */}
      <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span>Factual Grounding • Percentages calculated only when verified figures exist. Unreported fields display &quot;N/A&quot;.</span>
        </span>
      </div>
    </div>
  );
};

export default YearOverYearComparisonSection;
