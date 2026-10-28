import React, { useState } from 'react';
import {
  Globe,
  ExternalLink,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Calendar,
  FileText,
} from 'lucide-react';
import { SourceMetadata } from '../../services/conversationService';
import { WebSourceItem } from '../../services/chatService';
import { PdfCitation } from './PdfCitation';

interface SourceListProps {
  webSources?: WebSourceItem[];
  pdfSources?: SourceMetadata[];
  onOpenPdfCitation?: (citation: SourceMetadata) => void;
}

/**
 * Extracts a readable domain/publisher name from a URL
 */
const extractDomain = (url: string): string => {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\./, '');
    return host;
  } catch {
    return 'External Source';
  }
};

/**
 * Deduplicates web sources by URL
 */
const deduplicateWebSources = (sources?: WebSourceItem[]): WebSourceItem[] => {
  if (!sources || sources.length === 0) return [];
  const seen = new Set<string>();
  const unique: WebSourceItem[] = [];

  for (const src of sources) {
    if (!src.url) continue;
    const normUrl = src.url.trim().toLowerCase();
    if (!seen.has(normUrl)) {
      seen.add(normUrl);
      unique.push(src);
    }
  }
  return unique;
};

/**
 * Deduplicates PDF sources by page_number + section
 */
const deduplicatePdfSources = (sources?: SourceMetadata[]): SourceMetadata[] => {
  if (!sources || sources.length === 0) return [];
  const seen = new Set<string>();
  const unique: SourceMetadata[] = [];

  for (const src of sources) {
    const page = src.page_number;
    const sec = (src.section || 'General Section').trim().toLowerCase();
    const key = `${page}_${sec}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(src);
    }
  }
  return unique;
};

export const SourceList: React.FC<SourceListProps> = ({
  webSources = [],
  pdfSources = [],
  onOpenPdfCitation,
}) => {
  const [isPdfExpanded, setIsPdfExpanded] = useState<boolean>(true);
  const [isWebExpanded, setIsWebExpanded] = useState<boolean>(true);

  const cleanWebSources = deduplicateWebSources(webSources);
  const cleanPdfSources = deduplicatePdfSources(pdfSources);

  if (cleanWebSources.length === 0 && cleanPdfSources.length === 0) {
    return null;
  }

  return (
    <div className="pt-3 border-t border-slate-200/80 dark:border-slate-800/80 space-y-3">
      {/* 1. Verified PDF Filing Citations Group */}
      {cleanPdfSources.length > 0 && (
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => setIsPdfExpanded(!isPdfExpanded)}
            className="flex items-center justify-between w-full text-[11px] font-extrabold text-slate-600 dark:text-slate-300 uppercase tracking-wider hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              <span>Verified Report Citations ({cleanPdfSources.length})</span>
            </span>
            <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
              <span>{isPdfExpanded ? 'Hide' : 'Show'}</span>
              {isPdfExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </span>
          </button>

          {isPdfExpanded && (
            <div className="flex flex-wrap gap-2 pt-1 animate-fade-in">
              {cleanPdfSources.map((citation, idx) => (
                <PdfCitation
                  key={`pdf_${citation.page_number}_${idx}`}
                  citation={citation}
                  onOpenPdf={onOpenPdfCitation}
                  variant="pill"
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* 2. Live Web Sources Group */}
      {cleanWebSources.length > 0 && (
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => setIsWebExpanded(!isWebExpanded)}
            className="flex items-center justify-between w-full text-[11px] font-extrabold text-blue-600 dark:text-blue-400 uppercase tracking-wider hover:text-blue-700 dark:hover:text-blue-300 transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-blue-500" />
              <span>Live Web Sources ({cleanWebSources.length})</span>
            </span>
            <span className="flex items-center gap-1 text-[10px] font-bold text-blue-600 dark:text-blue-400">
              <span>{isWebExpanded ? 'Hide' : 'Show'}</span>
              {isWebExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </span>
          </button>

          {isWebExpanded && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 animate-fade-in">
              {cleanWebSources.map((ws, idx) => {
                const domain = ws.publisher || extractDomain(ws.url);
                return (
                  <a
                    key={`web_${idx}`}
                    href={ws.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-3 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-blue-500/50 hover:bg-blue-50/40 dark:hover:bg-blue-950/20 transition-all text-xs group block shadow-xs"
                  >
                    <div className="flex items-center justify-between gap-1.5 mb-1">
                      <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-700 dark:text-blue-300 font-bold text-[10px] truncate max-w-[150px]">
                        {domain}
                      </span>
                      {ws.date && (
                        <span className="text-[10px] text-slate-400 flex items-center gap-1 flex-shrink-0">
                          <Calendar className="w-3 h-3" />
                          {ws.date}
                        </span>
                      )}
                      <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-blue-500 flex-shrink-0 ml-auto" />
                    </div>

                    <h4 className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 text-xs truncate leading-snug">
                      {ws.title || domain}
                    </h4>

                    {ws.snippet && (
                      <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                        {ws.snippet}
                      </p>
                    )}

                    <div className="mt-1.5 text-[10px] font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-1 group-hover:underline">
                      <span>View original source</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </div>
                  </a>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SourceList;

