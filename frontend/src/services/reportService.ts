import apiClient from './api';
import { ApiResponse, ReportItem, ReportDetail, ReportUploadResponse } from '../types';

export const reportService = {
  async uploadReport(file: File): Promise<ApiResponse<ReportUploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<ApiResponse<ReportUploadResponse>>(
      '/reports/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  async listReports(): Promise<ApiResponse<ReportItem[]>> {
    const response = await apiClient.get<ApiResponse<ReportItem[]>>('/reports');
    return response.data;
  },

  async getReportDetail(reportId: string): Promise<ApiResponse<ReportDetail>> {
    const response = await apiClient.get<ApiResponse<ReportDetail>>(`/reports/${reportId}`);
    return response.data;
  },

  async deleteReport(reportId: string): Promise<ApiResponse<any>> {
    const response = await apiClient.delete<ApiResponse<any>>(`/reports/${reportId}`);
    return response.data;
  },
};
