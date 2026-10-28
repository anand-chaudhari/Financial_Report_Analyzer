import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { ReportItem } from '../types/report';
import { documentService } from '../services/documentService';
import { financialService } from '../services/financialService';
import { useAuthContext } from './AuthContext';

interface ReportContextType {
  reports: ReportItem[];
  activeReport: ReportItem | null;
  loading: boolean;
  error: string | null;
  activeProcessingReport: ReportItem | null;
  fetchReports: () => Promise<void>;
  uploadReport: (file: File, onProgress?: (pct: number) => void) => Promise<ReportItem>;
  setActiveReport: (report: ReportItem | null) => void;
  deleteReport: (reportId: string) => Promise<void>;
  renameReport: (reportId: string, newName: string) => Promise<void>;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

const getInitialDeletedReportIds = (): Set<string> => {
  try {
    const raw = sessionStorage.getItem('finsight_deleted_reports');
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) {
        return new Set(arr);
      }
    }
  } catch {
    // ignore
  }
  return new Set<string>();
};

const saveDeletedReportIds = (ids: Set<string>) => {
  try {
    sessionStorage.setItem('finsight_deleted_reports', JSON.stringify(Array.from(ids)));
  } catch {
    // ignore
  }
};

const deduplicateReports = (items: ReportItem[], deletedIds: Set<string>): ReportItem[] => {
  const result: ReportItem[] = [];
  const seenIds = new Set<string>();
  const seenFileKeys = new Set<string>();

  for (const item of items) {
    const id = item.id || item.documentId;
    if (!id || deletedIds.has(id)) {
      continue;
    }
    if (seenIds.has(id)) {
      continue;
    }
    seenIds.add(id);

    // Dedup by fileName + fileSize (if non-zero)
    const fileName = item.fileName || item.filename || '';
    const fileSize = item.fileSize || item.file_size || 0;
    if (fileName && fileSize > 0) {
      const key = `${fileName}_${fileSize}`;
      if (seenFileKeys.has(key)) {
        continue;
      }
      seenFileKeys.add(key);
    }

    result.push(item);
  }

  return result;
};

