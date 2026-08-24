import React from 'react';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

export interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  description?: string;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'emerald' | 'cyan' | 'indigo' | 'amber' | 'rose' | 'blue' | 'violet';
  iconColor?: 'emerald' | 'cyan' | 'indigo' | 'amber' | 'rose' | 'blue' | 'violet';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  changeType = 'positive',
  description,
  subtitle,
  icon: Icon,
  color,
  iconColor,
}) => {
  const chosenColor = color || iconColor || 'emerald';

  const colorMap = {
    emerald: {
      bg: 'bg-emerald-500/10 dark:bg-emerald-500/15',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-500/20 dark:border-emerald-500/30',
    },
    blue: {
      bg: 'bg-blue-500/10 dark:bg-blue-500/15',
      text: 'text-blue-600 dark:text-blue-400',
      border: 'border-blue-500/20 dark:border-blue-500/30',
    },
    cyan: {
      bg: 'bg-cyan-500/10 dark:bg-cyan-500/15',
      text: 'text-cyan-600 dark:text-cyan-400',
      border: 'border-cyan-500/20 dark:border-cyan-500/30',
    },
    indigo: {
      bg: 'bg-indigo-500/10 dark:bg-indigo-500/15',
      text: 'text-indigo-600 dark:text-indigo-400',
      border: 'border-indigo-500/20 dark:border-indigo-500/30',
    },
    violet: {
      bg: 'bg-violet-500/10 dark:bg-violet-500/15',
      text: 'text-violet-600 dark:text-violet-400',
      border: 'border-violet-500/20 dark:border-violet-500/30',
    },
    amber: {
      bg: 'bg-amber-500/10 dark:bg-amber-500/15',
      text: 'text-amber-600 dark:text-amber-400',
      border: 'border-amber-500/20 dark:border-amber-500/30',
    },
    rose: {
      bg: 'bg-rose-500/10 dark:bg-rose-500/15',
      text: 'text-rose-600 dark:text-rose-400',
      border: 'border-rose-500/20 dark:border-rose-500/30',
    },
  };

  const selectedColor = colorMap[chosenColor] || colorMap.emerald;
  const subText = subtitle || description;

  return (
    <div className="relative p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all duration-200 flex flex-col justify-between group min-w-0">
      <div className="flex items-start justify-between gap-3 min-w-0">
        <span className="text-[11px] font-extrabold text-slate-500 dark:text-slate-400 tracking-wider uppercase leading-snug whitespace-normal break-words">
          {title}
        </span>
        <div
          className={`p-2.5 rounded-xl border ${selectedColor.bg} ${selectedColor.border} ${selectedColor.text} transition-transform group-hover:scale-105 duration-200 flex-shrink-0`}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-3 space-y-1 min-w-0">
        <div className="flex items-baseline gap-2 min-w-0 flex-wrap">
          <span className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight break-words">
            {value}
          </span>
          {change && (
            <span
              className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md flex-shrink-0 ${
                changeType === 'positive'
                  ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                  : changeType === 'negative'
                  ? 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              {changeType === 'positive' && <TrendingUp className="w-3 h-3" />}
              {changeType === 'negative' && <TrendingDown className="w-3 h-3" />}
              {changeType === 'neutral' && <Minus className="w-3 h-3" />}
              <span>{change}</span>
            </span>
          )}
        </div>

        {subText && (
          <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium leading-normal whitespace-normal break-words">
            {subText}
          </p>
        )}
      </div>
    </div>
  );
};
