import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  RotateCcw,
  Sparkles,
  Clock,
  Bot,
  BarChart3,
  Layers,
  Cpu,
  Database,
  Check,
  ArrowRight,
  ShieldCheck,
  FileSpreadsheet,
} from 'lucide-react';
import { formatBytes } from '../utils/formatters';
import { useReportContext } from '../context/ReportContext';
import { documentService } from '../services/documentService';
import { ReportItem } from '../types/report';

interface PipelineStep {
  id: string;
  label: string;
  desc: string;
  icon: React.ElementType;
  minPercent: number;
}

const PIPELINE_STEPS: PipelineStep[] = [
  {
    id: 'upload',
    label: 'Upload Stream',
    desc: 'Streaming file bytes to local storage',
    icon: UploadCloud,
    minPercent: 0,
  },
  {
    id: 'analyze',
    label: 'Analysis & Pages',
    desc: 'Magic byte check, metadata, page detection',
    icon: Layers,
    minPercent: 15,
  },
  {
    id: 'extract',
    label: 'Table & Text Extract',
    desc: 'Extracting tables, statements & footnotes',
    icon: FileText,
    minPercent: 40,
  },
  {
    id: 'embed',
    label: 'Neural Embeddings',
    desc: 'Generating high-dimensional vector embeddings',
    icon: Cpu,
    minPercent: 75,
  },
  {
    id: 'index',
    label: 'Vector Indexing',
    desc: 'ChromaDB persistent vector indexation',
    icon: Database,
    minPercent: 90,
  },
];

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { uploadReport, fetchReports } = useReportContext();

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Real-time progress states
  const [uploadProgress, setUploadProgress] = useState(0); // 0-100% of network
  const [pipelineProgress, setPipelineProgress] = useState(0); // 0-100% of pipeline
  const [currentStageName, setCurrentStageName] = useState('Uploading');
  const [stageDetailMessage, setStageDetailMessage] = useState('Initiating streaming upload...');
  const [processedResult, setProcessedResult] = useState<ReportItem | null>(null);

  // Time & ETA tracking
  const startTimeRef = useRef<number | null>(null);
  const [etaRemaining, setEtaRemaining] = useState<string>('Estimating time...');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const SUPPORTED_EXTENSIONS = ['.pdf', '.csv', '.tsv', '.docx', '.docm', '.xlsx', '.xls', '.xlsm', '.txt', '.md', '.json'];
  const isSupportedFile = (file: File) => {
    const name = file.name.toLowerCase();
    return SUPPORTED_EXTENSIONS.some((ext) => name.endsWith(ext));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    setErrorMessage(null);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (isSupportedFile(file)) {
        setSelectedFile(file);
      } else {
        setErrorMessage('Supported formats: PDF (.pdf), CSV (.csv), Word (.docx), Excel (.xlsx/.xls), and Text (.txt).');
      }
    }
  };

  const handleFileSelect = (file: File) => {
    setErrorMessage(null);
    if (isSupportedFile(file)) {
      setSelectedFile(file);
    } else {
      setErrorMessage('Supported formats: PDF (.pdf), CSV (.csv), Word (.docx), Excel (.xlsx/.xls), and Text (.txt).');
    }
  };

  // Timer for elapsed seconds and ETA computation
  useEffect(() => {
    if (isProcessing && !timerRef.current) {
      startTimeRef.current = Date.now();
      timerRef.current = setInterval(() => {
        if (!startTimeRef.current) return;
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setElapsedSeconds(elapsed);
      }, 500);
    }

    if (!isProcessing && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isProcessing]);

  // Overall effective percentage
  const effectivePercentage = Math.min(
    100,
    Math.max(
      processedResult?.status === 'completed' ? 100 : 0,
      uploadProgress < 100
        ? Math.round(uploadProgress * 0.2) // Upload byte transfer is first 20%
        : 20 + Math.round(pipelineProgress * 0.8) // Server pipeline is remaining 80%
    )
  );

  // Dynamic ETA update whenever effectivePercentage or elapsedSeconds changes
  useEffect(() => {
    if (!isProcessing || effectivePercentage >= 100) {
      if (effectivePercentage >= 100) {
        setEtaRemaining('Complete!');
      }
      return;
    }

    if (effectivePercentage < 5 || elapsedSeconds < 2) {
      setEtaRemaining('Estimating time remaining...');
      return;
    }

    // Dynamic linear estimation with damping
    const totalEstimatedSec = (elapsedSeconds / effectivePercentage) * 100;
    const remainingSec = Math.max(1, Math.round(totalEstimatedSec - elapsedSeconds));

    if (remainingSec <= 2) {
      setEtaRemaining('Finalizing index...');
    } else if (remainingSec < 60) {
      setEtaRemaining(`~${remainingSec}s remaining`);
    } else {
      const mins = Math.floor(remainingSec / 60);
      const secs = remainingSec % 60;
      setEtaRemaining(`~${mins}m ${secs}s remaining`);
    }
  }, [isProcessing, effectivePercentage, elapsedSeconds]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);

  const handleStartProcess = async () => {
    if (!selectedFile || isProcessing) return;
    setIsProcessing(true);
    setErrorMessage(null);
    setProcessedResult(null);
    setUploadProgress(0);
    setPipelineProgress(5);
    setCurrentStageName('Uploading');
    setStageDetailMessage(`Streaming ${selectedFile.name} (${formatBytes(selectedFile.size)}) to server...`);
    startTimeRef.current = Date.now();
    setElapsedSeconds(0);

    try {
      // 1. Stream file with Axios byte progress
      const result = await uploadReport(selectedFile, (pct: number) => {
        setUploadProgress(pct);
        if (pct >= 100) {
          setCurrentStageName('Analyzing');
          setStageDetailMessage('File uploaded. Starting background AI parsing & extraction...');
        }
      });

      setProcessedResult(result);
      const docId: string = result.id || result.documentId || '';
      if (!docId) {
        setIsProcessing(false);
        return;
      }

      // Check if document was instantly resolved from verified vector cache
      if (result.status === 'completed' || result.currentStage === 'Ready' || result.progressPercent === 100) {
        setPipelineProgress(100);
        setCurrentStageName('Ready');
        setStageDetailMessage(result.stageMessage || 'Document loaded instantly from verified cache.');
        setIsProcessing(false);
        await fetchReports();
        return;
      }

      // 2. Poll document status every 1000ms until complete
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }

      pollIntervalRef.current = setInterval(async () => {
        const liveStatus = await documentService.getDocumentStatus(docId);
        if (liveStatus) {
          const pct = liveStatus.progressPercent !== undefined ? liveStatus.progressPercent : 50;
          setPipelineProgress(pct);
          if (liveStatus.currentStage) setCurrentStageName(liveStatus.currentStage);
          if (liveStatus.stageMessage) setStageDetailMessage(liveStatus.stageMessage);

          if (liveStatus.status === 'completed' || pct >= 100 || liveStatus.currentStage === 'Ready') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setPipelineProgress(100);
            setCurrentStageName('Ready');
            setStageDetailMessage('Processing and vector indexing complete!');
            setProcessedResult((prev) => (prev ? { ...prev, ...liveStatus, status: 'completed' } : liveStatus));
            setIsProcessing(false);
            await fetchReports();
          } else if (liveStatus.status === 'failed') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setIsProcessing(false);
            setErrorMessage(liveStatus.errorMessage || 'Background document processing failed.');
            await fetchReports();
          }
        }
      }, 1500);
    } catch (err: any) {
      setIsProcessing(false);
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      await fetchReports();
      const serverMsg =
        err?.response?.data?.message ||
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to initialize document upload. Please verify file and try again.';
      setErrorMessage(serverMsg);
    }
  };

  const handleReset = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsProcessing(false);
    setSelectedFile(null);
    setProcessedResult(null);
    setUploadProgress(0);
    setPipelineProgress(0);
    setErrorMessage(null);
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto animate-fade-in w-full pb-12">
      {/* Top Header */}
      <div className="flex items-center gap-3 pb-2">
        <button
          onClick={() => navigate('/dashboard')}
          className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer shadow-xs"
          title="Back to Dashboard"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Upload Financial Filing
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Automated layout extraction, OCR, vector embedding, and ChromaDB indexing
          </p>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/25 text-rose-600 dark:text-rose-400 text-xs flex items-start gap-3 animate-fade-in">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-bold">Upload / Processing Error</p>
            <p>{errorMessage}</p>
          </div>
          <button
            onClick={() => {
              setErrorMessage(null);
              setIsProcessing(false);
            }}
            className="p-1.5 hover:bg-rose-500/20 rounded-lg text-rose-600 dark:text-rose-400 transition-colors cursor-pointer"
            title="Dismiss error"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Upload / Processing Card */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm transition-all">
        {/* State A: In-Progress Realtime Loading Bar */}
        {isProcessing ? (
          <div className="space-y-6 py-2 animate-fade-in">
            {/* Header info */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate max-w-xs sm:max-w-md">
                    {selectedFile?.name}
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                    {selectedFile ? formatBytes(selectedFile.size) : ''} • Elapsed: {elapsedSeconds}s
                  </p>
                </div>
              </div>

              {/* ETA Pill */}
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-300 text-xs font-semibold self-start sm:self-auto">
                <Clock className="w-3.5 h-3.5 animate-pulse text-emerald-500" />
                <span>{etaRemaining}</span>
              </div>
            </div>

            {/* REALTIME LOADING BAR */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-bold">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
                  <span className="text-slate-900 dark:text-slate-100 uppercase tracking-wider font-extrabold text-[11px]">
                    {currentStageName} Stage
                  </span>
                </div>
                <span className="font-mono text-base font-extrabold text-emerald-600 dark:text-emerald-400">
                  {effectivePercentage}%
                </span>
              </div>

              {/* Progress Track */}
              <div className="w-full h-4 sm:h-5 bg-slate-100 dark:bg-slate-800 rounded-full p-1 shadow-inner relative overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-500 transition-all duration-300 ease-out relative overflow-hidden shadow-md shadow-emerald-500/30"
                  style={{ width: `${Math.max(3, effectivePercentage)}%` }}
                >
                  {/* Realtime Shimmer animation */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer" />
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-0.5">
                <span className="truncate pr-2 font-medium">
                  {stageDetailMessage}
                </span>
                <span className="flex-shrink-0 font-mono font-semibold">
                  {effectivePercentage}/100%
                </span>
              </div>
            </div>

            {/* Pipeline Stage Stepper */}
            <div className="pt-2">
              <p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">
                Pipeline Stages
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
                {PIPELINE_STEPS.map((step) => {
                  const isDone = effectivePercentage > step.minPercent + 15 || effectivePercentage === 100;
                  const isCurrent = effectivePercentage >= step.minPercent && !isDone;
                  const Icon = step.icon;

                  return (
                    <div
                      key={step.id}
                      className={`p-3 rounded-2xl border transition-all text-left flex flex-col justify-between ${
                        isDone
                          ? 'bg-emerald-500/5 dark:bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400'
                          : isCurrent
                          ? 'bg-teal-500/10 dark:bg-teal-500/15 border-teal-500/40 text-teal-700 dark:text-teal-300 ring-2 ring-teal-500/20'
                          : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-400'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <Icon className="w-4 h-4 flex-shrink-0" />
                        {isDone ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : isCurrent ? (
                          <span className="w-2 h-2 rounded-full bg-teal-500 animate-ping" />
                        ) : (
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-300 dark:bg-slate-700" />
                        )}
                      </div>
                      <div>
                        <p className="text-xs font-bold leading-tight truncate">{step.label}</p>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                          {step.minPercent}%
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Non-blocking background worker reminder */}
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="space-y-0.5">
                <p className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  <span>Non-Blocking Asynchronous Processing</span>
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  You can safely browse other sections. Processing continues seamlessly in the background.
                </p>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white font-semibold text-xs cursor-pointer transition-colors"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => navigate('/reports')}
                  className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs cursor-pointer transition-colors shadow-sm"
                >
                  Reports Library
                </button>
              </div>
            </div>
          </div>
        ) : processedResult && processedResult.status === 'completed' ? (
          /* State B: Success Complete View */
          <div className="py-6 space-y-6 text-center animate-fade-in">
            <div className="w-16 h-16 rounded-3xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/10">
              <CheckCircle2 className="w-9 h-9" />
            </div>

            <div className="space-y-1">
              <h3 className="text-xl font-extrabold text-slate-900 dark:text-white">
                Filing Processed & 100% Indexed!
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Financial tables, MD&A statements, and vector embeddings are ready for grounded RAG analysis.
              </p>
            </div>

            {/* Document summary box */}
            <div className="max-w-md mx-auto p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs space-y-2.5 text-left">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Company Name:</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {processedResult.companyName || processedResult.company_name || 'Corporate Filing'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Document ID:</span>
                <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                  {processedResult.id || processedResult.documentId}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Filing Period / Pages:</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {processedResult.financialYear || 'FY2026'} • {processedResult.pageCount || processedResult.total_pages || 1} pages
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Status:</span>
                <span className="inline-flex items-center gap-1 font-bold text-emerald-600 dark:text-emerald-400">
                  <Check className="w-3.5 h-3.5" /> Ready for AI Analysis
                </span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                onClick={() => navigate(`/analyst?reportId=${processedResult.id || processedResult.documentId}`)}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 flex items-center gap-2 cursor-pointer transition-all"
              >
                <Bot className="w-4 h-4" />
                <span>Ask AI Analyst</span>
              </button>

              <button
                onClick={() => navigate(`/reports/${processedResult.id || processedResult.documentId}/summary`)}
                className="px-5 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold text-xs flex items-center gap-2 cursor-pointer transition-colors"
              >
                <Sparkles className="w-4 h-4 text-emerald-500" />
                <span>Executive Summary</span>
              </button>

              <button
                onClick={() => navigate('/dashboard')}
                className="px-5 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold text-xs cursor-pointer transition-colors"
              >
                Dashboard
              </button>

              <button
                onClick={handleReset}
                className="px-4 py-2.5 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-white font-semibold text-xs cursor-pointer transition-colors"
              >
                Upload Another
              </button>
            </div>
          </div>
        ) : (
          /* State C: Drag and Drop Selection View */
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            className={`p-8 sm:p-10 rounded-2xl border-2 border-dashed text-center transition-all ${
              dragActive
                ? 'border-emerald-500 bg-emerald-500/10'
                : 'border-slate-300 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40'
            }`}
          >
            <div className="space-y-5">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto shadow-sm">
                <UploadCloud className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Drag and drop your financial filing here
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                  Supports PDF (.pdf), CSV (.csv), Excel (.xlsx/.xls), Word (.docx) up to 250MB with automated streaming
                </p>
              </div>

              {selectedFile && (
                <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between text-xs max-w-md mx-auto text-left shadow-xs">
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <FileText className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    <span className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                      {selectedFile.name}
                    </span>
                    <span className="text-slate-400 text-[10px] flex-shrink-0">
                      ({formatBytes(selectedFile.size)})
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="text-slate-400 hover:text-rose-500 text-xs font-bold px-2 cursor-pointer transition-colors"
                  >
                    ✕
                  </button>
                </div>
              )}

              <div className="pt-2 flex justify-center">
                {!selectedFile ? (
                  <label className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-500/20 cursor-pointer transition-all flex items-center gap-2">
                    <UploadCloud className="w-4 h-4" />
                    <span>Choose File to Upload</span>
                    <input
                      type="file"
                      accept=".pdf,.csv,.tsv,.docx,.docm,.xlsx,.xls,.xlsm,.txt,.md,.json"
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
                    <span>Upload & Start Realtime AI Indexing</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Feature highlight footer cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs space-y-1 shadow-xs">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold">
            <Cpu className="w-4 h-4" />
            <span>Local RAG Processing</span>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-[11px]">
            Embeddings and parsing execute on local worker threads without external storage leaks.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs space-y-1 shadow-xs">
          <div className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400 font-bold">
            <FileSpreadsheet className="w-4 h-4" />
            <span>Multi-Format Parsing</span>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-[11px]">
            Handles 10-K PDFs, Excel balance sheets, Word reports, and raw CSV ledger files up to 250MB.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs space-y-1 shadow-xs">
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-bold">
            <Bot className="w-4 h-4" />
            <span>Grounded Citations</span>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-[11px]">
            Every metric and answer from the AI analyst is linked to exact page and section citations.
          </p>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
