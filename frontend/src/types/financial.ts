export interface MetricDataPoint {
  period: string;
  value: number;
  unit: string;
  page_number?: number;
  metric_name?: string;
}

export interface AssetsLiabilitiesPoint {
  period: string;
  assets: number;
  liabilities: number;
  unit: string;
  page_number?: number;
}

export interface CashFlowPoint {
  period: string;
  operating?: number;
  investing?: number;
  financing?: number;
  net_cash_flow?: number;
  unit: string;
  page_number?: number;
}

export interface YoYComparisonPoint {
  metric_name: string;
  previous_year_period: string;
  previous_year_value: number;
  current_year_period: string;
  current_year_value: number;
  yoy_change_percent?: number;
  unit: string;
  page_number?: number;
}

export interface KeyRatio {
  name: string;
  value: string;
  description?: string;
  page_number?: number;
}

export interface FinancialSummary {
  report_id: string;
  company_name: string;
  fiscal_period: string;
  currency: string;
  executive_summary: string;
  key_highlights: string[];
  risks_and_challenges: string[];
}

export interface FinancialChartData {
  report_id: string;
  company_name: string;
  has_data?: boolean;
  currency?: string;
  revenue_chart?: MetricDataPoint[];
  profit_chart?: MetricDataPoint[];
  net_income_chart?: MetricDataPoint[];
  expense_chart?: MetricDataPoint[];
  operating_expenses_chart?: MetricDataPoint[];
  assets_vs_liabilities_chart?: AssetsLiabilitiesPoint[];
  cash_flow_chart?: CashFlowPoint[];
  yoy_comparison_chart?: YoYComparisonPoint[];
  key_ratios?: KeyRatio[];
  extracted_at?: string;
}

export interface OverviewMetricItem {
  name: string;
  fy2025_value?: string;
  fy2026_value?: string;
  growth?: string;
  unit?: string;
  page_number?: number;
  is_available?: boolean;
}

export interface FinancialOverviewData {
  report_id: string;
  company_name: string;
  currency: string;
  has_data: boolean;
  reporting_periods: string[];
  revenue: OverviewMetricItem;
  net_profit: OverviewMetricItem;
  eps: OverviewMetricItem;
  total_assets: OverviewMetricItem;
  total_liabilities: OverviewMetricItem;
  equity: OverviewMetricItem;
  cash_flow: OverviewMetricItem;
  important_ratios: OverviewMetricItem[];
  executive_overview?: string;
  extracted_at?: string;
}

export interface SourceMetadata {
  page_number: number;
  section: string;
  document_name?: string;
  snippet?: string;
  confidence?: number;
}

export type FinancialAnalyticsResponse = FinancialChartData;
