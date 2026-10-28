import apiClient from './api';
import { ApiResponse, FinancialSummary, FinancialChartData } from '../types';
import { FinancialOverviewData, RiskAnalysisResponse } from '../types/financial';

// In-memory client cache to make switching sections (Dashboard <-> Analyst <-> Compare <-> Analytics) instant
const overviewCache = new Map<string, FinancialOverviewData>();
const riskCache = new Map<string, RiskAnalysisResponse>();
const chartCache = new Map<string, ApiResponse<FinancialChartData>>();
const summaryCache = new Map<string, ApiResponse<FinancialSummary>>();

// In-flight promise tracking to deduplicate concurrent requests for the same report
const inFlightOverview = new Map<string, Promise<FinancialOverviewData>>();
const inFlightRisk = new Map<string, Promise<RiskAnalysisResponse>>();
const inFlightChart = new Map<string, Promise<ApiResponse<FinancialChartData>>>();
const inFlightSummary = new Map<string, Promise<ApiResponse<FinancialSummary>>>();

export const financialService = {
  clearCache(reportId?: string) {
    if (reportId) {
      overviewCache.delete(reportId);
      riskCache.delete(reportId);
      chartCache.delete(reportId);
      summaryCache.delete(reportId);
    } else {
      overviewCache.clear();
      riskCache.clear();
      chartCache.clear();
      summaryCache.clear();
    }
  },

  async getSummary(reportId: string, forceRefresh = false): Promise<ApiResponse<FinancialSummary>> {
    if (!forceRefresh && summaryCache.has(reportId)) {
      return summaryCache.get(reportId)!;
    }
    if (inFlightSummary.has(reportId) && !forceRefresh) {
      return inFlightSummary.get(reportId)!;
    }

    const promise = (async () => {
      try {
        const response = await apiClient.get<ApiResponse<FinancialSummary>>(`/financials/${reportId}/summary`, {
          params: forceRefresh ? { refresh: true } : undefined,
        });
        summaryCache.set(reportId, response.data);
        return response.data;
      } finally {
        inFlightSummary.delete(reportId);
      }
    })();

    inFlightSummary.set(reportId, promise);
    return promise;
  },

  async getChartData(reportId: string, forceRefresh = false): Promise<ApiResponse<FinancialChartData>> {
    if (!forceRefresh && chartCache.has(reportId)) {
      return chartCache.get(reportId)!;
    }
    if (inFlightChart.has(reportId) && !forceRefresh) {
      return inFlightChart.get(reportId)!;
    }

    const promise = (async () => {
      try {
        const response = await apiClient.get<ApiResponse<FinancialChartData>>(`/financials/${reportId}/charts`, {
          params: forceRefresh ? { refresh: true } : undefined,
        });
        chartCache.set(reportId, response.data);
        return response.data;
      } finally {
        inFlightChart.delete(reportId);
      }
    })();

    inFlightChart.set(reportId, promise);
    return promise;
  },

  async getFinancialOverview(reportId: string, forceRefresh = false): Promise<FinancialOverviewData> {
    if (!forceRefresh && overviewCache.has(reportId)) {
      return overviewCache.get(reportId)!;
    }
    if (inFlightOverview.has(reportId) && !forceRefresh) {
      return inFlightOverview.get(reportId)!;
    }

    const promise = (async () => {
      try {
        let result: FinancialOverviewData;
        try {
          const response = await apiClient.get<ApiResponse<FinancialOverviewData>>(`/financials/${reportId}/overview`, {
            params: forceRefresh ? { refresh: true } : undefined,
          });
          result = response.data.data;
        } catch {
          // Fallback endpoint
          const response = await apiClient.get<FinancialOverviewData>(`/documents/${reportId}/overview`, {
            params: forceRefresh ? { refresh: true } : undefined,
          });
          result = response.data;
        }
        overviewCache.set(reportId, result);
        return result;
      } finally {
        inFlightOverview.delete(reportId);
      }
    })();

    inFlightOverview.set(reportId, promise);
    return promise;
  },

  async getRiskAnalysis(reportId: string, forceRefresh = false): Promise<RiskAnalysisResponse> {
    if (!forceRefresh && riskCache.has(reportId)) {
      return riskCache.get(reportId)!;
    }
    if (inFlightRisk.has(reportId) && !forceRefresh) {
      return inFlightRisk.get(reportId)!;
    }

    const promise = (async () => {
      try {
        let result: RiskAnalysisResponse;
        try {
          const response = await apiClient.get<ApiResponse<RiskAnalysisResponse>>(`/financials/${reportId}/risks`, {
            params: forceRefresh ? { refresh: true } : undefined,
          });
          result = response.data.data;
        } catch {
          // Fallback endpoint
          const response = await apiClient.get<RiskAnalysisResponse>(`/documents/${reportId}/risks`, {
            params: forceRefresh ? { refresh: true } : undefined,
          });
          result = response.data;
        }
        riskCache.set(reportId, result);
        return result;
      } finally {
        inFlightRisk.delete(reportId);
      }
    })();

    inFlightRisk.set(reportId, promise);
    return promise;
  },
};
