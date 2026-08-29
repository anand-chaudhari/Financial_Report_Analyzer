import React, { useState } from 'react';
import { Citation } from '../types';
import { ShieldCheck, BookOpen } from 'lucide-react';

interface CitationBadgeProps {
  citation: Citation;
  onClick?: () => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation, onClick }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  const sectionName = citation.section || 'Financial Statement';
  const displayLabel = sectionName && sectionName !== 'Financial Statement' && sectionName.length < 35
    ? `Source: Page ${citation.page_number} — ${sectionName}`
    : `Source: Page ${citation.page_number}`;

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={onClick ? onClick : () => setShowTooltip(!showTooltip)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 text-xs font-semibold shadow-xs transition-all duration-200 cursor-pointer active:scale-95 group"
        title={`Verified Citation: Page ${citation.page_number}`}
      >
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 group-hover:scale-110 transition-transform flex-shrink-0" />
        <span className="truncate max-w-[260px]">{displayLabel}</span>
      </button>

      {showTooltip && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-80 p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/90 rounded-2xl shadow-2xl text-xs text-slate-800 dark:text-slate-200 z-50 animate-fade-in-up pointer-events-none backdrop-blur-xl">
          <div className="flex items-center justify-between font-bold text-emerald-700 dark:text-emerald-400 mb-1.5">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              Verified Source: Page {citation.page_number}
            </span>
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
              {citation.section || 'Report Citation'}
            </span>
          </div>
          <p className="italic text-slate-600 dark:text-slate-300 font-mono text-[11px] leading-relaxed line-clamp-5 bg-slate-50 dark:bg-slate-950/70 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800">
            &quot;{citation.snippet}&quot;
          </p>
        </div>
      )}
    </div>
  );
};

export default CitationBadge;
