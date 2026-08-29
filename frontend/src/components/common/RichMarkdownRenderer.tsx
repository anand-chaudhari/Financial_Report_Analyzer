import React from 'react';
import { ShieldCheck, BookOpen } from 'lucide-react';

export interface SourceMetadata {
  page_number: number;
  section: string;
  document_name?: string;
  snippet?: string;
}

/**
 * Formats inline text with bold, italic, code, and interactive citation badges
 */
export const renderInlineMarkdown = (
  text: string,
  sources?: SourceMetadata[],
  onOpenSourceModal?: (s: SourceMetadata) => void
): React.ReactNode => {
  if (!text) return null;

  // Sanitize internal debugging tokens
  const cleanText = text
    .replace(/svgPage\s*\d+/gi, '')
    .replace(/Evidence\s*\d+\s*[:\-]/gi, '')
    .trim();

  // Pattern matches: [Page X], (Page X), 【Page X】, Page X — Section, **bold**, *italic*, `code`
  const tokenRegex = /(\[(?:Page\s*)?\d+(?:\s*—[^\]]+)?\]|\(Page\s*\d+\)|【Page\s*\d+】|Page\s*\d+\s*—\s*[A-Za-z0-9\s,\.\-&]+|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = tokenRegex.exec(cleanText)) !== null) {
    const matchedStr = match[0];
    const index = match.index;

    if (index > lastIndex) {
      parts.push(cleanText.substring(lastIndex, index));
    }

    // A. Bold text
    if (matchedStr.startsWith('**') && matchedStr.endsWith('**')) {
      parts.push(
        <strong key={`b_${index}`} className="font-bold text-slate-900 dark:text-white">
          {matchedStr.slice(2, -2)}
        </strong>
      );
    }
    // B. Italic text
    else if (matchedStr.startsWith('*') && matchedStr.endsWith('*')) {
      parts.push(
        <em key={`i_${index}`} className="italic text-slate-700 dark:text-slate-300">
          {matchedStr.slice(1, -1)}
        </em>
      );
    }
    // C. Code text
    else if (matchedStr.startsWith('`') && matchedStr.endsWith('`')) {
      parts.push(
        <code key={`c_${index}`} className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-xs text-emerald-600 dark:text-emerald-400">
          {matchedStr.slice(1, -1)}
        </code>
      );
    }
    // D. Citation reference (e.g. [Page 291], Page 291 — Balance Sheet)
    else {
      const pageMatch = matchedStr.match(/Page\s*(\d+)/i);
      const pageNum = pageMatch ? parseInt(pageMatch[1], 10) : null;

      if (pageNum) {
        const matchedSource = sources?.find((s) => s.page_number === pageNum) || {
          page_number: pageNum,
          section: matchedStr.includes('—') ? matchedStr.split('—')[1].replace(/[\]\)]/g, '').trim() : 'Financial Filing Reference',
          document_name: 'Financial Filing',
          snippet: `Referenced statement snippet on Page ${pageNum}.`,
        };

        parts.push(
          <button
            key={`badge_${index}`}
            type="button"
            onClick={() => onOpenSourceModal?.(matchedSource)}
            className="inline-flex items-center gap-1 px-2 py-0.5 mx-1 my-0.5 rounded-md bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 font-extrabold text-[11px] transition-all cursor-pointer shadow-xs group align-middle"
            title={`View citation for Page ${pageNum}`}
          >
            <ShieldCheck className="w-3 h-3 text-emerald-500 group-hover:scale-110 transition-transform" />
            <span>Page {pageNum}</span>
          </button>
        );
      } else {
        parts.push(matchedStr);
      }
    }

    lastIndex = tokenRegex.lastIndex;
  }

  if (lastIndex < cleanText.length) {
    parts.push(cleanText.substring(lastIndex));
  }

  return parts.length > 0 ? parts : cleanText;
};

/**
 * Rich Markdown Component that parses Headings, Tables, Lists, and Paragraphs
 */
