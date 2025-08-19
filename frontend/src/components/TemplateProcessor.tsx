'use client';

import { useState, useRef, useEffect } from 'react';
import { templateApi, csvApi, ApiError } from '@/lib/api';
import { API_BASE_URL } from '@/config/api';
import { useAuth } from '@/contexts/AuthContext';
import { FileHistoryItem } from './FileHistory';

interface TemplateAnalysis {
  device_id: string;
  template_filename: string;
  total_fields: number;
  fillable_fields: number;
  field_analysis: Record<string, {
    can_fill: boolean;
    confidence: number;
    sources: number;
  }>;
}

interface CSVAnalysis {
  device_id: string;
  csv_filename: string;
  total_rows: number;
  total_columns: number;
  total_empty_cells: number;
  fillable_cells: number;
  sample_analysis: Record<string, {
    can_fill: boolean;
    confidence: number;
    sources: number;
  }>;
  columns: string[];
}

interface TemplateProcessorProps {
  deviceId: string;
  onFileHistoryUpdate?: (item: FileHistoryItem) => void;
}

export default function TemplateProcessor({ deviceId, onFileHistoryUpdate }: TemplateProcessorProps) {
  const [processing, setProcessing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzingCsv, setAnalyzingCsv] = useState(false);
  const [processingCsv, setProcessingCsv] = useState(false);
  const [analysis, setAnalysis] = useState<TemplateAnalysis | null>(null);
  const [csvAnalysis, setCsvAnalysis] = useState<CSVAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [csvSuccess, setCsvSuccess] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [csvDownloadUrl, setCsvDownloadUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressStage, setProgressStage] = useState('');
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);
  // Favorites state used by fetchFavorites (restore to avoid ReferenceError)
  const [favorites, setFavorites] = useState<FileHistoryItem[]>([]);
  const [favLoading, setFavLoading] = useState(false);
  const [favError, setFavError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const processInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const csvAnalyzeInputRef = useRef<HTMLInputElement>(null);
  const activeIntervalsRef = useRef<NodeJS.Timeout[]>([]);

  // --- ADDED: modal / source selection state ---
  const [sourceModalOpen, setSourceModalOpen] = useState(false);
  const [sourceModalUseCase, setSourceModalUseCase] = useState<'analyze-template'|'process-template'|'analyze-csv'|'process-csv' | null>(null);
  const [sourceModalView, setSourceModalView] = useState<'choose'|'favorites'|'device'>('choose');

  // Backend base used to resolve API download URLs (use env or fallback)
  const BACKEND_BASE = (process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000').replace(/\/$/, '');

  // new: track favorite processing to keep modal open and disable actions while using a fav
  const [favProcessing, setFavProcessing] = useState(false);
  const [favProcessingName, setFavProcessingName] = useState<string | null>(null);

  // Progress simulation during template processing
  useEffect(() => {
    // Clear any existing intervals
    activeIntervalsRef.current.forEach(interval => clearInterval(interval));
    activeIntervalsRef.current = [];

    if (!processing) {
      setProgress(0);
      setProgressStage('');
      setEstimatedTime(0);
      setStartTime(null);
      return;
    }

    const stages = [
      { progress: 15, stage: 'Analyzing template structure...', duration: 3000 },
      { progress: 30, stage: 'Extracting placeholders...', duration: 4000 },
      { progress: 50, stage: 'Searching knowledge base...', duration: 8000 },
      { progress: 70, stage: 'Generating field content...', duration: 15000 },
      { progress: 85, stage: 'Filling template fields...', duration: 8000 },
      { progress: 92, stage: 'Finalizing document...', duration: 3000 },
    ];

    let currentStageIndex = 0;

    const updateProgress = () => {
      if (currentStageIndex >= stages.length) return;

      const currentStage = stages[currentStageIndex];
      const stageStartProgress = currentStageIndex === 0 ? 0 : stages[currentStageIndex - 1].progress;
      const stageEndProgress = currentStage.progress;
      const stageDuration = currentStage.duration;

      setProgressStage(currentStage.stage);

      const stageStartTime = Date.now();
      const stageInterval = setInterval(() => {
        const elapsed = Date.now() - stageStartTime;
        const stageProgress = Math.min(elapsed / stageDuration, 1);
        const currentProgress = stageStartProgress + (stageEndProgress - stageStartProgress) * stageProgress;
        
        setProgress(Math.min(currentProgress, 100));

        // Calculate estimated time remaining
        if (startTime) {
          const totalElapsed = Date.now() - startTime;
          const totalEstimated = totalElapsed / (currentProgress / 100);
          const remaining = Math.max(0, totalEstimated - totalElapsed);
          setEstimatedTime(Math.ceil(remaining / 1000));
        }

        if (stageProgress >= 1) {
          clearInterval(stageInterval);
          // Remove this interval from active intervals
          activeIntervalsRef.current = activeIntervalsRef.current.filter(id => id !== stageInterval);
          
          currentStageIndex++;
          if (currentStageIndex < stages.length) {
            setTimeout(updateProgress, 100);
          }
        }
      }, 100);

      // Track the active interval
      activeIntervalsRef.current.push(stageInterval);
    };

    if (startTime === null) {
      setStartTime(Date.now());
    }

    updateProgress();

    // Cleanup function
    return () => {
      activeIntervalsRef.current.forEach(interval => clearInterval(interval));
      activeIntervalsRef.current = [];
    };
  }, [processing, startTime]);

  // Helper to upload file to GCS via file-history API
  async function uploadFileToGCS(file: File, type: string, timestamp?: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);
    formData.append('timestamp', timestamp || new Date().toISOString());
    try {
      const response = await fetch('http://localhost:8000/api/favorites/', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error('GCS upload failed');
      return await response.json();
    } catch (err) {
      // Silent fail, don't block main flow
      return null;
    }
  }

  // Minimal helper to POST favorite metadata or file to backend (no local UI state here)
  async function postFavorite(formData: FormData) {
    try {
      await fetch('http://localhost:8000/api/favorites/', {
        method: 'POST',
        body: formData,
      });
    } catch (e) {
      // ignore — sidebar will reflect server state on refresh
      console.error('Failed to post favorite', e);
    }
  }

  async function addFavoriteFromFile_noUI(file: File, type: 'analyzed' | 'filled', url?: string) {
    const form = new FormData();
    form.append('file', file);
    form.append('type', type);
    form.append('filename', file.name);
    if (url) form.append('url', url);
    await postFavorite(form);
  }

  async function addFavoriteMetadata_noUI(metadata: FileHistoryItem) {
    const form = new FormData();
    form.append('filename', metadata.filename);
    form.append('type', metadata.type);
    form.append('timestamp', metadata.timestamp);
    if (metadata.url) form.append('url', metadata.url);
    await postFavorite(form);
  }

  // Fetch favorites from backend
  async function fetchFavorites() {
    setFavLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/favorites/');
      if (!res.ok) throw new Error('Failed to load favorites');
      const items = await res.json();
      setFavorites(items);
    } catch (e) {
      setFavError((e as Error).message || 'Failed to load favorites');
      setFavorites([]);
    } finally {
      setFavLoading(false);
    }
  }

  useEffect(() => {
    // load favorites once on mount
    fetchFavorites();
  }, []);

  // --- NEW: file-based helpers reused by device & favorites flows ---
  async function analyzeTemplateFile(file: File) {
    if (!file) return;
    if (!file.name.endsWith('.docx')) {
      setError('Only .docx template files are supported');
      return;
    }
    setAnalyzing(true);
    setError(null);
    setAnalysis(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('device_id', deviceId);
      const response = await fetch('http://localhost:8000/api/templates/analyze', { method: 'POST', body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }
      const result = await response.json();
      setAnalysis(result);
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.template_filename, type: 'analyzed', url: '', timestamp: new Date().toISOString() });
      }
      await uploadFileToGCS(file, 'analyzed', new Date().toISOString());
      await addFavoriteMetadata_noUI({ filename: result.template_filename, type: 'analyzed', url: '', timestamp: new Date().toISOString() });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  }

  async function processTemplateFile(file: File) {
    if (!file) return;
    if (!file.name.endsWith('.docx')) {
      setError('Only .docx template files are supported');
      return;
    }
    setProcessing(true);
    setError(null);
    setSuccess(null);
    setDownloadUrl(null);
    setProgress(0);
    setProgressStage('Starting template processing...');
    setStartTime(Date.now());
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('device_id', deviceId);
      setProgress(5);
      setProgressStage('Uploading template...');
      const response = await fetch('http://localhost:8000/api/templates/upload-and-fill', { method: 'POST', body: formData });
      setProgress(15);
      setProgressStage('Template uploaded, analyzing...');
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Processing failed');
      }
      const result = await response.json();
      setProgress(100);
      setProgressStage('Template processing completed!');
      setSuccess(`Template processed successfully! Filled ${Object.keys(result.filled_fields).length} fields.`);
      setDownloadUrl(`http://localhost:8000${result.filled_template_url}`);
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.template_filename, type: 'filled', url: `http://localhost:8000${result.filled_template_url}`, timestamp: new Date().toISOString() });
      }
      await uploadFileToGCS(file, 'filled', new Date().toISOString());
      await addFavoriteFromFile_noUI(file, 'filled', `http://localhost:8000${result.filled_template_url}`);
      if (processInputRef.current) processInputRef.current.value = '';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
      setProgress(0);
      setProgressStage('');
    } finally {
      setProcessing(false);
    }
  }

  async function analyzeCsvFile(file: File) {
    if (!file) return;
    if (!file.name.endsWith('.csv')) {
      setCsvError('Only .csv files are supported');
      return;
    }
    setAnalyzingCsv(true);
    setCsvError(null);
    setCsvAnalysis(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('device_id', deviceId);
      const response = await fetch('http://localhost:8000/api/templates/analyze-csv', { method: 'POST', body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'CSV analysis failed');
      }
      const result = await response.json();
      setCsvAnalysis(result);
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.csv_filename, type: 'analyzed', url: '', timestamp: new Date().toISOString() });
      }
      await uploadFileToGCS(file, 'analyzed', new Date().toISOString());
      if (csvAnalyzeInputRef.current) csvAnalyzeInputRef.current.value = '';
    } catch (err) {
      setCsvError(err instanceof Error ? err.message : 'CSV analysis failed');
    } finally {
      setAnalyzingCsv(false);
    }
  }

  async function processCsvFile(file: File) {
    if (!file) return;
    if (!file.name.endsWith('.csv')) {
      setCsvError('Only .csv files are supported');
      return;
    }
    setProcessingCsv(true);
    setCsvError(null);
    setCsvSuccess(null);
    setCsvDownloadUrl(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('device_id', deviceId);
      const response = await fetch('http://localhost:8000/api/templates/upload-and-fill-csv', { method: 'POST', body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'CSV processing failed');
      }
      const result = await response.json();
      setCsvSuccess(`CSV processed successfully! Filled ${result.filled_cells} out of ${result.total_empty_cells} empty cells.`);
      setCsvDownloadUrl(`http://localhost:8000${result.filled_csv_url}`);
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.csv_filename, type: 'filled', url: `http://localhost:8000${result.filled_csv_url}`, timestamp: new Date().toISOString() });
      }
      await uploadFileToGCS(file, 'filled', new Date().toISOString());
      if (csvInputRef.current) csvInputRef.current.value = '';
    } catch (err) {
      setCsvError(err instanceof Error ? err.message : 'CSV processing failed');
    } finally {
      setProcessingCsv(false);
    }
  }

  // --- REPLACE existing input handlers with wrappers that call the helpers ---
  const handleAnalyzeTemplate = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await analyzeTemplateFile(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleProcessTemplate = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await processTemplateFile(file);
    if (processInputRef.current) processInputRef.current.value = '';
  };

  const handleAnalyzeCsv = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await analyzeCsvFile(file);
    if (csvAnalyzeInputRef.current) csvAnalyzeInputRef.current.value = '';
  };

  const handleProcessCsv = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await processCsvFile(file);
    if (csvInputRef.current) csvInputRef.current.value = '';
  };

  // --- ADDED: modal helpers for choosing source ---
  const openSourceModal = (useCase: 'analyze-template'|'process-template'|'analyze-csv'|'process-csv') => {
    setSourceModalUseCase(useCase);
    setSourceModalView('choose');
    setSourceModalOpen(true);
  };

  const closeSourceModal = () => {
    setSourceModalOpen(false);
    setSourceModalUseCase(null);
    setSourceModalView('choose');
  };

  const chooseDeviceForUseCase = (useCase: typeof sourceModalUseCase) => {
    closeSourceModal();
    setTimeout(() => {
      if (useCase === 'analyze-template') fileInputRef.current?.click();
      if (useCase === 'process-template') processInputRef.current?.click();
      if (useCase === 'analyze-csv') csvAnalyzeInputRef.current?.click();
      if (useCase === 'process-csv') csvInputRef.current?.click();
    }, 50);
  };

  const chooseFavoritesForUseCase = (useCase: typeof sourceModalUseCase) => {
    setSourceModalView('favorites');
  };

  const selectFavoriteAndUse = async (fav: FileHistoryItem) => {
    // quick validation
    if (!fav.filename && !fav.url) {
      const msg = 'Selected favorite has no filename or URL.';
      if (sourceModalUseCase && sourceModalUseCase.includes('csv')) setCsvError(msg);
      else setError(msg);
      return;
    }

    setFavProcessing(true);
    setFavProcessingName(fav.filename || fav.url || null);
    setFavError(null);
    // Build candidate URLs: try backend URL (use BACKEND_BASE) first, then local_storage paths
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    const candidates: string[] = [];

    // If fav.url exists, try backend first (resolve against BACKEND_BASE)
    if (fav.url) {
      const backendUrl = fav.url.startsWith('http') ? fav.url : `${BACKEND_BASE}${fav.url}`;
      candidates.push(backendUrl);
      // also add a local_storage candidate using basename from fav.url (if any)
      try {
        const urlObj = new URL(fav.url, BACKEND_BASE);
        const basename = urlObj.pathname.split('/').pop();
        if (basename) {
          candidates.push(`${origin}/local_storage/favorites_uploads/${encodeURIComponent(basename)}`);
        }
      } catch {
        // ignore
      }
    }

    // also try the declared filename in local_storage (fallback)
    if (fav.filename) {
      candidates.push(`${origin}/local_storage/favorites_uploads/${encodeURIComponent(fav.filename)}`);
    }
    
    // Try each candidate until one returns ok
    let resp: Response | null = null;
    let lastError: Error | null = null;
    try {
      for (const c of candidates) {
        try {
          // small debug log
          // eslint-disable-next-line no-console
          console.debug('[Favorites] trying candidate URL:', c);
          resp = await fetch(c, { method: 'GET' });
          if (resp && resp.ok) {
            // eslint-disable-next-line no-console
            console.debug('[Favorites] fetched OK from', c, 'status', resp.status);
            break;
          } else {
            // eslint-disable-next-line no-console
            console.debug('[Favorites] candidate failed', c, resp?.status);
            resp = null;
          }
        } catch (fetchErr) {
          lastError = fetchErr as Error;
          // eslint-disable-next-line no-console
          console.debug('[Favorites] fetch error for', c, fetchErr);
          resp = null;
        }
      }

      if (!resp) {
        throw new Error(lastError?.message || 'Failed to retrieve favorite file from local storage or backend URL');
      }

      const blob = await resp.blob();
      const fileName = fav.filename || resp.headers.get('x-filename') || (resp.url ? resp.url.split('/').pop() : null) || 'favorite-file';
      const file = new File([blob], fileName, { type: blob.type || 'application/octet-stream' });

      // call appropriate handler and only close modal on success
      if (sourceModalUseCase === 'analyze-template') {
        await analyzeTemplateFile(file);
      } else if (sourceModalUseCase === 'process-template') {
        await processTemplateFile(file);
      } else if (sourceModalUseCase === 'analyze-csv') {
        await analyzeCsvFile(file);
      } else if (sourceModalUseCase === 'process-csv') {
        await processCsvFile(file);
      } else {
        throw new Error('Unknown use case');
      }

      // success -> close modal
      closeSourceModal();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to use favorite';
      // show error inside modal so user sees it
      setFavError(msg);
      if (sourceModalUseCase && sourceModalUseCase.includes('csv')) setCsvError(msg);
      else setError(msg);
      // keep modal open so user can retry or click the download link
      // eslint-disable-next-line no-console
      console.error('[Favorites] selectFavoriteAndUse failed:', msg);
    } finally {
      setFavProcessing(false);
      setFavProcessingName(null);
    }
  };

  // Helper to download filled template or csv
  const downloadTemplate = () => {
    if (!downloadUrl) return;
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  // Small button style tokens used across this component for consistent UI
  const primaryBtn = 'px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50';
  const ghostBtn = 'px-4 py-2 border border-gray-300 rounded text-sm bg-white hover:bg-gray-50 disabled:opacity-50';
  const smallGhost = 'px-3 py-1 border border-gray-200 rounded text-sm bg-white hover:bg-gray-50 disabled:opacity-50';

  return (
    <div className="space-y-6">
      {/* Template Analysis Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Analyze Template</h3>
        <p className="text-sm text-muted mb-4">Upload a template to see which fields can be filled for Device {deviceId}.</p>

        <div className="space-y-4">
          <div>
            <input ref={fileInputRef} type="file" accept=".docx" onChange={handleAnalyzeTemplate} disabled={analyzing} className="hidden" />
            <label className="block text-sm font-medium text-gray-700 mb-2">Select Template to Analyze</label>
            <div className="flex gap-2">
              <button onClick={() => openSourceModal('analyze-template')} disabled={analyzing} className={ghostBtn}>
                {analyzing ? 'Analyzing...' : 'Select File'}
              </button>
              <span className="text-xs text-gray-500 self-center">Only .docx files supported</span>
            </div>
          </div>

          {analyzing && (
            <div className="flex items-center space-x-2 text-gray-700">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
              <span className="text-sm">Analyzing template...</span>
            </div>
          )}
        </div>
      </div>

      {/* Analysis Results */}
      {analysis && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Results</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-gray-900">{analysis.total_fields}</div>
              <div className="text-sm text-muted">Total Fields</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-green-600">{analysis.fillable_fields}</div>
              <div className="text-sm text-muted">Fillable Fields</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-red-600">{analysis.total_fields - analysis.fillable_fields}</div>
              <div className="text-sm text-muted">Missing Fields</div>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium text-gray-900">Field Details:</h4>
            <div className="space-y-2">
              {Object.entries(analysis.field_analysis).map(([field, details]) => (
                <div key={field} className="flex items-center justify-between p-3 bg-gray-50 rounded-md border border-[var(--border)]">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${details.can_fill ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="font-medium">{field}</span>
                  </div>
                  <div className="text-sm text-muted">
                    {details.can_fill ? (
                      <span>
                        Confidence: {typeof details.confidence === 'number' && !isNaN(details.confidence) ? (details.confidence * 100).toFixed(1) : 'N/A'}%
                        ({details.sources || 0} sources)
                      </span>
                    ) : (
                      <span>No matching content found</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Template Processing Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex gap-6">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Process Template</h3>
            <p className="text-sm text-muted mb-4">Upload a template to automatically fill it with information from Device {deviceId}.</p>

            <div className="space-y-4">
              <div>
                <input ref={processInputRef} type="file" accept=".docx" onChange={handleProcessTemplate} disabled={processing} className="hidden" />
                <label className="block text-sm font-medium text-gray-700 mb-2">Select Template to Process</label>
                <div className="flex gap-2">
                  <button onClick={() => openSourceModal('process-template')} disabled={processing} className={primaryBtn}>
                    {processing ? 'Processing...' : 'Select File'}
                  </button>
                  <p className="text-xs text-gray-500 self-center">The template will be filled automatically</p>
                </div>
              </div>

              {processing && (
                <div className="flex items-center space-x-2 text-gray-700">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></div>
                  <span className="text-sm">Processing template...</span>
                </div>
              )}

              {error && <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">{error}</div>}

              {success && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-700">
                  <div>{success}</div>
                  {downloadUrl && (
                    <button onClick={downloadTemplate} className="mt-2 px-3 py-1 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Download Filled Template</button>
                  )}
                </div>
              )}
            </div>
          </div>

          {processing && (
            <div className="w-80 bg-gray-50 rounded-lg p-4 border-l-4 border-green-500">
              <h4 className="font-semibold text-gray-900 mb-3 text-center">Processing Progress</h4>

              <div className="mb-4">
                <div className="flex justify-between text-sm text-muted mb-1">
                  <span>Progress</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-[var(--primary)] h-3 rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
              </div>

              <div className="mb-4">
                <div className="text-sm font-medium text-gray-700 mb-1">Current Stage:</div>
                <div className="text-sm text-muted flex items-center"><div className="animate-pulse w-2 h-2 bg-green-500 rounded-full mr-2"></div>{progressStage}</div>
              </div>

              {estimatedTime > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-gray-700 mb-1">Estimated Time Remaining:</div>
                  <div className="text-sm text-muted">{estimatedTime > 60 ? `${Math.floor(estimatedTime / 60)}m ${estimatedTime % 60}s` : `${estimatedTime}s`}</div>
                </div>
              )}

              <div className="space-y-2 text-xs text-muted">
                <div className="flex justify-between"><span>Template Analysis</span><span>{progress >= 30 ? '✓' : '○'}</span></div>
                <div className="flex justify-between"><span>Knowledge Search</span><span>{progress >= 60 ? '✓' : '○'}</span></div>
                <div className="flex justify-between"><span>Content Generation</span><span>{progress >= 85 ? '✓' : '○'}</span></div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* CSV Analysis Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Analyze CSV
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Upload a CSV file to see which empty cells can be filled with the available documents for Device {deviceId}.
        </p>
        
        <div className="space-y-4">
          <div>
            <input ref={csvAnalyzeInputRef} type="file" accept=".csv" onChange={handleAnalyzeCsv} disabled={analyzingCsv} className="hidden" />
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select CSV File to Analyze
            </label>
            <div className="flex gap-2">
              <button onClick={() => openSourceModal('analyze-csv')} disabled={analyzingCsv} className={primaryBtn}>
                {analyzingCsv ? 'Analyzing...' : 'Select File'}
              </button>
              <p className="text-xs text-gray-500 self-center">This will analyze your CSV structure and show which empty cells can be filled</p>
            </div>
          </div>
          {/* ...existing CSV analyzing UI ... */}
        </div>
      </div>

      {/* CSV Processing Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Process CSV
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Upload a CSV file to automatically fill missing values with information from Device {deviceId}&apos;s documents.
        </p>
        
        <div className="space-y-4">
          <div>
            <input ref={csvInputRef} type="file" accept=".csv" onChange={handleProcessCsv} disabled={processingCsv} className="hidden" />
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select CSV File to Process
            </label>
            <div className="flex gap-2">
              <button onClick={() => openSourceModal('process-csv')} disabled={processingCsv} className={primaryBtn}>
                {processingCsv ? 'Processing...' : 'Select File'}
              </button>
              <p className="text-xs text-gray-500 self-center">The CSV will be analyzed and empty cells filled with relevant data</p>
            </div>
          </div>
          {/* ...existing CSV processing UI ... */}
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          How to Use Templates & CSV Processing
        </h3>
        <div className="text-sm text-blue-800 space-y-2">
          <div>
            <p className="font-semibold">Template Processing:</p>
            <p><strong>1. Create Template:</strong> Use Word to create a .docx template with placeholders like {`{name}`}, {`{date}`}, {`{amount}`}, etc.</p>
            <p><strong>2. Analyze First:</strong> Use the analyze function to see which fields can be filled with your uploaded documents.</p>
            <p><strong>3. Process Template:</strong> Upload your template to automatically fill placeholders with relevant information.</p>
            <p><strong>4. Download Result:</strong> Get your filled template ready for use.</p>
          </div>
          <div className="mt-4">
            <p className="font-semibold">CSV Processing:</p>
            <p><strong>1. Prepare CSV:</strong> Create a CSV file with headers and some empty cells that need to be filled.</p>
            <p><strong>2. Upload CSV:</strong> Use the CSV processor to analyze and fill empty cells with relevant data.</p>
            <p><strong>3. AI Enhancement:</strong> The system will intelligently match and populate missing information from your documents.</p>
            <p><strong>4. Download Enhanced CSV:</strong> Get your completed CSV with all available fields filled.</p>
          </div>
        </div>
      </div>

      {/* --- ADDED: Modal for choosing source and favorites list --- */}
      {sourceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-md max-w-2xl w-full p-6 card">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold">Choose Source</h4>
              <button onClick={closeSourceModal} className="text-sm text-muted hover:text-gray-700">Close</button>
            </div>

            <div className="flex gap-3 mb-4">
              <button
                onClick={() => setSourceModalView('choose')}
                className={`px-3 py-1 rounded text-sm ${sourceModalView === 'choose' ? 'bg-[var(--primary)] text-white' : 'btn-ghost'}`}
              >
                Upload from Device
              </button>
              <button
                onClick={() => chooseFavoritesForUseCase(sourceModalUseCase!)}
                className={`px-3 py-1 rounded text-sm ${sourceModalView === 'favorites' ? 'bg-[var(--primary)] text-white' : 'btn-ghost'}`}
              >
                Favorites
              </button>
              <button
                onClick={() => chooseDeviceForUseCase(sourceModalUseCase!)}
                className="ml-auto btn-ghost text-sm"
              >
                Choose Local Device File
              </button>
            </div>

            {sourceModalView === 'choose' && (
              <div className="text-sm text-muted">
                <p>Select a file from your device (the file picker will open when you confirm).</p>
              </div>
            )}

            {sourceModalView === 'favorites' && (
              <div className="space-y-3">
                {favLoading ? (
                  <div className="text-sm text-muted">Loading favorites...</div>
                ) : favorites.length === 0 ? (
                  <div className="text-sm text-muted">No favorites available</div>
                ) : (
                  favorites.map((f) => (
                    <div key={(f.timestamp || '') + f.filename} className="flex items-center justify-between p-3 bg-gray-50 rounded border border-[var(--border)]">
                      <div className="flex-1">
                        <div className="font-medium truncate">{f.filename || (f.url ?? 'Unknown')}</div>
                        <div className="text-xs text-muted">{new Date(f.timestamp).toLocaleString()}</div>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <a href={f.url || '#'} target="_blank" rel="noreferrer" className="text-[var(--primary)] hover:underline text-sm">Download</a>
                        <button
                          onClick={() => selectFavoriteAndUse(f)}
                          disabled={favProcessing}
                          className="btn-primary text-sm"
                        >
                          {favProcessing && favProcessingName === f.filename ? 'Using...' : 'Use'}
                        </button>
                      </div>
                    </div>
                  ))
                )}
                {favError && <div className="text-sm text-red-600">{favError}</div>}
              </div>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <button onClick={closeSourceModal} className="btn-ghost">Cancel</button>
              <button
                onClick={() => {
                  // quick fallback: open device file picker for the chosen use case
                  chooseDeviceForUseCase(sourceModalUseCase!);
                }}
                className="btn-primary"
              >
                Upload from device
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
