import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message,
  onRetry,
}) => {
  return (
    <div className="p-6 rounded-2xl bg-rose-500/5 dark:bg-rose-500/10 border border-rose-500/20 text-center space-y-3 max-w-lg mx-auto">
      <div className="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center mx-auto">
        <AlertCircle className="w-5 h-5" />
      </div>

      <div className="space-y-1">
        <h4 className="text-sm font-bold text-rose-800 dark:text-rose-300">{title}</h4>
        <p className="text-xs text-rose-600 dark:text-rose-400 leading-relaxed">{message}</p>
      </div>

      {onRetry && (
        <div className="pt-1">
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-xl transition-colors cursor-pointer shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Try Again</span>
          </button>
        </div>
      )}
    </div>
  );
};
