import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, ArrowLeft } from 'lucide-react';
import { formatBytes } from '../utils/formatters';
import { useReportContext } from '../context/ReportContext';
import { ReportItem } from '../types/report';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { uploadReport } = useReportContext();

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

  const handleStartProcess = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setErrorMessage(null);

    try {
      const result = await uploadReport(selectedFile);
      setUploadedResult(result);
      setUploading(false);
      setTimeout(() => {
        navigate('/reports');
      }, 2000);
    } catch (err: any) {
      setUploading(false);
      setErrorMessage(err?.message || 'Failed to upload and process PDF file. Please try again.');
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto animate-fade-in w-full">
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
            Upload any corporate 10-K, 10-Q, 8-K, or earnings report PDF
          </p>
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`p-10 rounded-3xl border-2 border-dashed text-center transition-all ${
          dragActive
            ? 'border-emerald-500 bg-emerald-500/10'
            : 'border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900'
        }`}
      >
        {uploading ? (
          <div className="py-10 space-y-4">
            <div className="w-12 h-12 border-3 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin mx-auto" />
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Processing & Chunking PDF Filing...
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Extracting text page-by-page, identifying sections, and generating vector embeddings in ChromaDB.
            </p>
          </div>
        ) : uploadedResult ? (
          <div className="py-8 space-y-4 text-emerald-600 dark:text-emerald-400 max-w-md mx-auto">
            <CheckCircle2 className="w-14 h-14 mx-auto" />
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Report Uploaded & Indexed Successfully!
            </h3>

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
                <span className="text-slate-500">Fiscal Period:</span>
                <span className="font-bold">{uploadedResult.financialYear || uploadedResult.fiscal_period}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Total Pages:</span>
                <span className="font-bold">{uploadedResult.pageCount || uploadedResult.total_pages} pages</span>
              </div>
            </div>

            <p className="text-xs text-slate-500">Redirecting to your reports library...</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto">
              <UploadCloud className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Drag and drop your PDF report here
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Supports PDF up to 25MB with page-by-page extraction
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

            <div className="pt-2 flex items-center justify-center gap-3">
              <label className="px-5 py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold text-xs rounded-xl cursor-pointer transition-colors">
                <span>Browse Files</span>
                <input
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSelectedFile(e.target.files[0]);
                    }
                  }}
                />
              </label>

              {selectedFile && (
                <button
                  onClick={handleStartProcess}
                  className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer"
                >
                  Start AI Indexing
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
