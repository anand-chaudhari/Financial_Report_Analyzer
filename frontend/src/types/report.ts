export type ReportStatus = 'uploaded' | 'processing' | 'ready' | 'failed';

export interface ReportItem {
  id: string;
  filename: string;
  file_size: number;
  total_pages: number;
  status: ReportStatus;
  uploaded_at: string;
  company_name?: string;
  fiscal_period?: string;
}

export interface ReportDetail extends ReportItem {
  user_id: string;
  storage_url?: string;
  executive_summary?: string;
  error_message?: string;
}

export interface ReportUploadResponse {
  report_id: string;
  filename: string;
  status: string;
  message: string;
}
