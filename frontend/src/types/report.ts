export type ReportStatus = 'uploaded' | 'processing' | 'completed' | 'ready' | 'failed';

export interface ReportItem {
  id: string;
  documentId?: string;
  filename: string;
  fileName?: string;
  file_size: number;
  fileSize?: number;
  total_pages: number;
  pageCount?: number;
  status: ReportStatus;
  uploaded_at: string;
  uploadedAt?: string;
  processedAt?: string;
  company_name?: string;
  companyName?: string;
  fiscal_period?: string;
  financialYear?: string;
  storage_url?: string;
  storageUrl?: string;
  ticker?: string;
  filingType?: string;
  revenue?: string;
  growth?: string;
  tags?: string[];
}

export interface ReportDetail extends ReportItem {
  user_id?: string;
  userId?: string;
  executive_summary?: string;
  error_message?: string;
  errorMessage?: string;
}

export interface ReportUploadResponse {
  documentId?: string;
  report_id?: string;
  fileName?: string;
  filename?: string;
  companyName?: string;
  financialYear?: string;
  pageCount?: number;
  status: string;
  storageUrl?: string;
  uploadedAt?: string;
  message?: string;
}
