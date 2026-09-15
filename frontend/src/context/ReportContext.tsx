import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { ReportItem } from '../types/report';
import { documentService } from '../services/documentService';
import { useAuthContext } from './AuthContext';

interface ReportContextType {
  reports: ReportItem[];
  activeReport: ReportItem | null;
  loading: boolean;
  error: string | null;
  activeProcessingReport: ReportItem | null;
  fetchReports: () => Promise<void>;
  uploadReport: (file: File) => Promise<ReportItem>;
  setActiveReport: (report: ReportItem | null) => void;
  deleteReport: (reportId: string) => Promise<void>;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

export const ReportProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading: authLoading } = useAuthContext();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [activeReport, setActiveReport] = useState<ReportItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);

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
  }, [activeReport]);

  const activeProcessingReport = reports.find((r) => r.status === 'processing' || r.status === 'uploaded') || null;

  // Background polling loop for documents currently being processed
  useEffect(() => {
    const processingDoc = reports.find((r) => r.status === 'processing' || r.status === 'uploaded');

    if (!processingDoc) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    const pollDocId = processingDoc.id || processingDoc.documentId;
    if (!pollDocId) return;

    if (!pollingTimerRef.current) {
      pollingTimerRef.current = setInterval(async () => {
        const updatedStatus = await documentService.getDocumentStatus(pollDocId);
        if (updatedStatus) {
          setReports((prev) =>
            prev.map((r) => {
              if (r.id === pollDocId || r.documentId === pollDocId) {
                return {
                  ...r,
                  status: updatedStatus.status || r.status,
                  currentStage: updatedStatus.currentStage || r.currentStage,
                  stageMessage: updatedStatus.stageMessage || r.stageMessage,
                  progressPercent: updatedStatus.progressPercent !== undefined ? updatedStatus.progressPercent : r.progressPercent,
                  pageCount: updatedStatus.pageCount || r.pageCount,
                  companyName: updatedStatus.companyName || r.companyName,
                  company_name: updatedStatus.companyName || r.company_name,
                  financialYear: updatedStatus.financialYear || r.financialYear,
                };
              }
              return r;
            })
          );

          if (updatedStatus.status === 'completed' || updatedStatus.status === 'failed' || updatedStatus.status === 'ready') {
            if (pollingTimerRef.current) {
              clearInterval(pollingTimerRef.current);
              pollingTimerRef.current = null;
            }
            fetchReports();
          }
        }
      }, 3000);
    }

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [reports, fetchReports]);

  const uploadReport = async (file: File): Promise<ReportItem> => {
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
    if (!authLoading && user) {
      fetchReports();
    } else if (!authLoading && !user) {
      setReports([]);
      setActiveReport(null);
    }
  }, [authLoading, user, fetchReports]);

  return (
    <ReportContext.Provider
      value={{
        reports,
        activeReport,
        loading,
        error,
        activeProcessingReport,
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
