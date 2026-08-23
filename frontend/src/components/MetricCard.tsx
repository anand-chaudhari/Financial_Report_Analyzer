import React from 'react';
import { TrendingUp, DollarSign, Activity, FileCheck } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: 'dollar' | 'trend' | 'activity' | 'check';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  trend = 'neutral',
  icon = 'trend',
}) => {
  const getIconConfig = () => {
    switch (icon) {
      case 'dollar':
        return {
          icon: <DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />,
          bg: 'bg-emerald-500/10 border-emerald-500/25',
        };
      case 'activity':
        return {
          icon: <Activity className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />,
          bg: 'bg-cyan-500/10 border-cyan-500/25',
        };
      case 'check':
        return {
          icon: <FileCheck className="w-5 h-5 text-teal-600 dark:text-teal-400" />,
          bg: 'bg-teal-500/10 border-teal-500/25',
        };
      default:
        return {
          icon: <TrendingUp className="w-5 h-5 text-amber-600 dark:text-amber-400" />,
          bg: 'bg-amber-500/10 border-amber-500/25',
        };
    }
  };

  const config = getIconConfig();

  return (
    <div className="group relative bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm dark:shadow-glass hover:border-slate-300 dark:hover:border-slate-700 transition-all duration-300">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </span>
        <div className={`p-2.5 rounded-2xl border ${config.bg} shadow-inner group-hover:scale-110 transition-transform duration-200`}>
          {config.icon}
        </div>
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          {value}
        </span>
        {trend === 'up' && (
          <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-md">
            <TrendingUp className="w-3 h-3" />
            Active
          </span>
        )}
      </div>

      {subtitle && (
        <div className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium">
          {subtitle}
        </div>
      )}
    </div>
  );
};
