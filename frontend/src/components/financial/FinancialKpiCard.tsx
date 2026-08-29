import React from 'react';
import {
  LucideIcon,
  TrendingUp,
  TrendingDown,
  Minus,
  BookOpen,
  DollarSign,
  PieChart,
  Percent,
  Building2,
  Scale,
  Coins,
  Layers,
} from 'lucide-react';
import { OverviewMetricItem } from '../../types/financial';

export interface FinancialKpiCardProps {
  title: string;
  item?: OverviewMetricItem;
  currentYearLabel?: string;
  previousYearLabel?: string;
  icon?: LucideIcon;
  color?: 'emerald' | 'cyan' | 'blue' | 'indigo' | 'violet' | 'amber' | 'rose';
  onOpenCitation?: (page: number) => void;
}

// Utility to parse numeric value from financial string (e.g. "₹12,450 Cr", "$45.2M", "14.50")
function parseNumeric(val?: string): number | null {
  if (!val || val.toLowerCase().includes('not available') || val.toLowerCase().includes('n/a')) {
    return null;
  }
  const clean = val.replace(/[^0-9.-]/g, '');
  const num = parseFloat(clean);
  return isNaN(num) ? null : num;
}

export const FinancialKpiCard: React.FC<FinancialKpiCardProps> = ({
  title,
  item,
  currentYearLabel = 'FY2026',
  previousYearLabel = 'FY2025',
  icon: Icon = DollarSign,
  color = 'emerald',
  onOpenCitation,
}) => {
  const currentVal = item?.fy2026_value && !item.fy2026_value.toLowerCase().includes('not available')
    ? item.fy2026_value
    : 'N/A';

  const prevVal = item?.fy2025_value && !item.fy2025_value.toLowerCase().includes('not available')
    ? item.fy2025_value
    : 'N/A';

  // Calculate Absolute & Percentage Variance if calculable
  const curNum = parseNumeric(currentVal);
  const prevNum = parseNumeric(prevVal);

  let absChangeStr = 'N/A';
  let pctChangeStr = item?.growth && !item.growth.toLowerCase().includes('not available') ? item.growth : 'N/A';
  let isPositive: boolean | null = null;

  if (curNum !== null && prevNum !== null && prevNum !== 0) {
    const diff = curNum - prevNum;
    const sign = diff >= 0 ? '+' : '';
    absChangeStr = `${sign}${diff.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    if (item?.unit) {
      absChangeStr += ` ${item.unit}`;
    }

    if (pctChangeStr === 'N/A') {
      const pct = (diff / Math.abs(prevNum)) * 100;
      pctChangeStr = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
    }
    isPositive = diff >= 0;
  } else if (pctChangeStr !== 'N/A') {
    isPositive = pctChangeStr.startsWith('+') || (!pctChangeStr.startsWith('-') && !pctChangeStr.toLowerCase().includes('decline'));
  }

  const colorStyles = {
    emerald: {
      iconBg: 'bg-emerald-500/10 dark:bg-emerald-500/15',
      iconColor: 'text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
    },
    cyan: {
      iconBg: 'bg-cyan-500/10 dark:bg-cyan-500/15',
      iconColor: 'text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
    },
    blue: {
      iconBg: 'bg-blue-500/10 dark:bg-blue-500/15',
      iconColor: 'text-blue-600 dark:text-blue-400 border-blue-500/20',
    },
    indigo: {
      iconBg: 'bg-indigo-500/10 dark:bg-indigo-500/15',
      iconColor: 'text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
    },
    violet: {
      iconBg: 'bg-violet-500/10 dark:bg-violet-500/15',
      iconColor: 'text-violet-600 dark:text-violet-400 border-violet-500/20',
    },
    amber: {
      iconBg: 'bg-amber-500/10 dark:bg-amber-500/15',
      iconColor: 'text-amber-600 dark:text-amber-400 border-amber-500/20',
    },
    rose: {
      iconBg: 'bg-rose-500/10 dark:bg-rose-500/15',
      iconColor: 'text-rose-600 dark:text-rose-400 border-rose-500/20',
    },
  }[color] || {
    iconBg: 'bg-emerald-500/10 dark:bg-emerald-500/15',
    iconColor: 'text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  };

  return (
    <div className="relative p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all duration-200 flex flex-col justify-between group min-w-0">
      {/* Header: Title & Icon */}
      <div className="flex items-start justify-between gap-3 min-w-0">
        <span className="text-[11px] font-extrabold text-slate-500 dark:text-slate-400 uppercase tracking-wider leading-snug">
          {title}
        </span>
        <div
          className={`p-2.5 rounded-2xl border ${colorStyles.iconBg} ${colorStyles.iconColor} transition-transform group-hover:scale-105 duration-200 flex-shrink-0`}
        >
          <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
      </div>

      {/* Main KPI Value (Current Fiscal Year) */}
      <div className="mt-3 space-y-2">
        <div className="space-y-0.5">
          <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase">
            {currentYearLabel} (Current)
          </span>
          <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight break-words">
            {currentVal}
          </div>
        </div>

        {/* Previous Fiscal Year */}
        <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
          <span className="text-slate-500 dark:text-slate-400 text-[11px]">
            {previousYearLabel} (Prior):
          </span>
          <span className="font-bold text-slate-700 dark:text-slate-300 text-xs">
            {prevVal}
          </span>
        </div>

        {/* Variance & Percentage Change Row */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <div className="flex items-center gap-1.5">
            {isPositive === true && (
              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <TrendingUp className="w-3 h-3" />
                <span>↑ {pctChangeStr}</span>
              </span>
            )}
            {isPositive === false && (
              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                <TrendingDown className="w-3 h-3" />
                <span>↓ {pctChangeStr}</span>
              </span>
            )}
            {isPositive === null && (
              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                <Minus className="w-3 h-3" />
                <span>{pctChangeStr}</span>
              </span>
            )}
          </div>

          {/* Absolute Change or Citation */}
          {absChangeStr !== 'N/A' && (
            <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400 truncate">
              Δ {absChangeStr}
            </span>
          )}

          {item?.page_number && item.page_number > 0 && (
            <button
              type="button"
              onClick={() => onOpenCitation?.(item.page_number!)}
              className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 hover:text-emerald-500 dark:text-slate-400 dark:hover:text-emerald-400 transition-colors"
              title={`View on Page ${item.page_number}`}
            >
              <BookOpen className="w-3 h-3 text-emerald-500" />
              <span>P.{item.page_number}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FinancialKpiCard;
