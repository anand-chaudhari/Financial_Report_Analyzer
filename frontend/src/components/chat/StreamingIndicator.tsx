import React from 'react';
import { Bot, Sparkles } from 'lucide-react';

interface StreamingIndicatorProps {
  status?: string;
  hasStartedTokens?: boolean;
}

export const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({
  status = 'Analyzing report filing & synthesizing response...',
  hasStartedTokens = false,
}) => {
  if (hasStartedTokens) {
    // Subtle trailing typing indicator when tokens are actively streaming
    return (
      <span className="inline-flex items-center ml-1 align-baseline">
        <span className="w-1.5 h-3.5 bg-emerald-500 rounded-sm animate-pulse" />
      </span>
    );
  }

  // Pre-token waiting state
  return (
    <div className="flex items-center gap-3 py-2 px-1 text-xs text-slate-500 dark:text-slate-400 animate-fade-in">
      <div className="flex items-center gap-1.5 p-1.5 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        <Bot className="w-4 h-4 animate-pulse" />
      </div>

      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1">
          <div
            className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"
            style={{ animationDelay: '0ms' }}
          />
          <div
            className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"
            style={{ animationDelay: '150ms' }}
          />
          <div
            className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"
            style={{ animationDelay: '300ms' }}
          />
        </div>
        <span className="font-semibold text-slate-700 dark:text-slate-300">
          {status}
        </span>
      </div>
    </div>
  );
};

export default StreamingIndicator;

