import React from 'react';

interface PageLoadingStateProps {
  label?: string;
  sublabel?: string;
}

export const PageLoadingState: React.FC<PageLoadingStateProps> = ({
  label = 'Loading FinSight AI Workspace...',
  sublabel = 'Preparing grounded financial models & reports',
}) => {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 w-full animate-fade-in">
      {/* Top Animated Progress Indicator Bar */}
      <div className="fixed top-0 left-0 right-0 h-1 bg-slate-200 dark:bg-slate-800 z-50 overflow-hidden">
        <div className="h-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-500 animate-progress-bar w-full" />
      </div>

      {/* Main Glowing Brand Loader */}
      <div className="relative mb-6">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 border border-emerald-500/30 flex items-center justify-center shadow-lg shadow-emerald-500/10">
          <div className="w-10 h-10 border-3 border-emerald-500/30 border-t-emerald-500 border-r-teal-400 rounded-full animate-spin" />
        </div>
        <div className="absolute -inset-2 rounded-3xl bg-emerald-500/10 blur-xl animate-pulse -z-10" />
      </div>

      {/* Loading Labels */}
      <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 tracking-wide animate-pulse">
        {label}
      </h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm text-center">
        {sublabel}
      </p>

      {/* Skeleton Card Grid Placeholder */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full max-w-5xl mt-10 opacity-70 animate-pulse">
        {[1, 2, 3].map((item) => (
          <div
            key={item}
            className="p-5 rounded-2xl bg-white dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 space-y-4 shadow-sm"
          >
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-800" />
              <div className="space-y-2 flex-1">
                <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-2/3" />
                <div className="h-2 bg-slate-100 dark:bg-slate-800/60 rounded w-1/3" />
              </div>
            </div>
            <div className="h-16 bg-slate-100/60 dark:bg-slate-950/60 rounded-xl border border-slate-200/50 dark:border-slate-800/50" />
            <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/60">
              <div className="h-2.5 bg-slate-200 dark:bg-slate-800 rounded w-1/4" />
              <div className="h-5 w-14 bg-slate-200 dark:bg-slate-800 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
