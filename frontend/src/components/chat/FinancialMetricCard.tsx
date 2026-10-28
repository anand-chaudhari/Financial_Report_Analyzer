import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, Activity, PieChart, ShieldAlert } from 'lucide-react';

interface FinancialMetricCardProps {
  label: string;
  value: string | number;
  change?: string | number;
  period?: string;
  isPositive?: boolean;
  subtext?: string;
  icon?: React.ReactNode;
}

export const FinancialMetricCard: React.FC<FinancialMetricCardProps> = ({
  label,
  value,
  change,
  period,
  isPositive,
  subtext,
  icon,
}) => {
  const isPos = isPositive !== undefined ? isPositive : (typeof change === 'string' && !change.startsWith('-'));

  return (
    <div className="p-3.5 sm:p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs hover:border-emerald-500/40 transition-all flex flex-col justify-between">
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider truncate">
          {label}
        </span>
        {icon ? (
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            {icon}
          </div>
        ) : (
          period && (
            <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-semibold text-slate-600 dark:text-slate-300">
              {period}
            </span>
          )
        )}
      </div>

      <div className="flex items-baseline justify-between gap-2 mt-1">
        <span className="text-base sm:text-lg font-black text-slate-900 dark:text-white tabular-nums tracking-tight">
          {value}
        </span>
        {change && (
          <span
            className={`px-1.5 py-0.5 rounded text-[11px] font-bold flex items-center gap-0.5 tabular-nums ${
              isPos
                ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                : 'bg-rose-500/15 text-rose-700 dark:text-rose-300'
            }`}
          >
            {isPos ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            <span>{change}</span>
          </span>
        )}
      </div>

      {subtext && (
        <p className="mt-1 text-[10px] text-slate-400 dark:text-slate-500 font-medium truncate">
          {subtext}
        </p>
      )}
    </div>
  );
};

export default FinancialMetricCard;

