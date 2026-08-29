import React, { useState, useEffect } from 'react';
import {
  Scale,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  ShieldCheck,
  FileSpreadsheet,
  Printer,
  Sparkles,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { useReportContext } from '../context/ReportContext';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

interface ComparisonData {
  document_a: {
    id: string;
    company_name: string;
    financial_year: string;
    file_name: string;
    page_count: number;
  };
  document_b: {
    id: string;
    company_name: string;
    financial_year: string;
    file_name: string;
    page_count: number;
  };
  metrics: Array<{
    metric_name: string;
    unit: string;
    val_a: number;
    val_b: number;
    absolute_delta: number;
    percentage_delta: number;
    trend: 'up' | 'down' | 'neutral';
  }>;
  comparative_summary: string;
}

export const ComparePage: React.FC = () => {
  const { reports } = useReportContext();
  const [docAId, setDocAId] = useState<string>(reports[0]?.id || '');
  const [docBId, setDocBId] = useState<string>(reports[1]?.id || reports[0]?.id || '');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (reports.length >= 2) {
      if (!docAId) setDocAId(reports[0].id);
      if (!docBId) setDocBId(reports[1].id);
    } else if (reports.length === 1) {
      if (!docAId) setDocAId(reports[0].id);
      if (!docBId) setDocBId(reports[0].id);
    }
  }, [reports, docAId, docBId]);

  const handleRunComparison = async () => {
    if (!docAId || !docBId) {
      setErrorMsg('Please select two reports to compare.');
      return;
    }
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_a_id: docAId,
          document_b_id: docBId,
          user_id: 'dev_user_123',
        }),
      });

      if (!response.ok) {
        throw new Error(`Comparison API returned HTTP ${response.status}`);
      }

      const data = await response.json();
      setComparisonData(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to compare reports.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (docAId && docBId && docAId !== docBId && !comparisonData) {
      handleRunComparison();
    }
  }, [docAId, docBId]);

  // Chart data formatting
  const chartData = comparisonData?.metrics.map((m) => ({
    name: m.metric_name,
    [comparisonData.document_a.company_name || 'Filing A']: m.val_a,
    [comparisonData.document_b.company_name || 'Filing B']: m.val_b,
  })) || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fade-in">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950/40 border border-slate-800 text-white shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-extrabold uppercase tracking-wider mb-3">
            <Scale className="w-3.5 h-3.5" />
            <span>Multi-Filing Peer & YoY Comparison</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
            Corporate Filing Variance & Benchmarking
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Compare financial performance, calculate YoY variance ($\Delta$), and review grounded comparative AI insights.
          </p>
        </div>

        <button
          onClick={handleRunComparison}
          disabled={isLoading}
          className="px-5 py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold text-xs sm:text-sm flex items-center gap-2 transition-all shadow-lg shadow-emerald-500/20 cursor-pointer disabled:opacity-50 self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{isLoading ? 'Analyzing Filings...' : 'Run Comparative Analysis'}</span>
        </button>
      </div>

      {/* Selectors Bar */}
      <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Document A Selector */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Base Filing (Document A)</span>
          </label>
          <select
            value={docAId}
            onChange={(e) => setDocAId(e.target.value)}
            className="w-full px-4 py-2.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
          >
            {reports.map((r) => (
              <option key={`a_${r.id}`} value={r.id}>
                {r.companyName || r.fileName} ({r.financialYear || 'Filing'})
              </option>
            ))}
          </select>
        </div>

        {/* Document B Selector */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span>Comparison Filing (Document B)</span>
          </label>
          <select
            value={docBId}
            onChange={(e) => setDocBId(e.target.value)}
            className="w-full px-4 py-2.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
          >
            {reports.map((r) => (
              <option key={`b_${r.id}`} value={r.id}>
                {r.companyName || r.fileName} ({r.financialYear || 'Filing'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs font-semibold">
          {errorMsg}
        </div>
      )}

      {/* Comparison Metrics Grid */}
      {comparisonData && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {comparisonData.metrics.map((m, idx) => {
            const isPositive = m.percentage_delta > 0;
            return (
              <div
                key={idx}
                className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 dark:text-slate-400 truncate">
                    {m.metric_name}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-extrabold ${
                      isPositive
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    <span>{m.percentage_delta > 0 ? `+${m.percentage_delta}%` : `${m.percentage_delta}%`}</span>
                  </span>
                </div>

                <div className="flex items-baseline justify-between pt-1">
                  <div>
                    <span className="text-[10px] text-slate-400 block">{comparisonData.document_a.company_name}</span>
                    <span className="text-sm font-black text-slate-900 dark:text-white">
                      {m.val_a.toLocaleString()} {m.unit}
                    </span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 mx-1" />
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block">{comparisonData.document_b.company_name}</span>
                    <span className="text-sm font-black text-slate-900 dark:text-white">
                      {m.val_b.toLocaleString()} {m.unit}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                  <span>Absolute Variance ($\Delta$):</span>
                  <strong className="text-slate-900 dark:text-white">
                    {m.absolute_delta > 0 ? `+${m.absolute_delta.toLocaleString()}` : m.absolute_delta.toLocaleString()} {m.unit}
                  </strong>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Visual Comparison Chart */}
      {comparisonData && chartData.length > 0 && (
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-500" />
              <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Visual Filing Variance Comparison
              </h3>
            </div>
            <span className="text-xs text-slate-400">Values in reported monetary scale</span>
          </div>

          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '12px',
                    fontSize: '12px',
                    color: '#fff',
                  }}
                />
                <Legend />
                <Bar
                  dataKey={comparisonData.document_a.company_name || 'Filing A'}
                  fill="#10b981"
                  radius={[6, 6, 0, 0]}
                />
                <Bar
                  dataKey={comparisonData.document_b.company_name || 'Filing B'}
                  fill="#3b82f6"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* AI Comparative Synthesis Narrative */}
      {comparisonData && comparisonData.comparative_summary && (
        <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
            <Sparkles className="w-5 h-5" />
            <h3 className="text-base font-extrabold tracking-tight text-slate-900 dark:text-white">
              AI Grounded Comparative Synthesis
            </h3>
          </div>

          <div className="prose dark:prose-invert max-w-none text-xs sm:text-sm leading-relaxed whitespace-pre-wrap text-slate-700 dark:text-slate-300">
            {comparisonData.comparative_summary}
          </div>

          <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              <span>Grounded in extracted filing tables for {comparisonData.document_a.company_name} & {comparisonData.document_b.company_name}</span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
