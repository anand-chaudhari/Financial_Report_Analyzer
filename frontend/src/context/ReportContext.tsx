import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { ReportItem } from '../types';
import { reportService } from '../services/reportService';

interface ReportContextType {
  reports: ReportItem[];
  activeReport: ReportItem | null;
  loading: boolean;
  error: string | null;
  fetchReports: () => Promise<void>;
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
      const response = await reportService.listReports();
      if (response.success && response.data) {
        setReports(response.data);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteReport = async (reportId: string) => {
    try {
      await reportService.deleteReport(reportId);
      setReports((prev) => prev.filter((r) => r.id !== reportId));
      if (activeReport?.id === reportId) {
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
