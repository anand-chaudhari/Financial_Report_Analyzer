import React from 'react';
import { ShieldCheck, FileText, ChevronRight } from 'lucide-react';
import { SourceMetadata } from '../../services/conversationService';

interface PdfCitationProps {
  citation: SourceMetadata;
  onOpenPdf?: (citation: SourceMetadata) => void;
  variant?: 'pill' | 'card' | 'inline';
}

export const PdfCitation: React.FC<PdfCitationProps> = ({
  citation,
  onOpenPdf,
  variant = 'pill',
}) => {
  const pageNum = citation.page_number;
  const sectionName = (citation.section || 'Report Disclosure').trim();
  const docName = citation.document_name || 'Annual Report';

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenPdf?.(citation);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onOpenPdf?.(citation);
    }
  };

  if (variant === 'card') {
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className="p-3 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all text-xs cursor-pointer shadow-xs group block text-left"
        title={`View ${docName}, Page ${pageNum}: ${sectionName}`}
      >
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-bold text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{docName}, page {pageNum}</span>
          </div>
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold">
            Verified Filing
          </span>
        </div>
        <p className="font-semibold text-slate-800 dark:text-slate-200 text-xs truncate">
          {sectionName}
        </p>
        {citation.snippet && (
          <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed italic bg-slate-50 dark:bg-slate-950 p-1.5 rounded-lg border border-slate-100 dark:border-slate-800/60">
            "{citation.snippet}"
          </p>
        )}
      </div>
    );
  }

  // Default 'pill' variant
  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/60 hover:bg-emerald-500/10 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-all cursor-pointer shadow-xs group align-baseline"
      title={`Open ${docName} at page ${pageNum}: ${sectionName}`}
    >
      <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 group-hover:scale-110 transition-transform" />
      <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-bold text-[10px]">
        Page {pageNum}
      </span>
      <span className="truncate max-w-[160px] sm:max-w-[220px] text-[11px]">
        {sectionName}
      </span>
      <ChevronRight className="w-3 h-3 text-slate-400 group-hover:text-emerald-500 flex-shrink-0 ml-0.5" />
    </button>
  );
};

export default PdfCitation;

