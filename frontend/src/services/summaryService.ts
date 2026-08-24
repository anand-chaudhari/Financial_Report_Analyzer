import apiClient from './api';

export interface SummarySection {
  text: string;
  pages: number[];
  value?: string;
}

export interface KpiCard {
  label: string;
  value: string;
  change?: string;
  icon?: string;
}

export interface DocumentSummaryData {
  success: boolean;
  document_id: string;
  company_name: string;
  financial_year: string;
  file_name: string;
  
  executive_summary: SummarySection;
  key_financial_highlights: SummarySection;
  revenue: SummarySection;
  profit_loss: SummarySection;
  major_expenses: SummarySection;
  assets: SummarySection;
  liabilities: SummarySection;
  cash_flow: SummarySection;
  business_risks: SummarySection;
  management_discussion: SummarySection;
  future_plans: SummarySection;

  kpis: KpiCard[];
}

export const summaryService = {
  async getDocumentSummary(documentId: string): Promise<DocumentSummaryData> {
    const response = await apiClient.post<DocumentSummaryData>(`/documents/${documentId}/summary`);
    return response.data;
  },
};
