import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', label }) => {
  const sizeClasses = {
    sm: 'w-5 h-5 border-2',
    md: 'w-9 h-9 border-[3px]',
    lg: 'w-14 h-14 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center p-6 space-y-3">
      <div className="relative">
        <div
          className={`${sizeClasses[size]} border-emerald-500/20 border-t-emerald-500 border-r-teal-500 rounded-full animate-spin`}
        />
        <div className="absolute inset-0 rounded-full bg-emerald-400/10 blur-sm animate-pulse" />
      </div>
      {label && <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 tracking-wide animate-pulse">{label}</p>}
    </div>
  );
};
