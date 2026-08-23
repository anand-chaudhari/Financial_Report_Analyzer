import React, { useState } from 'react';
import { MOCK_REPORTS, MOCK_CONVERSATIONS } from '../utils/mockData';
import { Bot, Sparkles, Send, BookOpen, FileText, CheckCircle2 } from 'lucide-react';

export const AnalystPage: React.FC = () => {
  const [selectedReportId, setSelectedReportId] = useState(MOCK_REPORTS[0].id);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState(MOCK_CONVERSATIONS);
  const [loading, setLoading] = useState(false);

  const selectedReport = MOCK_REPORTS.find((r) => r.id === selectedReportId) || MOCK_REPORTS[0];

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userQ = query;
    setQuery('');
    setLoading(true);

    setTimeout(() => {
      const newAnswer = {
        id: `conv_${Date.now()}`,
        reportId: selectedReport.id,
        reportName: selectedReport.company,
        ticker: selectedReport.ticker,
        question: userQ,
        answer: `According to ${selectedReport.company}'s filing, the requested metrics show robust operating resilience with disciplined expense management and strong cash flow generation.`,
        timestamp: 'Just now',
        citations: [
          {
            page_number: 14,
            section: 'Item 7 - Management Discussion',
            snippet: `Direct snippet extracted from ${selectedReport.filename} regarding the query parameters.`,
          },
        ],
      };

      setMessages((prev) => [newAnswer, ...prev]);
      setLoading(false);
    }, 1000);
  };

  return (
    <div className="space-y-6 animate-fade-in w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-400 text-xs font-semibold mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Copilot</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Financial AI Analyst
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Ask natural language questions against indexed corporate filings with verified citations
          </p>
        </div>

        {/* Report Selector Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Document:</span>
          <select
            value={selectedReportId}
            onChange={(e) => setSelectedReportId(e.target.value)}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-emerald-500"
          >
            {MOCK_REPORTS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.company} ({r.filingType})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-6">
        {/* Sample queries */}
        <div className="flex flex-wrap gap-2">
          {[
            'What is the operating cash flow & free cash flow?',
            'Summarize key risk factors disclosed in Item 1A.',
            'What is the effective tax rate and guidance?',
            'Break down segment revenues and YoY growth.',
          ].map((prompt) => (
            <button
              key={prompt}
              onClick={() => setQuery(prompt)}
              className="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
            >
              "{prompt}"
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Ask a question about ${selectedReport.company}...`}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-2xl pl-4 pr-14 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 shadow-sm"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 disabled:opacity-40 text-white rounded-xl transition-all cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>

        {/* Conversation Stream */}
        <div className="space-y-4 pt-2">
          {loading && (
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
              <span className="text-xs text-slate-500">Synthesizing answer from retrieved chunks...</span>
            </div>
          )}

          {messages.map((item) => (
            <div
              key={item.id}
              className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold">
                    {item.ticker}
                  </span>
                  <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    {item.question}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400">{item.timestamp}</span>
              </div>

              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                {item.answer}
              </p>

              {item.citations && item.citations.length > 0 && (
                <div className="pt-2 border-t border-slate-200 dark:border-slate-850 flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase text-slate-400">Citations:</span>
                  {item.citations.map((c, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-[10px] font-semibold border border-emerald-500/20"
                    >
                      <BookOpen className="w-3 h-3" />
                      Page {c.page_number}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
