import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import { summaryService, DocumentSummaryData, SummarySection } from '../services/summaryService';
import {
  FileText,
  Sparkles,
  TrendingUp,
  DollarSign,
  PieChart,
  ShieldAlert,
  BookOpen,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  Printer,
  Building2,
  Calendar,
  CheckCircle2,
  Compass,
  FileCheck,
  Zap,
  BarChart3,
  Scale,
  Briefcase,
  RefreshCw,
} from 'lucide-react';

export const ReportSummaryPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { reports } = useReportContext();

  const [summaryData, setSummaryData] = useState<DocumentSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const selectedReportId = id || (reports[0]?.id ?? '');
  const activeReport = reports.find((r) => r.id === selectedReportId || r.documentId === selectedReportId);

  const fetchSummary = async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await summaryService.getDocumentSummary(selectedReportId);
      setSummaryData(data);
    } catch (err: any) {
      console.error('Error fetching document summary:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to generate AI document summary.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [selectedReportId]);

  const handleCopySummary = () => {
    if (!summaryData) return;
    const text = `
FINANCIAL REPORT AI SUMMARY: ${summaryData.company_name} (${summaryData.financial_year})
--------------------------------------------------------------------------------
1. EXECUTIVE SUMMARY:
${summaryData.executive_summary.text}

2. KEY FINANCIAL HIGHLIGHTS:
${summaryData.key_financial_highlights.text}

3. REVENUE: ${summaryData.revenue.value || ''}
${summaryData.revenue.text}

4. PROFIT / LOSS: ${summaryData.profit_loss.value || ''}
${summaryData.profit_loss.text}

5. MAJOR EXPENSES:
${summaryData.major_expenses.text}

6. TOTAL ASSETS: ${summaryData.assets.value || ''}
${summaryData.assets.text}

7. LIABILITIES: ${summaryData.liabilities.value || ''}
${summaryData.liabilities.text}

8. CASH FLOW:
${summaryData.cash_flow.text}

9. BUSINESS RISKS:
${summaryData.business_risks.text}

10. MANAGEMENT DISCUSSION:
${summaryData.management_discussion.text}

11. FUTURE PLANS:
${summaryData.future_plans.text}
    `.trim();

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderSectionCard = (
    title: string,
    icon: React.ReactNode,
    section: SummarySection,
    badgeColor: string = 'emerald'
  ) => {
    const isNotAvailable =
      !section.text ||
      section.text.toLowerCase().includes('not available') ||
      section.text.trim() === '';

    return (
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4 transition-all hover:border-slate-300 dark:hover:border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              {icon}
            </div>
            <div>
              <h3 className="text-base font-extrabold text-slate-900 dark:text-white tracking-tight">
                {title}
              </h3>
              {section.value && (
                <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {section.value}
                </p>
              )}
            </div>
          </div>

          {/* Source Page References */}
          {section.pages && section.pages.length > 0 && !isNotAvailable && (
            <div className="flex items-center gap-1.5 flex-wrap">
              {section.pages.map((pg, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-bold text-[10px] flex items-center gap-1"
                >
                  <BookOpen className="w-3 h-3 text-emerald-500" />
                  Page {pg}
                </span>
              ))}
            </div>
          )}
        </div>

        {isNotAvailable ? (
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 text-xs italic flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Not available in the uploaded report.</span>
          </div>
        ) : (
          <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap font-normal">
            {section.text}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto w-full min-w-0 animate-fade-in pb-10">
      {/* Top Navigation & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 sm:p-7 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3 overflow-hidden">
          <button
            onClick={() => navigate('/reports')}
            className="p-2.5 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer flex-shrink-0"
            title="Back to reports"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="min-w-0">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold mb-1">
              <Sparkles className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Grounded AI Executive Summary</span>
            </div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight truncate">
              {summaryData?.company_name || activeReport?.companyName || 'Financial Report Summary'}
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">
              {summaryData?.financial_year || activeReport?.financialYear || 'FY2026'} • {summaryData?.file_name || activeReport?.filename || 'annual_report_2025_2026.pdf'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 flex-wrap sm:flex-nowrap">
          <button
            onClick={fetchSummary}
            disabled={loading}
            className="px-3.5 py-2.5 rounded-2xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50 flex-shrink-0"
            title="Re-analyze document and regenerate summary"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Analyzing...' : 'Regenerate'}</span>
          </button>

          <button
            onClick={handleCopySummary}
            disabled={!summaryData || loading}
            className="px-3.5 py-2.5 rounded-2xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50 flex-shrink-0"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
            <span>{copied ? 'Copied!' : 'Copy Summary'}</span>
          </button>

          <button
            onClick={() => window.print()}
            disabled={!summaryData || loading}
            className="px-4 py-2.5 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-bold flex items-center gap-2 shadow-md shadow-emerald-500/20 transition-all cursor-pointer disabled:opacity-50 flex-shrink-0"
          >
            <Printer className="w-4 h-4" />
            <span>Print</span>
          </button>
        </div>
      </div>

      {/* LOADING STATE */}
      {loading && (
        <div className="py-24 text-center space-y-5 p-10 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm max-w-xl mx-auto">
          <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin" />
            <Loader2 className="w-7 h-7 text-emerald-500 animate-spin" />
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Generating Grounded Financial Summary...
            </h3>
            <p className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold animate-pulse">
              Extracting MD&A, Financial Statements, Revenue & Risk Factors from ChromaDB...
            </p>
          </div>
        </div>
      )}

      {/* ERROR STATE */}
      {error && !loading && (
        <div className="p-6 rounded-3xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 space-y-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-bold">Failed to Generate Report Summary</h3>
              <p className="text-xs opacity-90 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchSummary}
            className="px-4 py-2 rounded-xl bg-rose-600 text-white font-bold text-xs cursor-pointer hover:bg-rose-500 transition-colors"
          >
            Retry Generation
          </button>
        </div>
      )}

      {/* SUMMARY CONTENT */}
      {summaryData && !loading && (
        <div className="space-y-8">
          {/* KPI CARDS GRID */}
          {summaryData.kpis && summaryData.kpis.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {summaryData.kpis.map((kpi, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2"
                >
                  <p className="text-[11px] font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                    {kpi.label}
                  </p>
                  <p className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight">
                    {kpi.value}
                  </p>
                  {kpi.change && (
                    <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      {kpi.change}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 11 STRUCTURED GROUNDED SECTIONS */}
          <div className="space-y-6">
            {renderSectionCard(
              '1. Executive Summary',
              <Sparkles className="w-5 h-5" />,
              summaryData.executive_summary
            )}

            {renderSectionCard(
              '2. Key Financial Highlights',
              <TrendingUp className="w-5 h-5" />,
              summaryData.key_financial_highlights
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {renderSectionCard(
                '3. Revenue Analysis',
                <DollarSign className="w-5 h-5" />,
                summaryData.revenue
              )}

              {renderSectionCard(
                '4. Profit & Loss Statement',
                <PieChart className="w-5 h-5" />,
                summaryData.profit_loss
              )}
            </div>

            {renderSectionCard(
              '5. Major Expenses Breakdown',
              <BarChart3 className="w-5 h-5" />,
              summaryData.major_expenses
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {renderSectionCard(
                '6. Total Assets',
                <Building2 className="w-5 h-5" />,
                summaryData.assets
              )}

              {renderSectionCard(
                '7. Liabilities & Debt',
                <Scale className="w-5 h-5" />,
                summaryData.liabilities
              )}
            </div>

            {renderSectionCard(
              '8. Cash Flow Summary',
              <Zap className="w-5 h-5" />,
              summaryData.cash_flow
            )}

            {renderSectionCard(
              '9. Business Risks & Disclosures',
              <ShieldAlert className="w-5 h-5" />,
              summaryData.business_risks
            )}

            {renderSectionCard(
              '10. Management Discussion & Analysis (MD&A)',
              <Briefcase className="w-5 h-5" />,
              summaryData.management_discussion
            )}

            {renderSectionCard(
              '11. Future Strategic Plans & Guidance',
              <Compass className="w-5 h-5" />,
              summaryData.future_plans
            )}
          </div>
        </div>
      )}
    </div>
  );
};
