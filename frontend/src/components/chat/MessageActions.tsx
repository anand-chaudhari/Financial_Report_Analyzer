import React, { useState } from 'react';
import { Copy, Check, RefreshCw, Square } from 'lucide-react';

interface MessageActionsProps {
  content: string;
  onRegenerate?: () => void;
  onStop?: () => void;
  isGenerating?: boolean;
  isLastAssistant?: boolean;
}

export const MessageActions: React.FC<MessageActionsProps> = ({
  content,
  onRegenerate,
  onStop,
  isGenerating = false,
  isLastAssistant = false,
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-1.5 pt-2 text-slate-400">
      {/* Copy Response Button */}
      <button
        type="button"
        onClick={handleCopy}
        className="p-1.5 rounded-lg hover:bg-slate-200/60 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors text-xs flex items-center gap-1 cursor-pointer"
        title="Copy response to clipboard"
        aria-label="Copy response"
      >
        {copied ? (
          <>
            <Check className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">Copied</span>
          </>
        ) : (
          <>
            <Copy className="w-3.5 h-3.5" />
            <span className="text-[10px] font-medium hidden sm:inline">Copy</span>
          </>
        )}
      </button>

      {/* Regenerate Button (last assistant message only) */}
      {isLastAssistant && onRegenerate && !isGenerating && (
        <button
          type="button"
          onClick={onRegenerate}
          className="p-1.5 rounded-lg hover:bg-slate-200/60 dark:hover:bg-slate-800 text-slate-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors text-xs flex items-center gap-1 cursor-pointer"
          title="Regenerate this response"
          aria-label="Regenerate response"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span className="text-[10px] font-medium hidden sm:inline">Retry</span>
        </button>
      )}

      {/* Stop generating button if actively streaming this message */}
      {isGenerating && isLastAssistant && onStop && (
        <button
          type="button"
          onClick={onStop}
          className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 transition-colors text-xs flex items-center gap-1 cursor-pointer"
          title="Stop response generation"
          aria-label="Stop generation"
        >
          <Square className="w-3.5 h-3.5 fill-current" />
          <span className="text-[10px] font-bold">Stop</span>
        </button>
      )}
    </div>
  );
};

export default MessageActions;

