import React, { useState } from 'react';
import {
  X,
  Maximize2,
  Minimize2,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  FileText,
  ExternalLink,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { SourceMetadata } from '../../types/financial';
import { API_BASE_URL } from '../../utils/constants';

interface PdfSplitViewerProps {
  documentId: string;
  fileName?: string;
  storageUrl?: string;
  initialPage?: number;
  highlightSource?: SourceMetadata | null;
  onClose: () => void;
}

export const PdfSplitViewer: React.FC<PdfSplitViewerProps> = ({
  fileName = 'Financial Filing.pdf',
  storageUrl,
  initialPage = 1,
  highlightSource,
  onClose,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(highlightSource?.page_number || initialPage);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [zoom, setZoom] = useState<number>(100);

  // Derive source PDF URL
  const serverOrigin = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
  const pdfUrl = storageUrl
    ? (storageUrl.startsWith('http') ? storageUrl : `${serverOrigin}${storageUrl}`)
    : `${API_BASE_URL}/documents/preview/${encodeURIComponent(fileName)}#page=${currentPage}`;

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => prev + 1);
  };

  return (
    <div
      className={`flex flex-col bg-slate-900 border border-slate-800 transition-all duration-300 shadow-2xl z-30 rounded-3xl overflow-hidden ${
        isExpanded
          ? 'fixed inset-2 sm:inset-4 z-50 rounded-2xl h-[calc(100vh-16px)] sm:h-[calc(100vh-32px)]'
          : 'w-full lg:w-[480px] xl:w-[560px] 2xl:w-[640px] h-[520px] lg:h-full min-h-[420px]'
      }`}
    >
      {/* Top Header Bar */}
      <div className="p-3.5 px-4 bg-slate-950/90 border-b border-slate-800/80 flex items-center justify-between gap-3 text-white">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400">
            <FileText className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-bold truncate">{fileName}</h3>
            <span className="text-[10px] text-slate-400">Live In-Document Split View</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-slate-800/60 rounded-lg p-0.5 border border-slate-700/50 mr-1">
            <button
              onClick={() => setZoom((z) => Math.max(50, z - 15))}
              className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700/50"
              title="Zoom Out"
            >
              <ZoomOut className="w-3 h-3" />
            </button>
            <span className="text-[10px] font-mono px-1 text-slate-300">{zoom}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(200, z + 15))}
              className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700/50"
              title="Zoom In"
            >
              <ZoomIn className="w-3 h-3" />
            </button>
          </div>

          {/* Expand / Minimize */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            title={isExpanded ? 'Restore Split' : 'Expand Fullscreen'}
          >
            {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
            title="Close Split View"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Floating Citation Excerpt Callout */}
      {highlightSource && (
        <div className="p-3 bg-emerald-950/40 border-b border-emerald-500/30 flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-[11px] font-extrabold text-emerald-300">
                Verified Citation • Page {highlightSource.page_number}
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-medium truncate max-w-[140px]">
                {highlightSource.section || 'Statement Excerpt'}
              </span>
            </div>
            <p className="text-[11px] text-slate-300 line-clamp-2 leading-relaxed italic bg-black/20 p-1.5 rounded-lg border border-emerald-500/10">
              "{highlightSource.snippet || 'Supporting statement data'}"
            </p>
          </div>
        </div>
      )}

      {/* PDF View Container */}
      <div className="flex-1 w-full bg-slate-950 relative overflow-hidden flex flex-col">
        <iframe
          key={`${pdfUrl}_${currentPage}_${zoom}`}
          src={`${pdfUrl}#page=${currentPage}&zoom=${zoom}`}
          className="w-full h-full border-0 bg-slate-900"
          title="PDF Document Viewer"
        />
      </div>

      {/* Bottom Page Navigation Bar */}
      <div className="p-2.5 px-4 bg-slate-950 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-1.5">
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
            className="p-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] font-medium text-slate-300">
            Page <strong className="text-white">{currentPage}</strong>
          </span>
          <button
            onClick={handleNextPage}
            className="p-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] text-emerald-400 hover:underline flex items-center gap-1 font-semibold"
        >
          <span>Open Full PDF in New Tab</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};
