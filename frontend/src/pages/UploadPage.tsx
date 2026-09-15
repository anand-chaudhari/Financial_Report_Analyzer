import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import { formatBytes } from '../utils/formatters';
import { useReportContext } from '../context/ReportContext';
import { ReportItem } from '../types/report';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { uploadReport, fetchReports } = useReportContext();

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadedResult, setUploadedResult] = useState<ReportItem | null>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    setErrorMessage(null);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
        setSelectedFile(file);
      } else {
        setErrorMessage('Only PDF documents (.pdf) are supported.');
      }
    }
  };

  const handleFileSelect = (file: File) => {
    setErrorMessage(null);
    if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
      setSelectedFile(file);
    } else {
      setErrorMessage('Only PDF documents (.pdf) are supported.');
    }
  };

  const handleStartProcess = async () => {
    if (!selectedFile || uploading) return;
    setUploading(true);
    setErrorMessage(null);

    try {
      const result = await uploadReport(selectedFile);
      setUploadedResult(result);
      setUploading(false);
      await fetchReports();
      setTimeout(() => {
        navigate('/reports');
      }, 1500);
    } catch (err: any) {
      setUploading(false);
      await fetchReports();
      const serverMsg = err?.response?.data?.detail || err?.message || 'Failed to initialize document upload. Please verify file and try again.';
      setErrorMessage(serverMsg);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto animate-fade-in w-full pb-10">
      <div className="flex items-center gap-3 pb-2">
        <button
          onClick={() => navigate('/dashboard')}
          className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Upload Financial Filing
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Upload any corporate 10-K, 10-Q, 8-K, or annual earnings report PDF (up to 200MB)
          </p>
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-bold">Upload Error</p>
            <p>{errorMessage}</p>
          </div>
          <button
            onClick={() => {
              setErrorMessage(null);
              setUploading(false);
            }}
            className="p-1.5 hover:bg-rose-500/20 rounded-lg text-rose-600 dark:text-rose-400 transition-colors"
            title="Dismiss error"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      )}

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`p-8 sm:p-10 rounded-3xl border-2 border-dashed text-center transition-all ${
          dragActive
            ? 'border-emerald-500 bg-emerald-500/10'
            : 'border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900'
        }`}
      >
        {uploading ? (
          <div className="py-8 space-y-4 max-w-xl mx-auto text-center">
            <div className="relative w-14 h-14 mx-auto flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin" />
              <Loader2 className="w-6 h-6 text-emerald-500 animate-spin" />
            </div>
            <h3 className="text-base font-extrabold text-slate-900 dark:text-white">
              Uploading Filing to Storage...
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
              {selectedFile?.name} ({selectedFile ? formatBytes(selectedFile.size) : ''})
            </p>
            <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
              Background worker starting local extraction & indexing. You can safely navigate to other pages anytime.
            </p>
          </div>
        ) : uploadedResult ? (
          <div className="py-8 space-y-4 text-emerald-600 dark:text-emerald-400 max-w-md mx-auto">
            <CheckCircle2 className="w-14 h-14 mx-auto" />
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Upload Successful!
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Local background worker is now processing and vector indexing your report.
            </p>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 text-xs space-y-2 text-left">
              <div className="flex justify-between">
                <span className="text-slate-500">Document ID:</span>
                <span className="font-mono font-bold">{uploadedResult.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Company:</span>
                <span className="font-bold">{uploadedResult.companyName || uploadedResult.company_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">Processing in Background</span>
              </div>
            </div>

            <p className="text-xs text-slate-500">Navigating to your reports library...</p>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto">
              <UploadCloud className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Drag and drop your PDF report here
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Supports PDF up to 200MB with automated non-blocking statement parsing
              </p>
            </div>

            {selectedFile && (
              <div className="p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between text-xs max-w-md mx-auto text-left">
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <FileText className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  <span className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                    {selectedFile.name}
                  </span>
                  <span className="text-slate-400 text-[10px]">({formatBytes(selectedFile.size)})</span>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-slate-400 hover:text-rose-500 text-xs font-bold px-2 cursor-pointer"
                >
                  ✕
                </button>
              </div>
            )}

            <div className="pt-2 flex justify-center">
              {!selectedFile ? (
                <label className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-500/20 cursor-pointer transition-all flex items-center gap-2">
                  <UploadCloud className="w-4 h-4" />
                  <span>Choose PDF & Upload Report</span>
                  <input
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileSelect(e.target.files[0]);
                      }
                    }}
                  />
                </label>
              ) : (
                <button
                  onClick={handleStartProcess}
                  className="px-8 py-3 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-500/20 transition-all cursor-pointer flex items-center gap-2"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload & Start Background AI Indexing</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadPage;
