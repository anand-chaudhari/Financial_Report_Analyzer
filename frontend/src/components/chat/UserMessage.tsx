import React from 'react';
import { User } from 'lucide-react';

interface UserMessageProps {
  id: string;
  text: string;
  timestamp: string;
}

export const UserMessage: React.FC<UserMessageProps> = ({ id, text, timestamp }) => {
  return (
    <div className="flex gap-2.5 sm:gap-3 justify-end items-end animate-fade-in group">
      <div className="flex flex-col items-end max-w-[88%] sm:max-w-xl">
        <div className="flex items-center gap-2 mb-1 px-1">
          <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium tabular-nums">
            {timestamp}
          </span>
          <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
            You
          </span>
        </div>

        <div className="p-3.5 sm:p-4 rounded-2xl rounded-br-xs bg-emerald-600 dark:bg-emerald-600 text-white shadow-sm leading-relaxed text-xs sm:text-sm font-medium whitespace-pre-wrap break-words">
          {text}
        </div>
      </div>

      <div className="w-8 h-8 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-200 flex items-center justify-center flex-shrink-0 shadow-xs mb-0.5 border border-slate-300 dark:border-slate-700">
        <User className="w-4 h-4" />
      </div>
    </div>
  );
};

export default UserMessage;

