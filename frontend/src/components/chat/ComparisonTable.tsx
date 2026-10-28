import React from 'react';
import { Table as TableIcon } from 'lucide-react';

interface ComparisonTableProps {
  headers: string[];
  rows: Array<Array<string | React.ReactNode>>;
  caption?: string;
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({
  headers,
  rows,
  caption,
}) => {
  if (!headers || headers.length === 0 || !rows || rows.length === 0) {
    return null;
  }

  return (
    <div className="my-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs overflow-hidden">
      {caption && (
        <div className="p-2.5 px-3.5 bg-slate-50 dark:bg-slate-950/80 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-300">
          <TableIcon className="w-3.5 h-3.5 text-emerald-500" />
          <span>{caption}</span>
        </div>
      )}

      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/80 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-extrabold text-[11px] uppercase tracking-wider">
              {headers.map((h, idx) => (
                <th
                  key={`th_${idx}`}
                  className={`p-3 whitespace-nowrap ${idx === 0 ? 'text-left' : 'text-right'}`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {rows.map((row, rIdx) => (
              <tr
                key={`tr_${rIdx}`}
                className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
              >
                {row.map((cell, cIdx) => (
                  <td
                    key={`td_${rIdx}_${cIdx}`}
                    className={`p-3 text-slate-800 dark:text-slate-200 whitespace-nowrap ${
                      cIdx === 0
                        ? 'font-semibold text-left'
                        : 'text-right font-mono tabular-nums text-emerald-700 dark:text-emerald-400 font-medium'
                    }`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ComparisonTable;

