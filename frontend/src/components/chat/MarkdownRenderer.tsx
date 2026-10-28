import React, { useMemo } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Calculator,
  ShieldCheck,
  ExternalLink,
} from 'lucide-react';
import { SourceMetadata } from '../../services/conversationService';
import { FinancialTableWithChart } from '../common/RichMarkdownRenderer';
import { PdfCitation } from './PdfCitation';

interface MarkdownRendererProps {
  content: string;
  sources?: SourceMetadata[];
  isStreaming?: boolean;
  onOpenPdfCitation?: (citation: SourceMetadata) => void;
}

/**
 * Sanitizes internal developer debugging tokens without altering factual numbers or symbols
 */
export const cleanUserFacingMarkdown = (raw: string): string => {
  if (!raw) return '';

  let text = raw;

  // 1. Strip raw internal evidence markers
  text = text.replace(/\[Evidence\s*\d+\]/gi, '');
  text = text.replace(/Evidence\s*\d+\s*(?:\/|—|-|:)?\s*(?:svgPage|Page)?\s*(\d+)/gi, 'Page $1');
  text = text.replace(/svgPage\s*(\d+)/gi, 'Page $1');

  // 2. Strip internal developer logs and internal IDs
  text = text.replace(
    /\b(?:RAG retrieval returned \d+ chunks?\.?|BM25 ranked[^\n.;]*[.;]?|ChromaDB found[^\n.;]*[.;]?|SSE stream completed[^\n.;]*[.;]?|Intent=[^\s;\n]+;?)/gi,
    ''
  );
  text = text.replace(/\b(?:doc_[a-f0-9]{8,16}|chunk_[a-z0-9_]+)\b/gi, '');

  // 3. Normalize unescaped literal \n sequences if present
  text = text.replace(/\\n/g, '\n');

  // 4. Clean extra spaces
  text = text.replace(/[ \t]{2,}/g, ' ');

  return text;
};

/**
 * Parses inline elements: bold, italic, code, financial amounts (₹, $, €), links, and citations
 */
