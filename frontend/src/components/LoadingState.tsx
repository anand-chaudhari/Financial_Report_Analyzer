import React from 'react';

export interface LoadingStateProps {
  type?: 'card-grid' | 'list' | 'spinner';
  count?: number;
  label?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  type = 'card-grid',
  count = 3,
  label = 'Loading financial insights...',
}) => {
  if (type === 'spinner') {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-3">
        <div className="w-8 h-8 border-3 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
      </div>
    );
  }

  if (type === 'list') {
    return (
      <div className="space-y-3 w-full animate-pulse">
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between"
          >
            <div className="flex items-center gap-3 w-3/4">
              <div className="w-9 h-9 rounded-lg bg-slate-200 dark:bg-slate-800 flex-shrink-0" />
              <div className="space-y-2 flex-1">
                <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-1/3" />
                <div className="h-2.5 bg-slate-100 dark:bg-slate-800/60 rounded w-1/2" />
              </div>
            </div>
            <div className="h-7 w-20 bg-slate-200 dark:bg-slate-800 rounded-lg" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 w-full animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-800" />
              <div className="space-y-2">
                <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-24" />
                <div className="h-2 bg-slate-100 dark:bg-slate-800/60 rounded w-32" />
              </div>
            </div>
            <div className="h-5 w-14 bg-slate-200 dark:bg-slate-800 rounded-full" />
          </div>
          <div className="h-14 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-100 dark:border-slate-800/50" />
          <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="h-2.5 bg-slate-200 dark:bg-slate-800 rounded w-20" />
            <div className="h-6 w-16 bg-slate-200 dark:bg-slate-800 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
};
