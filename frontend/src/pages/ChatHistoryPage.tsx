import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MOCK_CONVERSATIONS, MockConversation } from '../utils/mockData';
import { MessageSquare, Search, BookOpen, Trash2, ArrowRight, Bot } from 'lucide-react';

export const ChatHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<MockConversation[]>(MOCK_CONVERSATIONS);
  const [search, setSearch] = useState('');

  const filtered = conversations.filter(
    (c) =>
      c.question.toLowerCase().includes(search.toLowerCase()) ||
      c.answer.toLowerCase().includes(search.toLowerCase()) ||
      c.reportName.toLowerCase().includes(search.toLowerCase()) ||
      c.ticker.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
  };

  return (
    <div className="space-y-6 animate-fade-in w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            AI Query History
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Review past questions, grounded answers, and verified page references
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search query history..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Conversations list */}
      <div className="space-y-4">
        {filtered.length === 0 ? (
          <div className="p-12 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-slate-500 text-xs">
            No queries match your search.
          </div>
        ) : (
          filtered.map((conv) => (
            <div
              key={conv.id}
              className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3 transition-all hover:border-slate-300 dark:hover:border-slate-700"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-bold text-xs border border-emerald-500/20">
                    {conv.ticker}
                  </span>
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    {conv.reportName}
                  </span>
                  <span className="text-slate-300 dark:text-slate-700">•</span>
                  <span className="text-[11px] text-slate-400">{conv.timestamp}</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDelete(conv.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-500 rounded-lg transition-colors cursor-pointer"
                    title="Delete query"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => navigate(`/reports/${conv.reportId}`)}
                    className="flex items-center gap-1 px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-xs font-bold hover:bg-emerald-500/20 transition-colors cursor-pointer"
                  >
                    <span>Open Report</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  "{conv.question}"
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
                  {conv.answer}
                </p>
              </div>

              {conv.citations && conv.citations.length > 0 && (
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-bold uppercase text-slate-400">
                    Verified Citations:
                  </span>
                  {conv.citations.map((c, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-slate-50 dark:bg-slate-950 text-emerald-700 dark:text-emerald-400 text-[10px] font-semibold border border-slate-200 dark:border-slate-800"
                    >
                      <BookOpen className="w-3 h-3" />
                      Page {c.page_number} ({c.section || 'Statement'})
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