export const ReportProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading: authLoading } = useAuthContext();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [activeReport, setActiveReport] = useState<ReportItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const deletedReportIdsRef = useRef<Set<string>>(getInitialDeletedReportIds());

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const liveDocs = await documentService.getDocuments();
      const cleanDocs = deduplicateReports(liveDocs, deletedReportIdsRef.current);
      setReports(cleanDocs);
      if (cleanDocs.length > 0 && (!activeReport || deletedReportIdsRef.current.has(activeReport.id || activeReport.documentId || ''))) {
        setActiveReport(cleanDocs[0]);
      } else if (cleanDocs.length === 0) {
        setActiveReport(null);
      }
    } catch (err: any) {
      console.warn('Error loading reports context:', err);
      setError(err?.message || 'Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  }, [activeReport]);

  const activeProcessingReport = reports.find(
    (r) =>
      (r.status === 'processing' || r.status === 'uploaded') &&
      !deletedReportIdsRef.current.has(r.id || r.documentId || '')
  ) || null;

  // Background polling loop for documents currently being processed
  useEffect(() => {
    const processingDoc = reports.find(
      (r) =>
        (r.status === 'processing' || r.status === 'uploaded') &&
        !deletedReportIdsRef.current.has(r.id || r.documentId || '')
    );

    if (!processingDoc) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    const pollDocId = processingDoc.id || processingDoc.documentId;
    if (!pollDocId || deletedReportIdsRef.current.has(pollDocId)) return;

    if (!pollingTimerRef.current) {
      pollingTimerRef.current = setInterval(async () => {
        if (deletedReportIdsRef.current.has(pollDocId)) {
          if (pollingTimerRef.current) {
            clearInterval(pollingTimerRef.current);
            pollingTimerRef.current = null;
          }
          return;
        }

        const updatedStatus = await documentService.getDocumentStatus(pollDocId);
        if (!updatedStatus) {
          // Document was deleted or not found: stop polling
          if (pollingTimerRef.current) {
            clearInterval(pollingTimerRef.current);
            pollingTimerRef.current = null;
          }
          return;
        }

        setReports((prev) => {
          const currentItem = prev.find((r) => r.id === pollDocId || r.documentId === pollDocId);
          if (!currentItem || deletedReportIdsRef.current.has(pollDocId)) return prev;

          const newStatus = updatedStatus.status || currentItem.status;
          const newStage = updatedStatus.currentStage || currentItem.currentStage;
          const newMsg = updatedStatus.stageMessage !== undefined ? updatedStatus.stageMessage : currentItem.stageMessage;
          const newPct = updatedStatus.progressPercent !== undefined ? updatedStatus.progressPercent : currentItem.progressPercent;
          const newPages = updatedStatus.pageCount || currentItem.pageCount;
          const newComp = updatedStatus.companyName || currentItem.companyName;

          // Strict equality check: prevent re-rendering when polling returns identical values
          if (
            currentItem.status === newStatus &&
            currentItem.currentStage === newStage &&
            currentItem.stageMessage === newMsg &&
            currentItem.progressPercent === newPct &&
            currentItem.pageCount === newPages &&
            currentItem.companyName === newComp
          ) {
            return prev;
          }

          return prev.map((r) => {
            if (r.id === pollDocId || r.documentId === pollDocId) {
              return {
                ...r,
                status: newStatus,
                currentStage: newStage,
                stageMessage: newMsg,
                progressPercent: newPct,
                pageCount: newPages,
                companyName: newComp,
                company_name: newComp,
                financialYear: updatedStatus.financialYear || r.financialYear,
              };
            }
            return r;
          });
        });

        if (updatedStatus.status === 'completed' || updatedStatus.status === 'failed' || updatedStatus.status === 'ready') {
          if (pollingTimerRef.current) {
            clearInterval(pollingTimerRef.current);
            pollingTimerRef.current = null;
          }
          fetchReports();
        }
      }, 1500);
    }

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [reports, fetchReports]);

  const uploadReport = async (file: File, onProgress?: (pct: number) => void): Promise<ReportItem> => {
    setError(null);
    try {
      const newReport = await documentService.uploadDocument(file, onProgress);
      const newId = newReport.id || newReport.documentId;
      if (newId && deletedReportIdsRef.current.has(newId)) {
        deletedReportIdsRef.current.delete(newId);
        saveDeletedReportIds(deletedReportIdsRef.current);
      }
      setReports((prev) => {
        const withoutNew = prev.filter((r) => r.id !== newId && r.documentId !== newId);
        return deduplicateReports([newReport, ...withoutNew], deletedReportIdsRef.current);
      });
      setActiveReport(newReport);
      return newReport;
    } catch (err: any) {
      const msg =
        err?.response?.data?.message ||
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to upload PDF report';
      setError(msg);
      throw new Error(msg);
    }
  };

  const deleteReport = async (reportId: string): Promise<void> => {
    try {
      setError(null);
      // Immediately record as deleted in memory and storage so polling/re-fetch can NEVER resurrect it
      deletedReportIdsRef.current.add(reportId);
      saveDeletedReportIds(deletedReportIdsRef.current);

      // Stop active polling if this was the document being polled
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }

      // Immediately remove from state
      setReports((prev) => prev.filter((r) => r.id !== reportId && r.documentId !== reportId));
      if (activeReport?.id === reportId || activeReport?.documentId === reportId) {
        setActiveReport(null);
      }

      // Clear client-side financial cached data for this report
      financialService.clearCache(reportId);

      // Call backend delete
      const ok = await documentService.deleteDocument(reportId);
      if (!ok) {
        console.warn(`Backend delete returned false for ${reportId}`);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to delete report';
      setError(msg);
      throw new Error(msg);
    }
  };

  const renameReport = async (reportId: string, newName: string): Promise<void> => {
    try {
      setError(null);
      const ok = await documentService.renameDocument(reportId, newName);
      if (!ok) {
        throw new Error('Failed to rename report.');
      }
      setReports((prev) =>
        prev.map((r) => {
          if (r.id === reportId || r.documentId === reportId) {
            const clean = newName.trim();
            const isPdf = clean.toLowerCase().endsWith('.pdf');
            const compName = isPdf ? clean.slice(0, -4).replace(/_/g, ' ') : clean;
            return {
              ...r,
              companyName: compName,
              company_name: compName,
              fileName: isPdf ? clean : r.fileName,
              filename: isPdf ? clean : r.filename,
              ticker: compName.substring(0, 4).toUpperCase(),
            };
          }
          return r;
        })
      );
      if (activeReport && (activeReport.id === reportId || activeReport.documentId === reportId)) {
        const clean = newName.trim();
        const isPdf = clean.toLowerCase().endsWith('.pdf');
        const compName = isPdf ? clean.slice(0, -4).replace(/_/g, ' ') : clean;
        setActiveReport({
          ...activeReport,
          companyName: compName,
          company_name: compName,
          fileName: isPdf ? clean : activeReport.fileName,
          filename: isPdf ? clean : activeReport.filename,
          ticker: compName.substring(0, 4).toUpperCase(),
        });
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to rename report';
      setError(msg);
      throw new Error(msg);
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
        renameReport,
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