export const RichMarkdownRenderer: React.FC<{
  content: string;
  sources?: SourceMetadata[];
  onOpenSourceModal?: (s: SourceMetadata) => void;
}> = ({ content, sources, onOpenSourceModal }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let tableBuffer: string[] = [];
  let listBuffer: string[] = [];

  const flushTable = (keyIndex: number) => {
    if (tableBuffer.length < 2) {
      tableBuffer.forEach((line, lIdx) => {
        elements.push(
          <p key={`t_fallback_${keyIndex}_${lIdx}`} className="my-1 text-slate-700 dark:text-slate-300">
            {renderInlineMarkdown(line, sources, onOpenSourceModal)}
          </p>
        );
      });
      tableBuffer = [];
      return;
    }

    const headerLine = tableBuffer[0];
    const rowLines = tableBuffer.slice(2); // Skip separator line | --- | --- |

    const parseCells = (row: string) =>
      row
        .split('|')
        .map((c) => c.trim())
        .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

    const headers = parseCells(headerLine);

    elements.push(
      <div key={`table_${keyIndex}`} className="my-3 overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/80 dark:bg-slate-800/90 border-b border-slate-200 dark:border-slate-700">
              {headers.map((h, hIdx) => (
                <th key={`th_${hIdx}`} className="px-3.5 py-2.5 font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200 text-[11px]">
                  {renderInlineMarkdown(h, sources, onOpenSourceModal)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900/60">
            {rowLines.map((rowStr, rIdx) => {
              const cells = parseCells(rowStr);
              return (
                <tr key={`tr_${rIdx}`} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  {cells.map((cell, cIdx) => (
                    <td key={`td_${cIdx}`} className="px-3.5 py-2.5 text-slate-700 dark:text-slate-300 whitespace-nowrap text-xs">
                      {renderInlineMarkdown(cell, sources, onOpenSourceModal)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
    tableBuffer = [];
  };

  const flushList = (keyIndex: number) => {
    if (listBuffer.length === 0) return;
    elements.push(
      <ul key={`ul_${keyIndex}`} className="my-2 space-y-1.5 pl-1">
        {listBuffer.map((item, idx) => (
          <li key={`li_${idx}`} className="flex items-start gap-2.5 text-slate-700 dark:text-slate-300 text-xs sm:text-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
            <span className="flex-1 leading-relaxed">
              {renderInlineMarkdown(item, sources, onOpenSourceModal)}
            </span>
          </li>
        ))}
      </ul>
    );
    listBuffer = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // 1. Table Detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      if (listBuffer.length > 0) flushList(i);
      tableBuffer.push(trimmed);
      continue;
    } else if (tableBuffer.length > 0) {
      flushTable(i);
    }

    // 2. Bullet List Detection
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
      listBuffer.push(trimmed.replace(/^[-*•]\s+/, ''));
      continue;
    } else if (listBuffer.length > 0) {
      flushList(i);
    }

    // 3. Blank Lines
    if (!trimmed) {
      continue;
    }

    // 4. Headings
    if (trimmed.startsWith('### ')) {
      elements.push(
        <div key={`h3_${i}`} className="mt-4 mb-2 first:mt-1">
          <h3 className="text-xs sm:text-sm font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>{trimmed.replace(/^###\s+/, '')}</span>
          </h3>
        </div>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={`h2_${i}`} className="text-sm sm:text-base font-bold text-slate-900 dark:text-white mt-4 mb-2 border-b border-slate-100 dark:border-slate-800 pb-1">
          {trimmed.replace(/^##\s+/, '')}
        </h2>
      );
      continue;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={`h1_${i}`} className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white mt-4 mb-2">
          {trimmed.replace(/^#\s+/, '')}
        </h1>
      );
      continue;
    }

    // 5. Standard Paragraph Line
    elements.push(
      <p key={`p_${i}`} className="my-1.5 text-xs sm:text-sm leading-relaxed text-slate-700 dark:text-slate-300">
        {renderInlineMarkdown(rawLine, sources, onOpenSourceModal)}
      </p>
    );
  }

  if (tableBuffer.length > 0) flushTable(lines.length);
  if (listBuffer.length > 0) flushList(lines.length);

  return <div className="space-y-1">{elements}</div>;
};

export default RichMarkdownRenderer;
