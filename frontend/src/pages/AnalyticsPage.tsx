import React, { useState, useEffect } from 'react';
import { useTheme } from '../hooks/useTheme';
import { useReportContext } from '../context/ReportContext';
import { financialService } from '../services/financialService';
import { FinancialChartData } from '../types/financial';
import { EmptyState } from '../components/EmptyState';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  PieChart,
  FileText,
  AlertCircle,
  Loader2,
  RefreshCw,
  Scale,
  Wallet,
  ArrowUpRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const AnalyticsPage: React.FC = () => {
  const { theme } = useTheme();
  const { reports, activeReport } = useReportContext();
  const navigate = useNavigate();

  const [selectedReportId, setSelectedReportId] = useState<string>('');
  const [chartData, setChartData] = useState<FinancialChartData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sync default selected report
  useEffect(() => {
    if (activeReport?.id) {
      setSelectedReportId(activeReport.id);
    } else if (reports.length > 0 && !selectedReportId) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, activeReport]);

  // Fetch financial chart metrics from backend
  useEffect(() => {
    if (!selectedReportId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    financialService
      .getChartData(selectedReportId)
      .then((res) => {
        if (isMounted) {
          if (res.success && res.data) {
            setChartData(res.data);
          } else {
            setChartData(null);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          logger_error_fallback(err);
          setError('Could not fetch financial analytics data.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedReportId]);

  const logger_error_fallback = (err: any) => {
    console.error('Financial chart fetch error:', err);
  };

  const chartTheme = {
    grid: theme === 'dark' ? '#334155' : '#e2e8f0',
    axis: theme === 'dark' ? '#94a3b8' : '#64748b',
    tooltipBg: theme === 'dark' ? '#0f172a' : '#ffffff',
    tooltipBorder: theme === 'dark' ? '#334155' : '#cbd5e1',
    tooltipText: theme === 'dark' ? '#f8fafc' : '#0f172a',
  };

  const selectedReport = reports.find((r) => r.id === selectedReportId) || reports[0];

  // Extracts source pages safely
  const getSourcePageBadge = (pageNo?: number) => {
    if (!pageNo) return null;
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-800/60 px-2 py-0.5 rounded-full">
        <FileText className="w-3 h-3" />
        Page {pageNo}
      </span>
    );
  };

  // Helper for empty chart card when structured data is missing
  const renderEmptyChartCard = (title: string, icon: React.ElementType) => {
    const IconComponent = icon;
    return (
      <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4 flex flex-col justify-between min-h-[300px]">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <IconComponent className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>{title}</span>
          </h3>
          <span className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400">Grounding Enforced</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center bg-slate-50/50 dark:bg-slate-950/50 rounded-xl border border-dashed border-slate-200 dark:border-slate-800/80">
          <AlertCircle className="w-8 h-8 text-amber-500/80 mb-2" />
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 max-w-xs">
            Insufficient structured data available in this report.
          </p>
          <p className="text-[11px] text-slate-400 mt-1 max-w-xs">
            No verified numerical statement figures could be extracted for this visualization from the document context.
          </p>
        </div>
      </div>
    );
  };

  if (reports.length === 0) {
    return (
      <div className="space-y-6 animate-fade-in w-full min-w-0">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Financial Visual Analytics
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Automated statement extraction & multi-period trajectory modeling
          </p>
        </div>

        <EmptyState
          title="No Financial Reports Available"
          description="Upload a financial filing PDF to extract structured statement trends, cash flows, assets, liabilities, and ratios."
          actionLabel="Upload PDF Filing"
          onAction={() => navigate('/upload')}
          icon={BarChart3}
        />
      </div>
    );
  }

  // Extract chart arrays safely
  const revData = chartData?.revenue_chart || [];
  const profitData = chartData?.profit_chart || chartData?.net_income_chart || [];
  const expenseData = chartData?.expense_chart || chartData?.operating_expenses_chart || [];
  const assetsLiabData = chartData?.assets_vs_liabilities_chart || [];
  const cashFlowData = chartData?.cash_flow_chart || [];
  const yoyData = chartData?.yoy_comparison_chart || [];
  const keyRatios = chartData?.key_ratios || [];

  const defaultUnit = chartData?.currency ? `${chartData.currency}` : 'Units';

  return (
    <div className="space-y-6 animate-fade-in w-full min-w-0 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Financial Visual Analytics
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Strictly grounded statement metrics extracted directly from corporate filings
          </p>
        </div>

        {/* Target Report Selector */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-semibold text-slate-500 flex-shrink-0">Target Filing:</span>
          <select
            value={selectedReportId}
            onChange={(e) => setSelectedReportId(e.target.value)}
            disabled={loading}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-emerald-500 truncate max-w-[260px] shadow-sm cursor-pointer disabled:opacity-60"
          >
            {reports.map((r) => (
              <option key={r.id} value={r.id}>
                {r.companyName || r.company_name || r.filename} ({r.financialYear || r.fiscal_period || 'PDF'})
              </option>
            ))}
          </select>
          {loading && <Loader2 className="w-4 h-4 animate-spin text-emerald-500 flex-shrink-0" />}
        </div>
      </div>

      {/* Global Insufficient Data Warning Banner */}
      {!loading && chartData && !chartData.has_data && (
        <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 rounded-xl flex items-start gap-3 text-amber-800 dark:text-amber-300">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider">Limited Structured Statements Found</h4>
            <p className="text-xs mt-0.5">
              Insufficient structured data available in this report to construct all 6 time-series visualizations. FinSight AI strictly avoids hallucinating numbers.
            </p>
          </div>
        </div>
      )}

      {/* Error state banner */}
      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl flex items-center justify-between text-rose-700 dark:text-rose-300 text-xs font-medium">
          <span>{error}</span>
          <button
            onClick={() => setSelectedReportId(selectedReportId)}
            className="flex items-center gap-1 font-bold underline hover:text-rose-900"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      )}

      {/* CHARTS GRID (6 VISUALIZATIONS) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* 1. REVENUE TREND CHART */}
        {revData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <span>1. Revenue Trend</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Metric: {revData[0]?.metric_name || 'Total Revenue'} | Unit: {revData[0]?.unit || defaultUnit}
                </p>
              </div>
              {getSourcePageBadge(revData[0]?.page_number)}
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                  <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                  <YAxis stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBg,
                      borderColor: chartTheme.tooltipBorder,
                      borderRadius: '12px',
                      color: chartTheme.tooltipText,
                    }}
                    formatter={(value: any, name: any, item: any) => [
                      `${value} ${item.payload.unit || defaultUnit}`,
                      item.payload.metric_name || 'Revenue',
                    ]}
                    labelFormatter={(label, items) => `Period: ${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Bar dataKey="value" fill="#10b981" radius={[6, 6, 0, 0]} name="Revenue" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('1. Revenue Trend', BarChart3)
        )}

        {/* 2. PROFIT TREND CHART */}
        {profitData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <span>2. Profit Trend</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Metric: {profitData[0]?.metric_name || 'Net Profit'} | Unit: {profitData[0]?.unit || defaultUnit}
                </p>
              </div>
              {getSourcePageBadge(profitData[0]?.page_number)}
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={profitData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                  <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                  <YAxis stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBg,
                      borderColor: chartTheme.tooltipBorder,
                      borderRadius: '12px',
                      color: chartTheme.tooltipText,
                    }}
                    formatter={(value: any, name: any, item: any) => [
                      `${value} ${item.payload.unit || defaultUnit}`,
                      item.payload.metric_name || 'Net Profit',
                    ]}
                    labelFormatter={(label, items) => `Period: ${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#06b6d4"
                    strokeWidth={3}
                    dot={{ r: 5, fill: '#06b6d4' }}
                    name="Net Profit"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('2. Profit Trend', TrendingUp)
        )}

        {/* 3. EXPENSE TREND CHART */}
        {expenseData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span>3. Expense Trend</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Metric: {expenseData[0]?.metric_name || 'Operating Expenses'} | Unit: {expenseData[0]?.unit || defaultUnit}
                </p>
              </div>
              {getSourcePageBadge(expenseData[0]?.page_number)}
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={expenseData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                  <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                  <YAxis stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBg,
                      borderColor: chartTheme.tooltipBorder,
                      borderRadius: '12px',
                      color: chartTheme.tooltipText,
                    }}
                    formatter={(value: any, name: any, item: any) => [
                      `${value} ${item.payload.unit || defaultUnit}`,
                      item.payload.metric_name || 'Expenses',
                    ]}
                    labelFormatter={(label, items) => `Period: ${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Bar dataKey="value" fill="#f59e0b" radius={[6, 6, 0, 0]} name="Expenses" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('3. Expense Trend', DollarSign)
        )}

        {/* 4. ASSETS VS LIABILITIES CHART */}
        {assetsLiabData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Scale className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                  <span>4. Assets vs Liabilities</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Balance Sheet Comparison | Unit: {assetsLiabData[0]?.unit || defaultUnit}
                </p>
              </div>
              {getSourcePageBadge(assetsLiabData[0]?.page_number)}
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={assetsLiabData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                  <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                  <YAxis stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBg,
                      borderColor: chartTheme.tooltipBorder,
                      borderRadius: '12px',
                      color: chartTheme.tooltipText,
                    }}
                    labelFormatter={(label, items) => `Period: ${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="assets" fill="#6366f1" radius={[4, 4, 0, 0]} name="Total Assets" />
                  <Bar dataKey="liabilities" fill="#ec4899" radius={[4, 4, 0, 0]} name="Total Liabilities" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('4. Assets vs Liabilities', Scale)
        )}

        {/* 5. CASH FLOW CHART */}
        {cashFlowData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Wallet className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                  <span>5. Cash Flow Analysis</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Statement of Cash Flows | Unit: {cashFlowData[0]?.unit || defaultUnit}
                </p>
              </div>
              {getSourcePageBadge(cashFlowData[0]?.page_number)}
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cashFlowData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                  <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                  <YAxis stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBg,
                      borderColor: chartTheme.tooltipBorder,
                      borderRadius: '12px',
                      color: chartTheme.tooltipText,
                    }}
                    labelFormatter={(label, items) => `Period: ${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="operating" fill="#14b8a6" radius={[4, 4, 0, 0]} name="Operating CF" />
                  <Bar dataKey="investing" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Investing CF" />
                  <Bar dataKey="financing" fill="#f43f5e" radius={[4, 4, 0, 0]} name="Financing CF" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('5. Cash Flow', Wallet)
        )}

        {/* 6. YEAR-OVER-YEAR COMPARISON CHART */}
        {yoyData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <PieChart className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                  <span>6. Year-over-Year Comparison</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Multi-Period YoY Growth Rates | Unit: {yoyData[0]?.unit || defaultUnit}
                </p>
              </div>
              {getSourcePageBadge(yoyData[0]?.page_number)}
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={yoyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                  <XAxis dataKey="metric_name" stroke={chartTheme.axis} fontSize={11} />
                  <YAxis stroke={chartTheme.axis} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBg,
                      borderColor: chartTheme.tooltipBorder,
                      borderRadius: '12px',
                      color: chartTheme.tooltipText,
                    }}
                    formatter={(value: any, name: any, item: any) => [
                      `${value} ${item.payload.unit || defaultUnit}`,
                      name === 'previous_year_value'
                        ? `Prior (${item.payload.previous_year_period || 'Prior'})`
                        : `Current (${item.payload.current_year_period || 'Current'})`,
                    ]}
                    labelFormatter={(label, items) => `${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="previous_year_value" fill="#94a3b8" radius={[4, 4, 0, 0]} name="Previous Period" />
                  <Bar dataKey="current_year_value" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Current Period" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('6. Year-over-Year Comparison', PieChart)
        )}

      </div>

      {/* EXTRACTED KEY RATIOS SECTION */}
      <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4 mt-6">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ArrowUpRight className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Verified Statement Ratios for {selectedReport?.companyName || selectedReport?.company_name || selectedReport?.filename}</span>
          </h3>
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Grounded Evidence</span>
        </div>

        {keyRatios.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {keyRatios.map((ratio, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 dark:text-slate-400 font-semibold">{ratio.name}</span>
                  {ratio.page_number && (
                    <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950 px-1.5 py-0.5 rounded">
                      Page {ratio.page_number}
                    </span>
                  )}
                </div>
                <span className="text-2xl font-extrabold text-slate-900 dark:text-slate-100 block">{ratio.value}</span>
                {ratio.description && (
                  <span className="text-[11px] text-slate-400 line-clamp-2 block">{ratio.description}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic py-2">
            Insufficient structured data available in this report to extract key financial ratios.
          </p>
        )}
      </div>
    </div>
  );
};