const renderInlineTokens = (
  text: string,
  sources?: SourceMetadata[],
  onOpenPdfCitation?: (citation: SourceMetadata) => void
): React.ReactNode => {
  if (!text) return null;

  // Regex matches:
  // 1. Citations: [Page X], Source: Page X, Page X — Section
  // 2. Markdown links: [Title](https://...)
  // 3. Bold: **text**
  // 4. Italic: *text* or _text_
  // 5. Inline code: `code`
  // 6. Currencies & percentages: ₹1,234.50, $50M, +12.5%, -4.2%, FY2026, X Crore, X Lakh
  const regex = /(Source:\s*Page\s*\d+(?:\s*—[A-Za-z0-9\s,\.\-&]+)?|\[(?:Page\s*)?\d+(?:\s*—[^\]]+)?\]|\(Page\s*\d+\)|Page\s*\d+\s*—\s*[A-Za-z0-9\s,\.\-&]+|\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|(?:₹|\$|€)\s?[\d,]+(?:\.\d+)?(?:\s*(?:Crore|Cr|Lakh|Million|Billion|Trillion))?|(?:\+|\-)?\d+(?:\.\d+)?%|\bFY\s?20\d{2}\b)/g;

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const matched = match[0];
    const index = match.index;

    if (index > lastIndex) {
      parts.push(text.substring(lastIndex, index));
    }

    // 1. Markdown Links [label](url)
    if (match[1] && match[2]) {
      const linkLabel = match[1];
      const linkUrl = match[2];
      parts.push(
        <a
          key={`link_${index}`}
          href={linkUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-0.5 text-blue-600 dark:text-blue-400 font-semibold hover:underline align-baseline"
        >
          <span>{linkLabel}</span>
          <ExternalLink className="w-2.5 h-2.5 inline flex-shrink-0" />
        </a>
      );
    }
    // 2. Bold text
    else if (matched.startsWith('**') && matched.endsWith('**')) {
      const inner = matched.slice(2, -2);
      parts.push(
        <strong key={`b_${index}`} className="font-bold text-slate-900 dark:text-white">
          {inner}
        </strong>
      );
    }
    // 3. Italic text
    else if (matched.startsWith('*') && matched.endsWith('*') && matched.length > 2) {
      parts.push(
        <em key={`i_${index}`} className="italic text-slate-700 dark:text-slate-300">
          {matched.slice(1, -1)}
        </em>
      );
    }
    // 4. Code text
    else if (matched.startsWith('`') && matched.endsWith('`')) {
      parts.push(
        <code
          key={`c_${index}`}
          className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold"
        >
          {matched.slice(1, -1)}
        </code>
      );
    }
    // 5. Currency amounts & Percentages (₹X, $X, +6.8%, FY2026)
    else if (
      /^(?:₹|\$|€)/.test(matched) ||
      /%$/.test(matched) ||
      /^FY\s?20\d{2}$/.test(matched)
    ) {
      const isNegative = matched.startsWith('-');
      const isFY = /^FY\s?20\d{2}$/.test(matched);

      if (isFY) {
        parts.push(
          <span
            key={`fy_${index}`}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-bold bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 align-baseline"
          >
            {matched}
          </span>
        );
      } else if (isNegative) {
        parts.push(
          <span
            key={`neg_${index}`}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-bold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20 font-mono tabular-nums"
          >
            {matched}
          </span>
        );
      } else {
        parts.push(
          <span
            key={`fin_${index}`}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 font-mono tabular-nums"
          >
            {matched}
          </span>
        );
      }
    }
    // 6. Citation Reference
    else {
      const pageMatch = matched.match(/Page\s*(\d+)/i);
      const pageNum = pageMatch ? parseInt(pageMatch[1], 10) : null;

      if (pageNum) {
        let sectionName = 'Financial Filing';
        if (matched.includes('—')) {
          sectionName = matched.split('—')[1].replace(/[\]\)]/g, '').trim();
        }

        const matchedSource = sources?.find((s) => s.page_number === pageNum) || {
          page_number: pageNum,
          section: sectionName,
          document_name: 'Financial Filing',
          snippet: `Cited reference on Page ${pageNum}.`,
        };

        parts.push(
          <PdfCitation
            key={`cit_${index}`}
            citation={matchedSource}
            onOpenPdf={onOpenPdfCitation}
            variant="pill"
          />
        );
      } else {
        parts.push(matched);
      }
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  sources = [],
  isStreaming = false,
  onOpenPdfCitation,
}) => {
  const elements = useMemo(() => {
    if (!content) return null;

    const sanitized = cleanUserFacingMarkdown(content);
    const lines = sanitized.split(/\r?\n/);
    const parsedNodes: React.ReactNode[] = [];

    let tableBuffer: string[] = [];
    let listBuffer: string[] = [];
    let isOrderedList = false;

    const flushTable = (keyIdx: number) => {
      if (tableBuffer.length < 2) {
        tableBuffer.forEach((tblLine, idx) => {
          parsedNodes.push(
            <p key={`tbl_fallback_${keyIdx}_${idx}`} className="my-1.5 text-xs sm:text-sm text-slate-700 dark:text-slate-200">
              {renderInlineTokens(tblLine, sources, onOpenPdfCitation)}
            </p>
          );
        });
        tableBuffer = [];
        return;
      }

      const headerLine = tableBuffer[0];
      const rowLines = tableBuffer.slice(1).filter((r) => !r.includes('---'));

      const parseCells = (row: string) =>
        row
          .split('|')
          .map((c) => c.trim())
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

      const headers = parseCells(headerLine);

      parsedNodes.push(
        <FinancialTableWithChart
          key={`ftable_${keyIdx}`}
          headers={headers}
          rowLines={rowLines}
          sources={sources}
          onOpenSourceModal={onOpenPdfCitation}
        />
      );
      tableBuffer = [];
    };

    const flushList = (keyIdx: number) => {
      if (listBuffer.length === 0) return;

      if (isOrderedList) {
        parsedNodes.push(
          <ol key={`ol_${keyIdx}`} className="my-2.5 space-y-1.5 pl-4 list-decimal text-xs sm:text-sm text-slate-700 dark:text-slate-200">
            {listBuffer.map((item, idx) => (
              <li key={`oli_${idx}`} className="leading-relaxed pl-1">
                {renderInlineTokens(item, sources, onOpenPdfCitation)}
              </li>
            ))}
          </ol>
        );
      } else {
        parsedNodes.push(
          <ul key={`ul_${keyIdx}`} className="my-2.5 space-y-1.5 pl-1">
            {listBuffer.map((item, idx) => (
              <li key={`uli_${idx}`} className="flex items-start gap-2.5 text-slate-700 dark:text-slate-200 text-xs sm:text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
                <span className="flex-1 leading-relaxed">
                  {renderInlineTokens(item, sources, onOpenPdfCitation)}
                </span>
              </li>
            ))}
          </ul>
        );
      }
      listBuffer = [];
      isOrderedList = false;
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // 1. Table Row
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        if (listBuffer.length > 0) flushList(i);
        tableBuffer.push(trimmed);
        continue;
      } else if (tableBuffer.length > 0) {
        flushTable(i);
      }

      // 2. Ordered List (1. 2. 3.)
      const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
      if (orderedMatch) {
        if (listBuffer.length > 0 && !isOrderedList) flushList(i);
        isOrderedList = true;
        listBuffer.push(orderedMatch[2]);
        continue;
      }

      // 3. Unordered Bullet List (- * •)
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
        if (listBuffer.length > 0 && isOrderedList) flushList(i);
        isOrderedList = false;
        listBuffer.push(trimmed.replace(/^[-*•]\s+/, ''));
        continue;
      } else if (listBuffer.length > 0) {
        flushList(i);
      }

      // 4. Blank Lines
      if (!trimmed) {
        continue;
      }

      // 5. Headings
      if (trimmed.startsWith('### ')) {
        const headingText = trimmed.replace(/^###\s+/, '');
        let icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />;
        let badgeClass = "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25";

        if (/findings|highlights|metrics/i.test(headingText)) {
          icon = <TrendingUp className="w-3.5 h-3.5 text-cyan-500" />;
          badgeClass = "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/25";
        } else if (/calculations|ratios|indicators/i.test(headingText)) {
          icon = <Calculator className="w-3.5 h-3.5 text-amber-500" />;
          badgeClass = "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/25";
        } else if (/limitations|risks|challenges/i.test(headingText)) {
          icon = <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />;
          badgeClass = "bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/25";
        } else if (/sources|citations/i.test(headingText)) {
          icon = <ShieldCheck className="w-3.5 h-3.5 text-teal-500" />;
          badgeClass = "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/25";
        }

        parsedNodes.push(
          <div key={`h3_${i}`} className="mt-4 mb-2 first:mt-0 flex items-center gap-2">
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl border text-xs font-black uppercase tracking-wider ${badgeClass} shadow-xs`}>
              {icon}
              <span>{headingText}</span>
            </div>
          </div>
        );
        continue;
      }

      if (trimmed.startsWith('## ')) {
        parsedNodes.push(
          <h2
            key={`h2_${i}`}
            className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white mt-4 mb-2 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>{trimmed.replace(/^##\s+/, '')}</span>
          </h2>
        );
        continue;
      }

      if (trimmed.startsWith('# ')) {
        parsedNodes.push(
          <h1
            key={`h1_${i}`}
            className="text-base sm:text-lg font-black text-slate-900 dark:text-white mt-4 mb-2"
          >
            {trimmed.replace(/^#\s+/, '')}
          </h1>
        );
        continue;
      }

      // 6. Blockquote
      if (trimmed.startsWith('> ')) {
        parsedNodes.push(
          <blockquote
            key={`quote_${i}`}
            className="my-2.5 p-3 rounded-xl border-l-4 border-emerald-500 bg-slate-50 dark:bg-slate-950/60 text-xs sm:text-sm text-slate-600 dark:text-slate-300 italic"
          >
            {renderInlineTokens(trimmed.replace(/^>\s+/, ''), sources, onOpenPdfCitation)}
          </blockquote>
        );
        continue;
      }

      // 7. Horizontal separator
      if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
        parsedNodes.push(
          <hr key={`hr_${i}`} className="my-3 border-slate-200 dark:border-slate-800" />
        );
        continue;
      }

      // 8. Standard Paragraph
      parsedNodes.push(
        <p key={`p_${i}`} className="my-1.5 text-xs sm:text-sm leading-relaxed text-slate-800 dark:text-slate-200">
          {renderInlineTokens(line, sources, onOpenPdfCitation)}
        </p>
      );
    }

    if (tableBuffer.length > 0) flushTable(lines.length);
    if (listBuffer.length > 0) flushList(lines.length);

    return parsedNodes;
  }, [content, sources, onOpenPdfCitation]);

  return <div className="space-y-1">{elements}</div>;
};

export default MarkdownRenderer;

