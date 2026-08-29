import React from 'react';
import {
  DollarSign,
  TrendingUp,
  Percent,
  Building2,
  Scale,
  Coins,
  Layers,
  Sparkles,
} from 'lucide-react';
import { FinancialOverviewData } from '../../types/financial';
import { FinancialKpiCard } from './FinancialKpiCard';

interface FinancialKpiGridProps {
  data?: FinancialOverviewData | null;
  onOpenCitation?: (page: number) => void;
}

export const FinancialKpiGrid: React.FC<FinancialKpiGridProps> = ({
  data,
  onOpenCitation,
}) => {
  const p1 = data?.reporting_periods?.[0] || 'FY2025';
  const p2 = data?.reporting_periods?.[1] || 'FY2026';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <h3 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white tracking-tight">
            Key Financial KPIs ({p1} vs {p2})
          </h3>
        </div>
        <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 hidden sm:inline-block">
          7 Core Statement Metrics
        </span>
      </div>

      {/* Responsive Grid: 1 col on mobile, 2 cols on tablet, 3-4 cols on desktop */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
        {/* 1. Revenue */}
        <FinancialKpiCard
          title="Revenue from Operations"
          item={data?.revenue}
          currentYearLabel={p2}
          previousYearLabel={p1}
          icon={DollarSign}
          color="emerald"
          onOpenCitation={onOpenCitation}
        />

        {/* 2. Net Profit */}
        <FinancialKpiCard
          title="Net Profit (PAT)"
          item={data?.net_profit}
          currentYearLabel={p2}
          previousYearLabel={p1}
          icon={TrendingUp}
          color="blue"
          onOpenCitation={onOpenCitation}
        />

        {/* 3. EPS */}
        <FinancialKpiCard
          title="Earnings Per Share (EPS)"
          item={data?.eps}
          currentYearLabel={p2}
          previousYearLabel={p1}
          icon={Percent}
          color="indigo"
          onOpenCitation={onOpenCitation}
        />

        {/* 4. Total Assets */}
        <FinancialKpiCard
          title="Total Assets"
          item={data?.total_assets}
          currentYearLabel={p2}
          previousYearLabel={p1}
          icon={Building2}
          color="cyan"
          onOpenCitation={onOpenCitation}
        />

        {/* 5. Total Liabilities */}
        <FinancialKpiCard
          title="Total Liabilities"
          item={data?.total_liabilities}
          currentYearLabel={p2}
          previousYearLabel={p1}
          icon={Scale}
          color="amber"
          onOpenCitation={onOpenCitation}
        />

        {/* 6. Equity */}
        <FinancialKpiCard
          title="Shareholders Equity / Net Worth"
          item={data?.equity}
          currentYearLabel={p2}
          previousYearLabel={p1}
          icon={Coins}
          color="violet"
          onOpenCitation={onOpenCitation}
        />

        {/* 7. Operating Cash Flow */}
        <FinancialKpiCard
          title="Operating Cash Flow"
          item={data?.cash_flow}
          currentYearLabel={p2}
          previousYearLabel={p1}
          icon={Layers}
          color="rose"
          onOpenCitation={onOpenCitation}
        />
      </div>
    </div>
  );
};

export default FinancialKpiGrid;
