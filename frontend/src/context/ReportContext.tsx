import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { ReportItem } from '../types/report';
import { documentService } from '../services/documentService';

interface ReportContextType {
  reports: ReportItem[];
  activeReport: ReportItem | null;
  loading: boolean;
  error: string | null;
  fetchReports: () => Promise<void>;
  uploadReport: (file: File) => Promise<ReportItem>;
  setActiveReport: (report: ReportItem | null) => void;
  deleteReport: (reportId: string) => Promise<void>;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

export const ReportProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [activeReport, setActiveReport] = useState<ReportItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const liveDocs = await documentService.getDocuments();
      setReports(liveDocs);
      if (liveDocs.length > 0 && !activeReport) {
        setActiveReport(liveDocs[0]);
      }
    } catch (err: any) {
      console.warn('Error loading reports context:', err);
      setError(err?.message || 'Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadReport = async (file: File): Promise<ReportItem> => {
    setLoading(true);
    setError(null);
    try {
      const newReport = await documentService.uploadDocument(file);
      setReports((prev) => [newReport, ...prev.filter((r) => r.id !== newReport.id)]);
      setActiveReport(newReport);
      return newReport;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to upload PDF report';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const deleteReport = async (reportId: string) => {
    try {
      await documentService.deleteDocument(reportId);
      setReports((prev) => prev.filter((r) => r.id !== reportId && r.documentId !== reportId));
      if (activeReport?.id === reportId || activeReport?.documentId === reportId) {
        setActiveReport(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to delete report');
    }
  };

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  return (
    <ReportContext.Provider
      value={{
        reports,
        activeReport,
        loading,
        error,
        fetchReports,
        uploadReport,
        setActiveReport,
        deleteReport,
      }}
    >
      {children}
    </ReportContext.Provider>
  );
};

export const useReportContext = (): ReportContextType => {
  const context = useContext(ReportContext);
  if (!context) {
    throw new Error('useReportContext must be used within a ReportProvider');
  }
  return context;
};
