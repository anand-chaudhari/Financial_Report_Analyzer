import React from 'react';
import { Bot, Sparkles } from 'lucide-react';
import { SourceMetadata } from '../../services/conversationService';
import { WebSourceItem } from '../../services/chatService';
import { MarkdownRenderer } from './MarkdownRenderer';
import { MarketQuoteCard } from './MarketQuoteCard';
import { SourceList } from './SourceList';
import { MessageActions } from './MessageActions';
import { StreamingIndicator } from './StreamingIndicator';

export interface AssistantMessageProps {
  id: string;
  text: string;
  timestamp: string;
  sources?: SourceMetadata[];
  web_sources?: WebSourceItem[];
  market_data?: Record<string, any>;
  isGenerating?: boolean;
  isLastAssistant?: boolean;
  onOpenPdfCitation?: (citation: SourceMetadata) => void;
  onRegenerate?: () => void;
  onStop?: () => void;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({
  id,
  text,
  timestamp,
  sources = [],
  web_sources = [],
  market_data,
  isGenerating = false,
  isLastAssistant = false,
  onOpenPdfCitation,
  onRegenerate,
  onStop,
}) => {
  const hasText = Boolean(text && text.trim().length > 0);
  const isActivelyStreamingThis = isGenerating && isLastAssistant;

  return (
    <div className="flex gap-2.5 sm:gap-3.5 justify-start items-start animate-fade-in group">
      {/* Bot Avatar */}
      <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0 border border-emerald-500/20 shadow-xs mt-0.5">
        <Bot className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
      </div>

      {/* Main Message Card */}
      <div className="flex-1 max-w-full sm:max-w-3xl lg:max-w-4xl min-w-0">
        <div className="flex items-center justify-between gap-2 mb-1 px-1">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-extrabold text-slate-800 dark:text-slate-100 uppercase tracking-wider">
              FinSight AI Analyst
            </span>
            <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 text-[9px] font-extrabold uppercase">
              Grounded
            </span>
          </div>
          <span className="text-[10px] text-slate-400 dark:text-slate-500 tabular-nums">
            {timestamp}
          </span>
        </div>

        <div className="p-4 sm:p-5 rounded-2xl rounded-tl-xs bg-slate-50 dark:bg-slate-950/80 border border-slate-200/90 dark:border-slate-800/90 text-slate-800 dark:text-slate-200 shadow-xs space-y-3.5">
          {/* Live Market Quote Widget if present */}
          {market_data && market_data.symbol && (
            <MarketQuoteCard marketData={market_data} />
          )}

          {/* Main Answer Content */}
          <div className="text-xs sm:text-sm font-normal leading-relaxed break-words">
            {hasText ? (
              <>
                <MarkdownRenderer
                  content={text}
                  sources={sources}
                  isStreaming={isActivelyStreamingThis}
                  onOpenPdfCitation={onOpenPdfCitation}
                />
                {isActivelyStreamingThis && <StreamingIndicator hasStartedTokens />}
              </>
            ) : isActivelyStreamingThis ? (
              <StreamingIndicator status="Analyzing report context & searching filing..." />
            ) : null}
          </div>

          {/* Dedicated Sources Section: Separates Web Citations & PDF Grounded Citations */}
          <SourceList
            webSources={web_sources}
            pdfSources={sources}
            onOpenPdfCitation={onOpenPdfCitation}
          />

          {/* Action Toolbar (Copy, Regenerate, Stop) */}
          {hasText && (
            <MessageActions
              content={text}
              onRegenerate={onRegenerate}
              onStop={onStop}
              isGenerating={isGenerating}
              isLastAssistant={isLastAssistant}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default AssistantMessage;

