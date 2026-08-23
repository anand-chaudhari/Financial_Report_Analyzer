import React, { useState } from 'react';
import { Citation } from '../types';
import { BookOpen } from 'lucide-react';

interface CitationBadgeProps {
  citation: Citation;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setShowTooltip(!showTooltip)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-xs font-semibold shadow-sm transition-all duration-200 cursor-pointer active:scale-95"
      >
        <BookOpen className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
        <span>Page {citation.page_number}</span>
      </button>

      {showTooltip && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-72 p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/90 rounded-2xl shadow-2xl text-xs text-slate-800 dark:text-slate-200 z-50 animate-fade-in-up pointer-events-none backdrop-blur-xl">
          <div className="flex items-center justify-between font-bold text-emerald-700 dark:text-emerald-400 mb-1.5">
            <span className="flex items-center gap-1">
              <BookOpen className="w-3.5 h-3.5" />
              Source Context (Page {citation.page_number})
            </span>
          </div>
          <p className="italic text-slate-600 dark:text-slate-300 font-mono text-[11px] leading-relaxed line-clamp-5 bg-slate-50 dark:bg-slate-950/70 p-2 rounded-xl border border-slate-200 dark:border-slate-800">
            "{citation.snippet}"
          </p>
        </div>
      )}
    </div>
  );
};
