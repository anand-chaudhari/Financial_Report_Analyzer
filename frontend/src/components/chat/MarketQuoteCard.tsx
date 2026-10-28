import React from 'react';
import { TrendingUp, TrendingDown, Clock, Activity } from 'lucide-react';

interface MarketQuoteCardProps {
  marketData?: Record<string, any>;
}

export const MarketQuoteCard: React.FC<MarketQuoteCardProps> = ({ marketData }) => {
  if (!marketData || !marketData.symbol) return null;

  const symbol = String(marketData.symbol).toUpperCase();
  const shortName = marketData.short_name || marketData.name || '';
  const price = marketData.current_price !== undefined ? Number(marketData.current_price) : null;
  const changePercent =
    marketData.change_percent !== undefined ? Number(marketData.change_percent) : null;
  const changeValue = marketData.change !== undefined ? Number(marketData.change) : null;
  const currencySymbol = marketData.currency === 'INR' || symbol.endsWith('.NS') || symbol.endsWith('.BO') ? '₹' : '$';
  const isPositive = changePercent !== null ? changePercent >= 0 : true;

  return (
    <div className="p-3.5 sm:p-4 rounded-2xl bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-emerald-50/40 dark:from-slate-900/90 dark:via-slate-900/80 dark:to-emerald-950/20 border border-blue-200/80 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isPositive
            ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
            : 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/20'
        }`}>
          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-black text-slate-900 dark:text-white uppercase tracking-wider text-xs sm:text-sm">
              {symbol}
            </span>
            <span className="px-1.5 py-0.2 rounded bg-slate-200/70 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-bold">
              Live Quote
            </span>
          </div>
          {shortName && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium truncate max-w-[200px]">
              {shortName}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 ml-auto sm:ml-0">
        {price !== null && (
          <div className="text-right">
            <span className="font-black text-slate-900 dark:text-white text-base sm:text-lg tabular-nums">
              {currencySymbol}{price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            {changePercent !== null && (
              <div className="flex items-center justify-end gap-1 mt-0.5">
                <span
                  className={`px-2 py-0.5 rounded-full font-bold text-[10px] flex items-center gap-0.5 tabular-nums ${
                    isPositive
                      ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                      : 'bg-rose-500/20 text-rose-700 dark:text-rose-300'
                  }`}
                >
                  {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
                  {changeValue !== null && ` (${isPositive ? '+' : ''}${changeValue.toFixed(2)})`}
                </span>
              </div>
            )}
          </div>
        )}

        {marketData.market_cap && (
          <div className="hidden md:block pl-3 border-l border-slate-200 dark:border-slate-800 text-right">
            <span className="text-[10px] text-slate-400 block font-medium">Market Cap</span>
            <span className="font-bold text-slate-700 dark:text-slate-300 text-xs font-mono">
              {currencySymbol}{(Number(marketData.market_cap) / 1e9).toFixed(2)}B
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketQuoteCard;

