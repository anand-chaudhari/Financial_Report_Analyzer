import apiClient from './api';
import { ApiResponse, FinancialSummary, FinancialChartData } from '../types';

export const financialService = {
  async getSummary(reportId: string): Promise<ApiResponse<FinancialSummary>> {
    const response = await apiClient.get<ApiResponse<FinancialSummary>>(`/financials/${reportId}/summary`);
    return response.data;
  },

  async getChartData(reportId: string): Promise<ApiResponse<FinancialChartData>> {
    const response = await apiClient.get<ApiResponse<FinancialChartData>>(`/financials/${reportId}/charts`);
    return response.data;
  },
};
