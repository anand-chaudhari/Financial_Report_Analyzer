export interface FinancialMetricSeries {
  period: string;
  value: number;
  unit: string;
}

export interface KeyRatio {
  name: string;
  value: string;
  description?: string;
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
  revenue_chart: FinancialMetricSeries[];
  net_income_chart: FinancialMetricSeries[];
  operating_expenses_chart: FinancialMetricSeries[];
  key_ratios: KeyRatio[];
  extracted_at: string;
}
