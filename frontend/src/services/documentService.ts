import apiClient from './api';
import { ApiResponse } from '../types';
import { ReportItem } from '../types/report';

export const documentService = {
  async uploadDocument(file: File): Promise<ReportItem> {
    const formData = new FormData();
    formData.append('file', file);

    // Call /api/documents/upload or /api/v1/documents/upload
    const response = await apiClient.post<any>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    const resData = response.data;
    const item = resData.data || resData;

    const docId = item.documentId || item.report_id || item.id || `doc_${Date.now()}`;
    const name = item.fileName || item.filename || file.name;
    const pages = item.pageCount || item.total_pages || 1;
    const size = item.fileSize || item.file_size || file.size;

    const reportItem: ReportItem = {
      id: docId,
      documentId: docId,
      filename: name,
      fileName: name,
      file_size: size,
      fileSize: size,
      total_pages: pages,
      pageCount: pages,
      status: item.status || 'completed',
      uploaded_at: item.uploadedAt || item.uploaded_at || new Date().toISOString(),
      uploadedAt: item.uploadedAt || item.uploaded_at || new Date().toISOString(),
      company_name: item.companyName || item.company_name || name.replace('.pdf', '').replace(/_/g, ' '),
      companyName: item.companyName || item.company_name || name.replace('.pdf', '').replace(/_/g, ' '),
      financialYear: item.financialYear || item.fiscal_period || `FY${new Date().getFullYear()}`,
      fiscal_period: item.financialYear || item.fiscal_period || `FY${new Date().getFullYear()}`,
      storage_url: item.storageUrl || item.storage_url || '',
      storageUrl: item.storageUrl || item.storage_url || '',
      filingType: '10-K',
      ticker: (item.companyName || name).substring(0, 4).toUpperCase(),
    };

    return reportItem;
  },

  async getDocuments(): Promise<ReportItem[]> {
    try {
      const response = await apiClient.get<any>('/documents');
      const data = response.data;
      const list = Array.isArray(data) ? data : data.data || [];

      return list.map((item: any) => {
        const docId = item.documentId || item.id;
        const name = item.fileName || item.filename || 'Report.pdf';
        const pages = item.pageCount || item.total_pages || 1;
        const size = item.fileSize || item.file_size || 0;

        return {
          id: docId,
          documentId: docId,
          filename: name,
          fileName: name,
          file_size: size,
          fileSize: size,
          total_pages: pages,
          pageCount: pages,
          status: item.status || 'completed',
          uploaded_at: item.uploadedAt || item.uploaded_at || new Date().toISOString(),
          uploadedAt: item.uploadedAt || item.uploaded_at || new Date().toISOString(),
          company_name: item.companyName || item.company_name || name.replace('.pdf', '').replace(/_/g, ' '),
          companyName: item.companyName || item.company_name || name.replace('.pdf', '').replace(/_/g, ' '),
          financialYear: item.financialYear || item.fiscal_period || 'FY2024',
          fiscal_period: item.financialYear || item.fiscal_period || 'FY2024',
          storage_url: item.storageUrl || item.storage_url || '',
          storageUrl: item.storageUrl || item.storage_url || '',
          filingType: '10-K',
          ticker: (item.companyName || name).substring(0, 4).toUpperCase(),
        };
      });
    } catch (e) {
      console.warn('Could not fetch live documents from backend:', e);
      return [];
    }
  },

  async deleteDocument(documentId: string): Promise<boolean> {
    try {
      await apiClient.delete(`/documents/${documentId}`);
      return true;
    } catch (e) {
      console.warn('Failed to delete document from backend:', e);
      return false;
    }
  },
};
