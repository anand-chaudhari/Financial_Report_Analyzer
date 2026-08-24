import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import { conversationService, ConversationItem } from '../services/conversationService';
import { EmptyState } from '../components/EmptyState';
import { MessageSquare, Search, BookOpen, Trash2, ArrowRight, Bot, Edit3, Clock, Sparkles } from 'lucide-react';

export const ChatHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const { reports } = useReportContext();
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const loadAllConversations = async () => {
    setLoading(true);
    const list = await conversationService.getConversations();
    setConversations(list);
    setLoading(false);
  };

  useEffect(() => {
    loadAllConversations();
  }, []);

  const filtered = conversations.filter((c) => {
    const titleMatch = c.title.toLowerCase().includes(search.toLowerCase());
    const docMatch = c.documentId.toLowerCase().includes(search.toLowerCase());
    return titleMatch || docMatch;
  });

  const handleDelete = async (conversationId: string) => {
    await conversationService.deleteConversation(conversationId);
    await loadAllConversations();
  };

  return (
    <div className="space-y-6 animate-fade-in w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Firestore Conversation History
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Review and continue past AI Analyst conversations linked to your account
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search conversation titles..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Conversations list */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-500">Loading conversation history from Firestore...</p>
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No Past Conversations Found"
            description="You haven't started any AI Analyst conversation threads yet. Select a report in the AI Analyst workspace to start asking questions."
            actionLabel="Go to AI Analyst"
            onAction={() => navigate('/analyst')}
            icon={MessageSquare}
          />
        ) : (
          filtered.map((conv) => {
            const docMatch = reports.find((r) => r.id === conv.documentId || r.documentId === conv.documentId);
            const reportName = docMatch?.companyName || docMatch?.company_name || docMatch?.filename || conv.documentId;

            return (
              <div
                key={conv.conversationId}
                className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3.5 transition-all hover:border-slate-300 dark:hover:border-slate-700"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2.5 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-bold text-xs border border-emerald-500/20">
                      {reportName}
                    </span>
                    <span className="text-slate-300 dark:text-slate-700">•</span>
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> Updated {new Date(conv.updatedAt).toLocaleString()}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/analyst?doc=${conv.documentId}&conv=${conv.conversationId}`)}
                      className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer"
                    >
                      <span>Continue Analysis</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => handleDelete(conv.conversationId)}
                      className="p-1.5 text-slate-400 hover:text-rose-500 rounded-lg transition-colors cursor-pointer"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-extrabold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    <span>{conv.title}</span>
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Conversation ID: <span className="font-mono">{conv.conversationId}</span>
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
