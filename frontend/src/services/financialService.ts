import apiClient from './api';
import { ApiResponse, FinancialSummary, FinancialChartData } from '../types';
import { FinancialOverviewData, RiskAnalysisResponse } from '../types/financial';

export const financialService = {
  async getSummary(reportId: string): Promise<ApiResponse<FinancialSummary>> {
    const response = await apiClient.get<ApiResponse<FinancialSummary>>(`/financials/${reportId}/summary`);
    return response.data;
  },

  async getChartData(reportId: string): Promise<ApiResponse<FinancialChartData>> {
    const response = await apiClient.get<ApiResponse<FinancialChartData>>(`/financials/${reportId}/charts`);
    return response.data;
  },

  async getFinancialOverview(reportId: string): Promise<FinancialOverviewData> {
    try {
      const response = await apiClient.get<ApiResponse<FinancialOverviewData>>(`/financials/${reportId}/overview`);
      return response.data.data;
    } catch (e) {
      // Fallback endpoint
      const response = await apiClient.get<FinancialOverviewData>(`/documents/${reportId}/overview`);
      return response.data;
    }
  },

  async getRiskAnalysis(reportId: string): Promise<RiskAnalysisResponse> {
    try {
      const response = await apiClient.get<ApiResponse<RiskAnalysisResponse>>(`/financials/${reportId}/risks`);
      return response.data.data;
    } catch (e) {
      // Fallback endpoint
      const response = await apiClient.get<RiskAnalysisResponse>(`/documents/${reportId}/risks`);
      return response.data;
    }
  },
};
