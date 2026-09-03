import React, { useState, useMemo } from 'react';
import {
  ShieldCheck,
  TrendingUp,
  DollarSign,
  Calculator,
  AlertTriangle,
  FileText,
  CheckCircle2,
  BarChart2,
  Table as TableIcon,
  LineChart as LineChartIcon,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

import { SourceMetadata } from '../../services/conversationService';
export type { SourceMetadata };

/**
 * Formats inline text with bold, italic, code, financial metrics, and interactive citation badges
 */
export const renderInlineMarkdown = (
  text: string,
  sources?: SourceMetadata[],
  onOpenSourceModal?: (s: SourceMetadata) => void
): React.ReactNode => {
  if (!text) return null;

  // Sanitize internal debugging tokens and transform them into clean Source citations
  const cleanText = text
    .replace(/Evidence\s*\d+\s*(?:\/|—|-|:)?\s*(?:svgPage|Page)?\s*(\d+)/gi, 'Source: Page $1')
    .replace(/svgPage\s*(\d+)/gi, 'Page $1')
    .replace(/\[Evidence\s*\d+\]/gi, '')
    .trim();

  // Pattern matches:
  // 1. Source citations (Source: Page X — Section, [Page X])
  // 2. Bold (**...**)
  // 3. Italic (*...*)
  // 4. Code / Formula (`...`)
  // 5. Financial Numbers & Percentages (₹X, $X, +X%, -X%, X Crore, X Lakh, X Billion, FY202X)
  const tokenRegex = /(Source:\s*Page\s*\d+(?:\s*—[A-Za-z0-9\s,\.\-&]+)?|\[(?:Page\s*)?\d+(?:\s*—[^\]]+)?\]|\(Page\s*\d+\)|【Page\s*\d+】|Page\s*\d+\s*—\s*[A-Za-z0-9\s,\.\-&]+|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|(?:₹|\$|€)\s?[\d,]+(?:\.\d+)?(?:\s*(?:Crore|Cr|Lakh|Million|Billion|Trillion))?|(?:\+|\-)?\d+(?:\.\d+)?%|\bFY\s?20\d{2}\b)/g;
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
      const inner = matchedStr.slice(2, -2);
      parts.push(
        <strong key={`b_${index}`} className="font-bold text-slate-900 dark:text-emerald-300">
          {inner}
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
    // C. Code / Formula text
    else if (matchedStr.startsWith('`') && matchedStr.endsWith('`')) {
      parts.push(
        <code key={`c_${index}`} className="px-2 py-0.5 rounded-lg bg-emerald-950/40 border border-emerald-500/20 font-mono text-[12px] text-emerald-400 font-semibold shadow-xs">
          {matchedStr.slice(1, -1)}
        </code>
      );
    }
    // D. Financial Currency amounts & Percentages (₹X, $X, +6.8%, FY2026)
    else if (
      /^(?:₹|\$|€)/.test(matchedStr) ||
      /%$/.test(matchedStr) ||
      /^FY\s?20\d{2}$/.test(matchedStr)
    ) {
      const isNegative = matchedStr.startsWith('-');
      const isFY = /^FY\s?20\d{2}$/.test(matchedStr);

      if (isFY) {
        parts.push(
          <span key={`fy_${index}`} className="inline-flex items-center px-2 py-0.5 mx-0.5 rounded-md text-[11px] font-bold bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 align-baseline">
            {matchedStr}
          </span>
        );
      } else if (isNegative) {
        parts.push(
          <span key={`neg_${index}`} className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[12px] font-bold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20">
            {matchedStr}
          </span>
        );
      } else {
        parts.push(
          <span key={`fin_${index}`} className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[12px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 shadow-2xs">
            {matchedStr}
          </span>
        );
      }
    }
    // E. Citation reference (e.g. Source: Page 291 — Consolidated Statement of Profit and Loss, [Page 291])
    else {
      const pageMatch = matchedStr.match(/Page\s*(\d+)/i);
      const pageNum = pageMatch ? parseInt(pageMatch[1], 10) : null;

      if (pageNum) {
        let sectionName = 'Financial Statement';
        if (matchedStr.includes('—')) {
          sectionName = matchedStr.split('—')[1].replace(/[\]\)]/g, '').trim();
        }

        const matchedSource = sources?.find((s) => s.page_number === pageNum) || {
          page_number: pageNum,
          section: sectionName,
          document_name: 'Financial Filing',
          snippet: `Referenced financial disclosure on Page ${pageNum}.`,
        };

        const displayLabel = sectionName && sectionName !== 'Financial Statement' && sectionName.length < 35
          ? `Source: Page ${pageNum} — ${sectionName}`
          : `Source: Page ${pageNum}`;

        parts.push(
          <button
            key={`badge_${index}`}
            type="button"
            onClick={() => onOpenSourceModal?.(matchedSource)}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 mx-1 my-0.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 font-extrabold text-[11px] transition-all cursor-pointer shadow-xs group align-middle"
            title={`View verified citation for Page ${pageNum}: ${sectionName}`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 group-hover:scale-110 transition-transform" />
            <span className="truncate max-w-[280px]">{displayLabel}</span>
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
 * Extract clean numeric float value from formatted financial string
 */
const parseFinancialNumber = (str: string): number | null => {
  if (!str) return null;
  const clean = str.replace(/[₹$€,\s%]/g, '').replace(/Crore|Cr|Lakh|Million|Billion|Trillion/gi, '').trim();
  if (!clean) return null;
  // Handle accounting brackets (e.g. (100) -> -100)
  if (clean.startsWith('(') && clean.endsWith(')')) {
    const num = parseFloat(clean.slice(1, -1));
    return isNaN(num) ? null : -num;
  }
  const num = parseFloat(clean);
  return isNaN(num) ? null : num;
};

const CHART_PALETTE = ['#10b981', '#06b6d4', '#6366f1', '#f59e0b', '#ec4899', '#8b5cf6'];

/**
 * Interactive Financial Table & In-Chat Dynamic Chart Component
 */
export const FinancialTableWithChart: React.FC<{
  headers: string[];
  rowLines: string[];
  sources?: SourceMetadata[];
  onOpenSourceModal?: (s: SourceMetadata) => void;
}> = ({ headers, rowLines, sources, onOpenSourceModal }) => {
  const [viewMode, setViewMode] = useState<'table' | 'bar' | 'line'>('table');

  const parseCells = (row: string) =>
    row
      .split('|')
      .map((c) => c.trim())
      .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

  // Extract structured chart data
  const { chartData, seriesKeys, isChartable } = useMemo(() => {
    if (headers.length < 2 || rowLines.length === 0) {
      return { chartData: [], seriesKeys: [], isChartable: false };
    }

    const data: Array<Record<string, any>> = [];
    const validNumericColumns = new Set<string>();

    for (const rowStr of rowLines) {
      const cells = parseCells(rowStr);
      if (cells.length === 0) continue;

      const rowLabel = cells[0]?.replace(/[*`_]/g, '') || `Row ${data.length + 1}`;
      const rowObj: Record<string, any> = { name: rowLabel };

      for (let c = 1; c < Math.min(cells.length, headers.length); c++) {
        const headerName = headers[c]?.replace(/[*`_]/g, '').trim() || `Col ${c}`;
        const val = parseFinancialNumber(cells[c]);
        if (val !== null) {
          rowObj[headerName] = val;
          validNumericColumns.add(headerName);
        }
      }
      data.push(rowObj);
    }

    const keys = Array.from(validNumericColumns);
    const chartable = keys.length > 0 && data.length >= 2;

    return { chartData: data, seriesKeys: keys, isChartable: chartable };
  }, [headers, rowLines]);

  return (
    <div className="my-4 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 shadow-md bg-white dark:bg-slate-900/90 backdrop-blur-md transition-all">
      {/* Header bar with view toggles if data is chartable */}
      <div className="px-4 py-2.5 bg-slate-50 dark:bg-slate-950/80 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-300">
          <DollarSign className="w-3.5 h-3.5 text-emerald-500" />
          <span>Financial Data Statement</span>
        </div>

        {isChartable && (
          <div className="flex items-center p-0.5 bg-slate-200/70 dark:bg-slate-800/80 rounded-xl text-[11px] font-semibold">
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-white dark:bg-slate-900 text-emerald-600 dark:text-emerald-400 shadow-xs font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <TableIcon className="w-3 h-3" />
              <span>Table</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('bar')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                viewMode === 'bar'
                  ? 'bg-white dark:bg-slate-900 text-emerald-600 dark:text-emerald-400 shadow-xs font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <BarChart2 className="w-3 h-3" />
              <span>Bar Chart</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('line')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                viewMode === 'line'
                  ? 'bg-white dark:bg-slate-900 text-emerald-600 dark:text-emerald-400 shadow-xs font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <LineChartIcon className="w-3 h-3" />
              <span>Trend Line</span>
            </button>
          </div>
        )}
      </div>

      {/* Content: Table or Chart */}
      {viewMode === 'table' ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gradient-to-r from-slate-100 via-slate-50 to-slate-100 dark:from-slate-800/80 dark:via-slate-850 dark:to-slate-800/80 border-b border-slate-200 dark:border-slate-700/80">
                {headers.map((h, hIdx) => (
                  <th
                    key={`th_${hIdx}`}
                    className={`px-4 py-3 font-extrabold uppercase tracking-wider text-slate-800 dark:text-emerald-400 text-[11px] ${
                      hIdx > 0 ? 'text-right' : 'text-left'
                    }`}
                  >
                    {renderInlineMarkdown(h, sources, onOpenSourceModal)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {rowLines.map((rowStr, rIdx) => {
                const cells = parseCells(rowStr);
                return (
                  <tr key={`tr_${rIdx}`} className="hover:bg-emerald-500/5 dark:hover:bg-emerald-500/10 transition-colors">
                    {cells.map((cell, cIdx) => (
                      <td
                        key={`td_${cIdx}`}
                        className={`px-4 py-2.5 text-slate-700 dark:text-slate-200 text-xs font-medium ${
                          cIdx > 0 ? 'text-right' : 'text-left font-semibold text-slate-900 dark:text-slate-100'
                        }`}
                      >
                        {renderInlineMarkdown(cell, sources, onOpenSourceModal)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-4 bg-slate-50/50 dark:bg-slate-950/40">
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              {viewMode === 'bar' ? (
                <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '12px',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  {seriesKeys.map((key, kIdx) => (
                    <Bar
                      key={key}
                      dataKey={key}
                      fill={CHART_PALETTE[kIdx % CHART_PALETTE.length]}
                      radius={[6, 6, 0, 0]}
                    />
                  ))}
                </BarChart>
              ) : (
                <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '12px',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  {seriesKeys.map((key, kIdx) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={CHART_PALETTE[kIdx % CHART_PALETTE.length]}
                      strokeWidth={3}
                      dot={{ r: 4, fill: CHART_PALETTE[kIdx % CHART_PALETTE.length] }}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Rich Markdown Component that parses Headings, Tables, Lists, Formulas, and Paragraphs with modern financial UI aesthetics
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
          <p key={`t_fallback_${keyIndex}_${lIdx}`} className="my-1.5 text-slate-700 dark:text-slate-200">
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
      <FinancialTableWithChart
        key={`table_${keyIndex}`}
        headers={headers}
        rowLines={rowLines}
        sources={sources}
        onOpenSourceModal={onOpenSourceModal}
      />
    );
    tableBuffer = [];
  };

  const flushList = (keyIndex: number) => {
    if (listBuffer.length === 0) return;
    elements.push(
      <ul key={`ul_${keyIndex}`} className="my-2.5 space-y-2 pl-1">
        {listBuffer.map((item, idx) => (
          <li key={`li_${idx}`} className="flex items-start gap-2.5 text-slate-700 dark:text-slate-200 text-xs sm:text-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 mt-2 flex-shrink-0 shadow-xs shadow-emerald-500/50" />
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

    // 4. Section Headings with rich color badges
    if (trimmed.startsWith('### ')) {
      const headingText = trimmed.replace(/^###\s+/, '');
      let icon = <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      let badgeClass = "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30";

      if (/findings|highlights|metrics/i.test(headingText)) {
        icon = <TrendingUp className="w-4 h-4 text-cyan-400" />;
        badgeClass = "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/30";
      } else if (/calculations|indicators|ratios/i.test(headingText)) {
        icon = <Calculator className="w-4 h-4 text-amber-400" />;
        badgeClass = "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30";
      } else if (/limitations|missing|risk/i.test(headingText)) {
        icon = <AlertTriangle className="w-4 h-4 text-rose-400" />;
        badgeClass = "bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30";
      } else if (/sources|citations/i.test(headingText)) {
        icon = <ShieldCheck className="w-4 h-4 text-teal-400" />;
        badgeClass = "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/30";
      }

      elements.push(
        <div key={`h3_${i}`} className="mt-5 mb-2.5 first:mt-1 flex items-center gap-2">
          <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl border text-xs font-black uppercase tracking-wider ${badgeClass} shadow-xs`}>
            {icon}
            <span>{headingText}</span>
          </div>
        </div>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={`h2_${i}`} className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white mt-5 mb-2 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span>{trimmed.replace(/^##\s+/, '')}</span>
        </h2>
      );
      continue;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={`h1_${i}`} className="text-base sm:text-lg font-black text-slate-900 dark:text-white mt-5 mb-3">
          {trimmed.replace(/^#\s+/, '')}
        </h1>
      );
      continue;
    }

    // 5. Horizontal Rule
    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      elements.push(
        <hr key={`hr_${i}`} className="my-4 border-slate-200 dark:border-slate-800" />
      );
      continue;
    }

    // 6. Standard Paragraph Line
    elements.push(
      <p key={`p_${i}`} className="my-2 text-xs sm:text-sm leading-relaxed text-slate-700 dark:text-slate-200">
        {renderInlineMarkdown(rawLine, sources, onOpenSourceModal)}
      </p>
    );
  }

  if (tableBuffer.length > 0) flushTable(lines.length);
  if (listBuffer.length > 0) flushList(lines.length);

  return <div className="space-y-1">{elements}</div>;
};

export default RichMarkdownRenderer;
