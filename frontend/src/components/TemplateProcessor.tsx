'use client';

import { useState, useRef, useEffect } from 'react';
import { documentReverseApi } from '@/lib/api';


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
  analysis_type: string;
  summary: {
    total_rows: number;
    total_columns: number;
    total_empty_cells: number;
    columns_with_empty_cells: number;
    sample_cells_analyzed: number;
    fillable_cells: number;
    overall_fill_rate: number;
    analysis_status: string;
  };
  columns: string[];
  column_analysis: Record<string, {
    empty_cells_in_column: number;
    sample_cells_analyzed: number;
    fillable_cells: number;
    fill_rate: number;
    average_confidence: number;
    sample_analysis: Record<string, {
      can_fill: boolean;
      confidence: number;
      sources: number;
      sample_query?: string;
      error?: string;
    }>;
    data_pattern: string;
  }>;
  recommendations: {
    high_fill_rate_columns: string[];
    low_fill_rate_columns: string[];
    total_processable: number;
  };
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
  
  // RAG Filling Mode State
  const [fillingMode, setFillingMode] = useState<'general' | 'accurate'>('general');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const processInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const csvAnalyzeInputRef = useRef<HTMLInputElement>(null);
  const reverseInputRef = useRef<HTMLInputElement>(null);
  const activeIntervalsRef = useRef<NodeJS.Timeout[]>([]);

  // Document Reverse Processing state
  const [reverseProcessing, setReverseProcessing] = useState(false);
  const [reverseError, setReverseError] = useState<string | null>(null);
  const [reverseSuccess, setReverseSuccess] = useState<string | null>(null);
  const [reverseDownloadUrl, setReverseDownloadUrl] = useState<string | null>(null);

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

  // --- File-based analysis and processing functions ---
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
      formData.append('filling_mode', fillingMode);
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
      setSuccess(`Template processed successfully using ${fillingMode} mode! Filled ${Object.keys(result.filled_fields).length} fields.`);
      setDownloadUrl(`http://localhost:8000${result.filled_template_url}`);
      console.log('Template processing result:', result);
      console.log('Calling onFileHistoryUpdate with:', { filename: result.template_filename, type: 'filled', url: `http://localhost:8000${result.filled_template_url}`, timestamp: new Date().toISOString() });
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.template_filename, type: 'filled', url: `http://localhost:8000${result.filled_template_url}`, timestamp: new Date().toISOString() });
        console.log('onFileHistoryUpdate called successfully for template');
      } else {
        console.log('onFileHistoryUpdate is not available for template');
      }
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
      formData.append('filling_mode', fillingMode);
      const response = await fetch('http://localhost:8000/api/templates/upload-and-fill-csv', { method: 'POST', body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'CSV processing failed');
      }
      const result = await response.json();
      console.log('CSV processing result:', result);
      setCsvSuccess(`CSV processed successfully! Filled ${result.filled_cells} cells using ${fillingMode} mode.`);
      setCsvDownloadUrl(`http://localhost:8000${result.filled_csv_url}`);
      console.log('Set CSV download URL to:', `http://localhost:8000${result.filled_csv_url}`);
      console.log('Calling onFileHistoryUpdate with:', { filename: result.filename, type: 'filled', url: `http://localhost:8000${result.filled_csv_url}`, timestamp: new Date().toISOString() });
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.filename, type: 'filled', url: `http://localhost:8000${result.filled_csv_url}`, timestamp: new Date().toISOString() });
        console.log('onFileHistoryUpdate called successfully for CSV');
      } else {
        console.log('onFileHistoryUpdate is not available for CSV');
      }
      if (csvInputRef.current) csvInputRef.current.value = '';
    } catch (err) {
      setCsvError(err instanceof Error ? err.message : 'CSV processing failed');
    } finally {
      setProcessingCsv(false);
    }
  }

  // Document Reverse Processing function
  async function processFilledDocumentToBlank(file: File) {
    if (!file) return;
    
    const allowedExtensions = ['.pdf', '.docx', '.doc'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
      setReverseError(`Unsupported file type: ${fileExtension}. Supported formats: ${allowedExtensions.join(', ')}`);
      return;
    }
    
    setReverseProcessing(true);
    setReverseError(null);
    setReverseSuccess(null);
    setReverseDownloadUrl(null);
    
    try {
      console.log('Processing filled document to blank template:', file.name);
      const result = await documentReverseApi.createBlankTemplate(file, deviceId);
      
      setReverseSuccess(`✅ Successfully created blank template from ${file.name}`);
      setReverseDownloadUrl(result.download_url);
      
      console.log('Document reverse processing result:', result);
      
      // Add to file history if callback is available
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({
          filename: result.template_filename,
          type: 'filled', // Using 'filled' type as it's the closest available
          url: `http://localhost:8000${result.download_url}`,
          timestamp: new Date().toISOString()
        });
        console.log('Added blank template to file history');
      }
      
      if (reverseInputRef.current) reverseInputRef.current.value = '';
    } catch (err) {
      console.error('Document reverse processing error:', err);
      setReverseError(err instanceof Error ? err.message : 'Document reverse processing failed');
    } finally {
      setReverseProcessing(false);
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

  const handleReverseProcessing = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await processFilledDocumentToBlank(file);
    if (reverseInputRef.current) reverseInputRef.current.value = '';
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

  // Helper to download filled CSV
  const downloadCsv = () => {
    if (!csvDownloadUrl) {
      console.log('No CSV download URL available');
      return;
    }
    console.log('Downloading CSV from:', csvDownloadUrl);
    const a = document.createElement('a');
    a.href = csvDownloadUrl;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  // Helper to download blank template
  const downloadBlankTemplate = () => {
    if (!reverseDownloadUrl) {
      console.log('No blank template download URL available');
      return;
    }
    console.log('Downloading blank template from:', reverseDownloadUrl);
    const a = document.createElement('a');
    a.href = `http://localhost:8000${reverseDownloadUrl}`;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  // Small button style tokens used across this component for consistent UI
  const primaryBtn = 'px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50';
  const ghostBtn = 'px-4 py-2 border border-gray-300 rounded text-sm bg-white hover:bg-gray-50 disabled:opacity-50';

  return (
    <div className="space-y-6">
      {/* RAG Filling Mode Toggle */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm border border-blue-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-900 mb-1">RAG Filling Mode</h3>
            <p className="text-xs text-gray-600">
              Choose how documents should be filled: 
              <span className="font-medium text-blue-600"> General</span> mode includes descriptions and interpretive content, 
              <span className="font-medium text-purple-600"> Accurate</span> mode uses only exact matches from the knowledge base.
            </p>
          </div>
          <div className="ml-4">
            <div className="flex items-center bg-white rounded-lg border border-gray-200 p-1">
              <button
                onClick={() => setFillingMode('general')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  fillingMode === 'general'
                    ? 'bg-blue-500 text-white shadow-sm'
                    : 'text-gray-600 hover:text-blue-600 hover:bg-blue-50'
                }`}
              >
                📝 General
              </button>
              <button
                onClick={() => setFillingMode('accurate')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  fillingMode === 'accurate'
                    ? 'bg-purple-500 text-white shadow-sm'
                    : 'text-gray-600 hover:text-purple-600 hover:bg-purple-50'
                }`}
              >
                🎯 Accurate
              </button>
            </div>
          </div>
        </div>
        
        {/* Mode Description */}
        <div className="mt-3 p-2 bg-white rounded border-l-4 border-l-blue-400">
          {fillingMode === 'general' ? (
            <p className="text-xs text-gray-700">
              <span className="font-medium text-blue-600">General Mode:</span> Fills documents with accurate data plus contextual descriptions. 
              Suitable for most documents where additional explanatory content enhances readability.
            </p>
          ) : (
            <p className="text-xs text-gray-700">
              <span className="font-medium text-purple-600">Accurate Mode:</span> Uses only exact values from the knowledge base with no interpretations. 
              Ideal for sensitive forms, regulatory documents, or when precise data integrity is critical.
            </p>
          )}
        </div>
      </div>

      {/* Template Analysis Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Analyze Template</h3>
        <p className="text-sm text-muted mb-4">Upload a template to see which fields can be filled for Device {deviceId}.</p>

        <div className="space-y-4">
          <div>
            <input ref={fileInputRef} type="file" accept=".docx" onChange={handleAnalyzeTemplate} disabled={analyzing} className="hidden" />
            <label className="block text-sm font-medium text-gray-700 mb-2">Select Template to Analyze</label>
            <div className="flex gap-2">
              <button onClick={() => fileInputRef.current?.click()} disabled={analyzing} className={ghostBtn}>
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
                  <button onClick={() => processInputRef.current?.click()} disabled={processing} className={primaryBtn}>
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
          Upload a CSV file to see which empty cells can be filled with the available documents for Device {deviceId}. <strong>Note:</strong> This only analyzes the file - use &quot;Process CSV&quot; below to actually fill the cells.
        </p>
        
        <div className="space-y-4">
          <div>
            <input ref={csvAnalyzeInputRef} type="file" accept=".csv" onChange={handleAnalyzeCsv} disabled={analyzingCsv} className="hidden" />
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select CSV File to Analyze
            </label>
            <div className="flex gap-2">
              <button onClick={() => csvAnalyzeInputRef.current?.click()} disabled={analyzingCsv} className={primaryBtn}>
                {analyzingCsv ? 'Analyzing...' : 'Select File'}
              </button>
              <p className="text-xs text-gray-500 self-center">This will analyze your CSV structure and show which empty cells can be filled</p>
            </div>
          </div>
          
          {csvError && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{csvError}</p>
            </div>
          )}
          
          {csvAnalysis && (
            <div className="bg-green-50 border border-green-200 rounded-md p-4">
              <h4 className="text-sm font-medium text-green-800 mb-3">CSV Analysis Results</h4>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">File:</span> {csvAnalysis.csv_filename}
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Rows:</span> {csvAnalysis.summary.total_rows}
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Columns:</span> {csvAnalysis.summary.total_columns}
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Empty Cells:</span> {csvAnalysis.summary.total_empty_cells}
                  </div>
                </div>
                
                <div className="bg-white rounded p-3 border">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-gray-700">Fillability:</span>
                    <span className="text-lg font-semibold text-blue-600">
                      {csvAnalysis.summary.fillable_cells}/{csvAnalysis.summary.total_empty_cells} cells
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${csvAnalysis.summary.total_empty_cells > 0 ? (csvAnalysis.summary.fillable_cells / csvAnalysis.summary.total_empty_cells) * 100 : 0}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {csvAnalysis.summary.total_empty_cells > 0 ? Math.round((csvAnalysis.summary.fillable_cells / csvAnalysis.summary.total_empty_cells) * 100) : 0}% of empty cells can be filled
                  </p>
                </div>
                
                {csvAnalysis.column_analysis && Object.keys(csvAnalysis.column_analysis).length > 0 && (
                  <div>
                    <h5 className="font-medium text-gray-700 mb-2">Column Analysis:</h5>
                    <div className="space-y-2">
                      {Object.entries(csvAnalysis.column_analysis).map(([column, data]) => (
                        <div key={column} className="flex justify-between items-center p-2 bg-white rounded border text-sm">
                          <span className="font-medium">{column}</span>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 rounded text-xs ${data.fill_rate > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                              {data.fill_rate > 0 ? 'Fillable' : 'Cannot Fill'}
                            </span>
                            {data.fill_rate > 0 && (
                              <>
                                <span className="text-gray-600">
                                  {Math.round(data.fill_rate * 100)}% fill rate
                                </span>
                                <span className="text-gray-600">
                                  {Math.round(data.average_confidence * 100)}% confidence
                                </span>
                                <span className="text-gray-600">
                                  {data.empty_cells_in_column} empty cells
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {csvAnalysis.recommendations && (
                  <div className="bg-blue-50 rounded p-3 border">
                    <h5 className="font-medium text-blue-800 mb-2">Recommendations:</h5>
                    <div className="text-sm space-y-1">
                      <div>
                        <span className="font-medium">High fillability:</span> {csvAnalysis.recommendations.high_fill_rate_columns.join(', ') || 'None'}
                      </div>
                      <div>
                        <span className="font-medium">Low fillability:</span> {csvAnalysis.recommendations.low_fill_rate_columns.join(', ') || 'None'}
                      </div>
                      <div>
                        <span className="font-medium">Processable columns:</span> {csvAnalysis.recommendations.total_processable} out of {csvAnalysis.summary.columns_with_empty_cells}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* CSV Processing Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Process CSV
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Upload a CSV file to automatically fill missing values with information from Device {deviceId}&apos;s documents. <strong>This creates a new filled CSV file that you can download.</strong>
        </p>
        
        <div className="space-y-4">
          <div>
            <input ref={csvInputRef} type="file" accept=".csv" onChange={handleProcessCsv} disabled={processingCsv} className="hidden" />
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select CSV File to Process
            </label>
            <div className="flex gap-2">
              <button onClick={() => csvInputRef.current?.click()} disabled={processingCsv} className={primaryBtn}>
                {processingCsv ? 'Processing...' : 'Select File'}
              </button>
              <p className="text-xs text-gray-500 self-center">The CSV will be analyzed and empty cells filled with relevant data</p>
            </div>
          </div>
          
          {csvError && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{csvError}</p>
            </div>
          )}
          
          {csvSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-md p-3">
              <p className="text-sm text-green-600">{csvSuccess}</p>
              {csvDownloadUrl && (
                <button onClick={downloadCsv} className={primaryBtn + ' mt-2'}>
                  Download Filled CSV
                </button>
              )}
            </div>
          )}
          
          {processingCsv && (
            <div className="flex items-center space-x-2 text-gray-700">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
              <span className="text-sm">Processing CSV...</span>
            </div>
          )}
        </div>
      </div>

      {/* Document Reverse Processing Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Create Blank Template
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Upload a <strong>filled document</strong> (PDF or Word) to automatically create a blank template. 
          PDFs will be processed using OCR and converted to Word format. Answers will be removed and replaced with blank fields.
        </p>
        
        <div className="space-y-4">
          <div>
            <input 
              ref={reverseInputRef} 
              type="file" 
              accept=".pdf,.docx,.doc" 
              onChange={handleReverseProcessing} 
              disabled={reverseProcessing} 
              className="hidden" 
            />
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Filled Document to Convert
            </label>
            <div className="flex gap-2">
              <button 
                onClick={() => reverseInputRef.current?.click()} 
                disabled={reverseProcessing} 
                className={primaryBtn}
              >
                {reverseProcessing ? 'Processing...' : 'Select Filled Document'}
              </button>
              <span className="text-xs text-gray-500 self-center">
                Supports PDF (with OCR), Word documents (.docx, .doc)
              </span>
            </div>
          </div>
          
          {reverseError && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{reverseError}</p>
            </div>
          )}
          
          {reverseSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-md p-3">
              <p className="text-sm text-green-600">{reverseSuccess}</p>
              {reverseDownloadUrl && (
                <button onClick={downloadBlankTemplate} className={primaryBtn + ' mt-2'}>
                  Download Blank Template
                </button>
              )}
            </div>
          )}
          
          {reverseProcessing && (
            <div className="flex items-center space-x-2 text-gray-700">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
              <span className="text-sm">
                {reverseProcessing ? 'Creating blank template...' : 'Processing...'}
              </span>
            </div>
          )}

          {/* Feature Details */}
          <div className="bg-gray-50 rounded-md p-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">How it works:</h4>
            <ul className="text-xs text-gray-600 space-y-1">
              <li>• <strong>PDF files:</strong> Uses advanced OCR to extract text, then creates blank template in Word format</li>
              <li>• <strong>Word files:</strong> Analyzes content and removes answers while preserving question structure</li>
              <li>• <strong>Smart detection:</strong> Automatically identifies form fields, labels, and answers</li>
              <li>• <strong>Structure preservation:</strong> Maintains original document layout and formatting</li>
              <li>• <strong>Word output:</strong> All blank templates are saved as editable Word documents</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          How to Use Templates, CSV Processing & Document Reverse
        </h3>
        <div className="text-sm text-blue-800 space-y-2">
          <div className="bg-white rounded p-3 border-l-4 border-blue-400 mb-4">
            <p className="font-semibold text-blue-900 mb-1">📝 RAG Filling Modes:</p>
            <p><strong>General Mode:</strong> Provides accurate data with descriptive context for better readability. Best for most documents.</p>
            <p><strong>Accurate Mode:</strong> Uses only exact values from knowledge base without interpretation. Ideal for regulatory forms and sensitive documents.</p>
          </div>
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
            <p><strong>2. Analyze First (Optional):</strong> Use &quot;Analyze CSV&quot; to see which empty cells can be filled without creating a file.</p>
            <p><strong>3. Process CSV:</strong> Use &quot;Process CSV&quot; to actually fill empty cells and create a new downloadable file.</p>
            <p><strong>4. Download Enhanced CSV:</strong> Get your completed CSV with all available fields filled from the file history.</p>
          </div>
          <div className="mt-4">
            <p className="font-semibold">Create Blank Template (NEW):</p>
            <p><strong>1. Upload Filled Document:</strong> Upload a PDF or Word document that already has answers filled in.</p>
            <p><strong>2. Automatic Processing:</strong> The system will use OCR (for PDFs) or direct text extraction (for Word) to analyze the content.</p>
            <p><strong>3. Smart Field Detection:</strong> Automatically identifies questions and answers, then removes answers while keeping questions.</p>
            <p><strong>4. Download Blank Template:</strong> Get a clean Word document template ready for reuse with blank fields for answers.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
