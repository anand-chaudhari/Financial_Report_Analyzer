import React from 'react';
import { Link } from 'react-router-dom';
import {
  FileSearch,
  Sparkles,
  ShieldCheck,
  BarChart4,
  ArrowRight,
  CheckCircle2,
  Zap,
} from 'lucide-react';

export const HomePage: React.FC = () => {
  return (
    <div className="space-y-16 py-6 sm:py-10 animate-fade-in w-full">
      {/* Hero Section */}
      <div className="text-center space-y-6 max-w-4xl mx-auto px-4">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-xs font-semibold backdrop-blur-md shadow-sm">
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span>Next-Generation Financial Document Intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.15]">
          Analyze Financial Reports with{' '}
          <span className="bg-gradient-to-r from-emerald-600 via-teal-500 to-cyan-500 dark:from-emerald-400 dark:via-teal-300 dark:to-cyan-400 bg-clip-text text-transparent glow-text">
            Intelligent AI
          </span>
        </h1>

        <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed">
          Upload annual reports, quarterly filings, and earnings PDFs. Instantly query balance sheets, inspect revenue trends, and review verified page citations with complete accuracy.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <Link
            to="/dashboard"
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold shadow-xl shadow-emerald-950/20 dark:shadow-emerald-950/70 hover:shadow-glow-emerald transition-all duration-200 cursor-pointer"
          >
            <span>Open Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/login"
            className="w-full sm:w-auto px-8 py-3.5 rounded-2xl bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 font-semibold border border-slate-300 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-600 transition-all shadow-sm cursor-pointer"
          >
            Sign In / Register
          </Link>
        </div>

        {/* Feature Highlights Pills */}
        <div className="pt-4 flex flex-wrap items-center justify-center gap-4 sm:gap-8 text-xs text-slate-600 dark:text-slate-400 font-medium">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Verified Page Citations
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Interactive Visual Analytics
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Executive CFO Summaries
          </span>
        </div>
      </div>

      {/* Feature Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <div className="group relative p-7 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/40 transition-all duration-300 shadow-sm dark:shadow-glass hover:shadow-lg dark:hover:shadow-glow-emerald">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center mb-5 text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform">
            <FileSearch className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">Verified Page Citations</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
            Every answer and financial metric is directly cited with the exact page number of the original document for complete transparency and rapid verification.
          </p>
        </div>

        <div className="group relative p-7 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-cyan-500/40 transition-all duration-300 shadow-sm dark:shadow-glass hover:shadow-lg dark:hover:shadow-glow-cyan">
          <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center mb-5 text-cyan-600 dark:text-cyan-400 group-hover:scale-110 transition-transform">
            <BarChart4 className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">Automated Visual Analytics</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
            Automatically extracts financial statements and renders revenue, profit margin, and EBITDA trends into interactive charts and key ratio cards.
          </p>
        </div>

        <div className="group relative p-7 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-amber-500/40 transition-all duration-300 shadow-sm dark:shadow-glass hover:shadow-lg dark:hover:shadow-glow-emerald">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center mb-5 text-amber-600 dark:text-amber-400 group-hover:scale-110 transition-transform">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">High-Precision Responses</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
            Strict AI guardrails ensure responses are synthesized purely from the uploaded report, proactively alerting you if specific metrics are undisclosed.
          </p>
        </div>
      </div>

      {/* 3-Step Simple Workflow for Users */}
      <div className="relative rounded-3xl p-8 sm:p-10 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm dark:shadow-2xl">
        <div className="max-w-3xl mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/25 text-cyan-700 dark:text-cyan-400 text-xs font-semibold mb-3">
            <Zap className="w-3.5 h-3.5" />
            <span>Effortless Workflow</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">How FinSight AI Works in 3 Simple Steps</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
            Turn complex, multi-page financial filings into instant answers and visual dashboards.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold flex items-center justify-center text-sm">1</div>
            <div className="text-base font-semibold text-slate-900 dark:text-slate-100">Upload Your Report</div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Drag and drop any corporate financial report or earnings PDF. The system automatically processes the pages and indexes tables.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2.5">
            <div className="w-8 h-8 rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-400 font-bold flex items-center justify-center text-sm">2</div>
            <div className="text-base font-semibold text-slate-900 dark:text-slate-100">Ask Natural Questions</div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Inquire about revenue breakdown, risk factors, debt maturity, or profit margins. Receive detailed answers with verified page numbers.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2.5">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold flex items-center justify-center text-sm">3</div>
            <div className="text-base font-semibold text-slate-900 dark:text-slate-100">Inspect Charts & Summaries</div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              View automated time-series charts of corporate performance and read structured executive CFO summaries.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
