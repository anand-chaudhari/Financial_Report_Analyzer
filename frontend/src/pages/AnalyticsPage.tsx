import React, { useState, useEffect } from 'react';
import { useTheme } from '../hooks/useTheme';
import { useReportContext } from '../context/ReportContext';
import { financialService } from '../services/financialService';
import { FinancialChartData } from '../types/financial';
import { EmptyState } from '../components/EmptyState';
import { exportToExcel, exportToPdfBrief, exportToPresentationDeck } from '../services/exportService';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
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
  PieChart as PieIcon,
  FileText,
  AlertCircle,
  Loader2,
  RefreshCw,
  Scale,
  Wallet,
  ArrowUpRight,
  Download,
  FileSpreadsheet,
  Printer,
  Presentation,
  Layers,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  HelpCircle,
  Activity,
  MessageSquareText,
  Building2,
  Calendar,
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
          console.error('Financial chart fetch error:', err);
          setError('Could not fetch financial analytics data. Please try refreshing.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedReportId]);

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

  // Quick Ask AI deep-dive prompt
  const handleAskAnalyst = (promptText: string) => {
    navigate('/analyst', {
      state: {
        prefilledQuery: promptText,
        reportId: selectedReportId,
      },
    });
  };

  // Helper for empty chart card when structured data is missing
  const renderEmptyChartCard = (title: string, icon: React.ElementType, description: string) => {
    const IconComponent = icon;
    return (
      <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs space-y-4 flex flex-col justify-between min-h-[300px]">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <IconComponent className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>{title}</span>
          </h3>
          <span className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400">Statement Grounded</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center bg-slate-50/60 dark:bg-slate-950/60 rounded-xl border border-dashed border-slate-200 dark:border-slate-800/80">
          <AlertCircle className="w-7 h-7 text-amber-500/90 mb-2" />
          <p className="text-xs font-bold text-slate-800 dark:text-slate-200 max-w-xs">
            {description}
          </p>
          <p className="text-[11px] text-slate-400 mt-1 max-w-xs">
            No isolated multi-period tabular breakdown was found in this specific document. FinSight AI strictly avoids fabricating numbers.
          </p>
          <button
            onClick={() => handleAskAnalyst(`Extract and explain all disclosures related to ${title} from this report.`)}
            className="mt-3 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-xs font-bold transition-colors inline-flex items-center gap-1.5 cursor-pointer"
          >
            <MessageSquareText className="w-3.5 h-3.5" />
            <span>Ask AI Analyst to Extract</span>
          </button>
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
          description="Upload a corporate financial filing PDF to extract structured statement trends, cash flows, balance sheets, and key ratios."
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
  const insights = chartData?.executive_insights || [];
  const defaultUnit = chartData?.currency ? `${chartData.currency}` : 'Units';

  // Compute high-level KPI cards from grounded data
  const latestRev = revData[revData.length - 1];
  const priorRev = revData.length > 1 ? revData[0] : null;
  const revGrowth = priorRev && latestRev && priorRev.value > 0
    ? (((latestRev.value - priorRev.value) / priorRev.value) * 100).toFixed(1)
    : null;

  const latestProfit = profitData[profitData.length - 1];
  const priorProfit = profitData.length > 1 ? profitData[0] : null;
  const profitGrowth = priorProfit && latestProfit && Math.abs(priorProfit.value) > 0
    ? (((latestProfit.value - priorProfit.value) / Math.abs(priorProfit.value)) * 100).toFixed(1)
    : null;

  const latestAssetLiab = assetsLiabData[assetsLiabData.length - 1];
  const assetCoverage = latestAssetLiab && latestAssetLiab.liabilities > 0
    ? (latestAssetLiab.assets / latestAssetLiab.liabilities).toFixed(2)
    : null;

  return (
    <div className="space-y-6 animate-fade-in w-full min-w-0 pb-16">
      {/* Header & Report Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Financial Visual Analytics
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-3.5 h-3.5" /> Factual Grounding
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Deterministic quantitative statement extraction and multi-period analytics
          </p>
        </div>

        {/* Target Report Selector */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-semibold text-slate-500 flex-shrink-0">Target Filing:</span>
          <select
            value={selectedReportId}
            onChange={(e) => setSelectedReportId(e.target.value)}
            disabled={loading}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-emerald-500 truncate max-w-[280px] shadow-sm cursor-pointer disabled:opacity-60"
          >
            {reports.map((r) => (
              <option key={r.id} value={r.id}>
                {r.companyName || r.company_name || r.filename} ({r.financialYear || r.fiscal_period || 'Filing'})
              </option>
            ))}
          </select>
          {loading && <Loader2 className="w-4 h-4 animate-spin text-emerald-500 flex-shrink-0" />}
        </div>
      </div>

      {/* TOP FINANCIAL KPIS SUMMARY RIBBON */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Topline Revenue */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <BarChart3 className="w-4 h-4 text-emerald-500" />
              <span>Reported Revenue</span>
            </span>
            {latestRev?.page_number && getSourcePageBadge(latestRev.page_number)}
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {latestRev ? `${Number(latestRev.value).toLocaleString()}` : 'Disclosed in Filing'}
            </span>
            <span className="text-xs font-semibold text-slate-400">{latestRev?.unit || defaultUnit}</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Period: {latestRev?.period || selectedReport?.financialYear || 'Current'}</span>
            {revGrowth && (
              <span className={`font-bold flex items-center gap-0.5 ${Number(revGrowth) >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                {Number(revGrowth) >= 0 ? '▲' : '▼'} {Math.abs(Number(revGrowth))}% YoY
              </span>
            )}
          </div>
        </div>

        {/* KPI 2: Bottomline Net Profit */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-cyan-500" />
              <span>Net Profit (PAT)</span>
            </span>
            {latestProfit?.page_number && getSourcePageBadge(latestProfit.page_number)}
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {latestProfit ? `${Number(latestProfit.value).toLocaleString()}` : 'Disclosed in Filing'}
            </span>
            <span className="text-xs font-semibold text-slate-400">{latestProfit?.unit || defaultUnit}</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Period: {latestProfit?.period || selectedReport?.financialYear || 'Current'}</span>
            {profitGrowth && (
              <span className={`font-bold flex items-center gap-0.5 ${Number(profitGrowth) >= 0 ? 'text-cyan-500' : 'text-rose-500'}`}>
                {Number(profitGrowth) >= 0 ? '▲' : '▼'} {Math.abs(Number(profitGrowth))}% YoY
              </span>
            )}
          </div>
        </div>

        {/* KPI 3: Asset to Liability Coverage */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Scale className="w-4 h-4 text-indigo-500" />
              <span>Asset / Liability Ratio</span>
            </span>
            {latestAssetLiab?.page_number && getSourcePageBadge(latestAssetLiab.page_number)}
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {assetCoverage ? `${assetCoverage}x` : 'Solvent'}
            </span>
            <span className="text-xs font-semibold text-slate-400">Coverage</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-400">
              {latestAssetLiab ? `${latestAssetLiab.assets.toLocaleString()} vs ${latestAssetLiab.liabilities.toLocaleString()}` : 'Balance Sheet'}
            </span>
            <span className="font-bold text-indigo-500">Asset Solvency</span>
          </div>
        </div>

        {/* KPI 4: Primary Statement Ratio */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-purple-500" />
              <span>{keyRatios[0]?.name || 'Operating Efficiency'}</span>
            </span>
            {keyRatios[0]?.page_number && getSourcePageBadge(keyRatios[0].page_number)}
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {keyRatios[0]?.value || 'Disclosed in Notes'}
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-400 truncate max-w-[170px]">{keyRatios[0]?.description || 'Financial Ratio'}</span>
            <span className="font-bold text-purple-500">Grounded</span>
          </div>
        </div>
      </div>

      {/* EXECUTIVE FINANCIAL INSIGHTS & TAKEAWAYS HUB */}
      {insights.length > 0 && (
        <div className="p-5 rounded-2xl bg-gradient-to-br from-emerald-500/5 via-cyan-500/5 to-slate-900/5 dark:from-emerald-950/40 dark:via-cyan-950/30 dark:to-slate-900 border border-emerald-500/20 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-emerald-500/20 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                <Sparkles className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-extrabold text-slate-900 dark:text-white tracking-tight">
                Executive CFO Insights & Performance Takeaways
              </h3>
            </div>
            <span className="text-[11px] font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
              {selectedReport?.companyName || selectedReport?.company_name || 'Corporate Entity'}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {insights.map((insight, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-white/80 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2.5 text-xs text-slate-700 dark:text-slate-300 leading-relaxed shadow-xs"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>{insight}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Institutional Export Suite Action Bar */}
      <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Download className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-900 dark:text-white block">Institutional Export Suite</span>
            <span className="text-[10px] text-slate-400">Download formatted financial models, briefs, and slides</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() =>
              exportToExcel({
                companyName: selectedReport?.companyName || selectedReport?.company_name || 'Corporate Filing',
                financialYear: selectedReport?.financialYear || selectedReport?.fiscal_period || 'FY2026',
                analytics: chartData,
              })
            }
            className="px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export Excel Model (.csv)</span>
          </button>

          <button
            onClick={() =>
              exportToPdfBrief({
                companyName: selectedReport?.companyName || selectedReport?.company_name || 'Corporate Filing',
                financialYear: selectedReport?.financialYear || selectedReport?.fiscal_period || 'FY2026',
                analytics: chartData,
              })
            }
            className="px-3 py-1.5 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-700 dark:text-blue-400 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>CFO Executive Brief (PDF)</span>
          </button>

          <button
            onClick={() =>
              exportToPresentationDeck({
                companyName: selectedReport?.companyName || selectedReport?.company_name || 'Corporate Filing',
                financialYear: selectedReport?.financialYear || selectedReport?.fiscal_period || 'FY2026',
                analytics: chartData,
              })
            }
            className="px-3 py-1.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 text-purple-700 dark:text-purple-400 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Presentation className="w-3.5 h-3.5" />
            <span>Board Slide Deck (.json)</span>
          </button>
        </div>
      </div>

      {/* 1-Tap AI Analyst Deep-Dive Bar */}
      <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold text-slate-600 dark:text-slate-400 flex items-center gap-1.5 mr-1">
          <MessageSquareText className="w-3.5 h-3.5 text-emerald-500" />
          <span>Quick Analyst Queries:</span>
        </span>
        {[
          'Explain key revenue growth drivers and segment performance',
          'Analyze operating cost breakdown and EBITDA margin expansion',
          'Evaluate balance sheet debt levels and liquidity position',
          'Summarize top strategic business risks and auditor comments',
        ].map((queryText, idx) => (
          <button
            key={idx}
            onClick={() => handleAskAnalyst(queryText)}
            className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/60 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 text-xs font-medium transition-colors shadow-2xs flex items-center gap-1 cursor-pointer"
          >
            <span>{queryText}</span>
            <ArrowUpRight className="w-3 h-3 opacity-60" />
          </button>
        ))}
      </div>

      {/* Error state banner */}
      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl flex items-center justify-between text-rose-700 dark:text-rose-300 text-xs font-medium">
          <span>{error}</span>
          <button
            onClick={() => setSelectedReportId(selectedReportId)}
            className="flex items-center gap-1 font-bold underline hover:text-rose-900 cursor-pointer"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      )}

      {/* CHARTS GRID (6 PRIMARY + DIAGNOSTIC VISUALIZATIONS) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* 1. REVENUE TREND CHART */}
        {revData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <span>1. Topline Revenue Trajectory</span>
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
                      `${Number(value).toLocaleString()} ${item.payload.unit || defaultUnit}`,
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
          renderEmptyChartCard('1. Revenue Trend', BarChart3, 'No multi-period revenue table isolated in this section.')
        )}

        {/* 2. PROFIT TREND CHART */}
        {profitData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <span>2. Net Profit & Earnings Trend</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Metric: {profitData[0]?.metric_name || 'Net Profit (PAT)'} | Unit: {profitData[0]?.unit || defaultUnit}
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
                      `${Number(value).toLocaleString()} ${item.payload.unit || defaultUnit}`,
                      item.payload.metric_name || 'Net Profit',
                    ]}
                    labelFormatter={(label, items) => `Period: ${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#06b6d4"
                    strokeWidth={3}
                    dot={{ r: 6, fill: '#06b6d4' }}
                    name="Net Profit"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('2. Profit Trend', TrendingUp, 'No isolated profit time-series statement table.')
        )}

        {/* 3. EXPENSE TREND CHART */}
        {expenseData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span>3. Operating Expenses & Cost Profile</span>
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
                      `${Number(value).toLocaleString()} ${item.payload.unit || defaultUnit}`,
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
          renderEmptyChartCard('3. Expense Trend', DollarSign, 'No standalone operational expense breakdown table.')
        )}

        {/* 4. ASSETS VS LIABILITIES CHART */}
        {assetsLiabData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Scale className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                  <span>4. Balance Sheet: Assets vs Liabilities</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Solvency & Capital Structure | Unit: {assetsLiabData[0]?.unit || defaultUnit}
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
          renderEmptyChartCard('4. Assets vs Liabilities', Scale, 'No isolated balance sheet asset/liability schedule.')
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
          renderEmptyChartCard('5. Cash Flow', Wallet, 'No dedicated Cash Flow statement schedule extracted in this filing.')
        )}

        {/* 6. YEAR-OVER-YEAR COMPARISON CHART */}
        {yoyData.length > 0 ? (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <PieChart className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                  <span>6. Year-over-Year (YoY) Multi-Metric Variance</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Comparative Growth & Variance | Unit: {yoyData[0]?.unit || defaultUnit}
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
                      `${Number(value).toLocaleString()} ${item.payload.unit || defaultUnit}`,
                      name === 'previous_year_value'
                        ? `Prior (${item.payload.previous_year_period || 'Prior'})`
                        : `Current (${item.payload.current_year_period || 'Current'})`,
                    ]}
                    labelFormatter={(label, items) => `${label} (Page ${items[0]?.payload?.page_number || 'N/A'})`}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="previous_year_value" fill="#94a3b8" radius={[4, 4, 0, 0]} name="Prior Period" />
                  <Bar dataKey="current_year_value" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Current Period" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          renderEmptyChartCard('6. Year-over-Year Comparison', PieIcon, 'No multi-period comparative variance table in filing.')
        )}

      </div>

      {/* EXTRACTED KEY RATIOS SECTION */}
      <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4 mt-6">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <ArrowUpRight className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Verified Statement Ratios & Performance Metrics
              </h3>
              <p className="text-[11px] text-slate-400">
                Extracted directly from {selectedReport?.companyName || selectedReport?.company_name || selectedReport?.filename}
              </p>
            </div>
          </div>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-500/20 px-2.5 py-1 rounded-full uppercase tracking-wider font-extrabold">
            Grounded Evidence
          </span>
        </div>

        {keyRatios.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {keyRatios.map((ratio, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-50/80 dark:bg-slate-950/80 border border-slate-200/80 dark:border-slate-800 space-y-1.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 dark:text-slate-400 font-semibold">{ratio.name}</span>
                  {ratio.page_number && (
                    <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                      Page {ratio.page_number}
                    </span>
                  )}
                </div>
                <span className="text-2xl font-black text-slate-900 dark:text-slate-100 block tracking-tight">{ratio.value}</span>
                {ratio.description && (
                  <span className="text-[11px] text-slate-400 line-clamp-2 block">{ratio.description}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 text-center text-xs text-slate-400 italic">
            Financial ratios can also be dynamically analyzed and derived by querying the AI Analyst in the chat tab.
          </div>
        )}
      </div>
    </div>
  );
};
