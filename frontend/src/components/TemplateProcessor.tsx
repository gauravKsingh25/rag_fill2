'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { documentReverseApi } from '@/lib/api';
import { FileHistoryItem } from './FileHistory';
import { Button } from './ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/Card';
import { Progress } from './ui/Progress';
import { Badge } from './ui/Badge';
import { Input } from './ui/Input';
import { API_BASE_URL } from '@/config/api';
import { 
  FiUpload, 
  FiFileText, 
  FiBarChart, 
  FiDownload, 
  FiLoader, 
  FiCheckCircle, 
  FiXCircle, 
  FiEye,
  FiSettings,
  FiZap,
  FiTarget,
  FiDatabase,
  FiRefreshCw
} from 'react-icons/fi';

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
      const response = await fetch(`${API_BASE_URL}/api/templates/analyze`, { method: 'POST', body: formData });
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
      const response = await fetch('${API_BASE_URL}/api/templates/upload-and-fill', { method: 'POST', body: formData });
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
      setDownloadUrl(`${API_BASE_URL}${result.filled_template_url}`);
      console.log('Template processing result:', result);
      console.log('Calling onFileHistoryUpdate with:', { filename: result.template_filename, type: 'filled', url: `${API_BASE_URL}${result.filled_template_url}`, timestamp: new Date().toISOString() });
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.template_filename, type: 'filled', url: `${API_BASE_URL}${result.filled_template_url}`, timestamp: new Date().toISOString() });
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
      const response = await fetch('${API_BASE_URL}/api/templates/analyze-csv', { method: 'POST', body: formData });
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
      const response = await fetch('${API_BASE_URL}/api/templates/upload-and-fill-csv', { method: 'POST', body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'CSV processing failed');
      }
      const result = await response.json();
      console.log('CSV processing result:', result);
      setCsvSuccess(`CSV processed successfully! Filled ${result.filled_cells} cells using ${fillingMode} mode.`);
      setCsvDownloadUrl(`${API_BASE_URL}${result.filled_csv_url}`);
      console.log('Set CSV download URL to:', `${API_BASE_URL}${result.filled_csv_url}`);
      console.log('Calling onFileHistoryUpdate with:', { filename: result.filename, type: 'filled', url: `${API_BASE_URL}${result.filled_csv_url}`, timestamp: new Date().toISOString() });
      if (onFileHistoryUpdate) {
        onFileHistoryUpdate({ filename: result.filename, type: 'filled', url: `${API_BASE_URL}${result.filled_csv_url}`, timestamp: new Date().toISOString() });
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
          url: `${API_BASE_URL}${result.download_url}`,
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
    a.href = `${API_BASE_URL}${reverseDownloadUrl}`;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: "spring" as const,
        stiffness: 300,
        damping: 24
      }
    }
  };

  return (
    <motion.div 
      className="space-y-8 p-1"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* RAG Filling Mode Toggle */}
      <motion.div variants={itemVariants}>
        <Card variant="glass" className="border-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-white rounded-lg shadow-sm">
                  <FiSettings className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <CardTitle className="text-gray-900">RAG Filling Mode</CardTitle>
                  <CardDescription className="text-gray-600">
                    Choose how documents should be filled with intelligent content
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center bg-white rounded-xl p-1 shadow-sm border">
                <Button
                  onClick={() => setFillingMode('general')}
                  variant={fillingMode === 'general' ? 'default' : 'ghost'}
                  size="sm"
                  className={`rounded-lg transition-all ${
                    fillingMode === 'general'
                      ? 'bg-blue-500 text-white shadow-md'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-blue-50'
                  }`}
                >
                  <FiZap className="h-4 w-4 mr-2" />
                  General
                </Button>
                <Button
                  onClick={() => setFillingMode('accurate')}
                  variant={fillingMode === 'accurate' ? 'default' : 'ghost'}
                  size="sm"
                  className={`rounded-lg transition-all ${
                    fillingMode === 'accurate'
                      ? 'bg-purple-500 text-white shadow-md'
                      : 'text-gray-600 hover:text-purple-600 hover:bg-purple-50'
                  }`}
                >
                  <FiTarget className="h-4 w-4 mr-2" />
                  Accurate
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <AnimatePresence mode="wait">
              <motion.div
                key={fillingMode}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="p-4 bg-white/70 rounded-xl border border-white/50"
              >
                {fillingMode === 'general' ? (
                  <div className="flex items-start space-x-3">
                    <FiZap className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-blue-900 mb-1">General Mode Active</p>
                      <p className="text-sm text-gray-700">
                        Fills documents with accurate data plus contextual descriptions. 
                        Provides comprehensive, readable content suitable for most documents.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start space-x-3">
                    <FiTarget className="h-5 w-5 text-purple-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-purple-900 mb-1">Accurate Mode Active</p>
                      <p className="text-sm text-gray-700">
                        Uses only exact values from the knowledge base with no interpretations. 
                        Perfect for regulatory documents and sensitive forms requiring precision.
                      </p>
                    </div>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </CardContent>
        </Card>
      </motion.div>

      {/* Template Analysis Section */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <FiEye className="h-5 w-5 text-blue-600" />
              </div>
              <span>Analyze Template</span>
            </CardTitle>
            <CardDescription>
              Upload a template to see which fields can be filled for Device {deviceId}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <Input 
                ref={fileInputRef} 
                type="file" 
                accept=".docx" 
                onChange={handleAnalyzeTemplate} 
                disabled={analyzing} 
                className="hidden" 
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select Template to Analyze
                </label>
                <div className="flex items-center space-x-3">
                  <Button 
                    onClick={() => fileInputRef.current?.click()} 
                    disabled={analyzing}
                    className="flex items-center space-x-2"
                    variant="outline"
                  >
                    {analyzing ? (
                      <FiLoader className="h-4 w-4 animate-spin" />
                    ) : (
                      <FiUpload className="h-4 w-4" />
                    )}
                    <span>{analyzing ? 'Analyzing...' : 'Choose File'}</span>
                  </Button>
                  <Badge variant="secondary" className="text-xs">
                    Only .docx files supported
                  </Badge>
                </div>
              </div>

              <AnimatePresence>
                {analyzing && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200"
                  >
                    <FiLoader className="h-5 w-5 text-blue-600 animate-spin" />
                    <span className="text-sm text-blue-800 font-medium">Analyzing template structure...</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Analysis Results */}
      <AnimatePresence>
        {analysis && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            variants={itemVariants}
          >
            <Card variant="elevated" className="border-green-200">
              <CardHeader>
                <CardTitle className="flex items-center space-x-3 text-green-800">
                  <FiCheckCircle className="h-6 w-6" />
                  <span>Analysis Results</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  <motion.div 
                    className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6 border border-gray-200"
                    whileHover={{ scale: 1.02 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <div className="text-3xl font-bold text-gray-900 mb-2">{analysis.total_fields}</div>
                    <div className="text-sm text-gray-600 font-medium">Total Fields</div>
                  </motion.div>
                  <motion.div 
                    className="bg-gradient-to-br from-green-50 to-emerald-100 rounded-xl p-6 border border-green-200"
                    whileHover={{ scale: 1.02 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <div className="text-3xl font-bold text-green-700 mb-2">{analysis.fillable_fields}</div>
                    <div className="text-sm text-green-600 font-medium">Fillable Fields</div>
                  </motion.div>
                  <motion.div 
                    className="bg-gradient-to-br from-red-50 to-rose-100 rounded-xl p-6 border border-red-200"
                    whileHover={{ scale: 1.02 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <div className="text-3xl font-bold text-red-700 mb-2">{analysis.total_fields - analysis.fillable_fields}</div>
                    <div className="text-sm text-red-600 font-medium">Missing Fields</div>
                  </motion.div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900 flex items-center space-x-2">
                    <FiFileText className="h-5 w-5" />
                    <span>Field Details</span>
                  </h4>
                  <div className="space-y-3">
                    {Object.entries(analysis.field_analysis).map(([field, details], index) => (
                      <motion.div
                        key={field}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all duration-200 hover:shadow-md"
                      >
                        <div className="flex items-center space-x-4">
                          <div className={`w-3 h-3 rounded-full ${details.can_fill ? 'bg-green-500' : 'bg-red-500'}`}></div>
                          <span className="font-medium text-gray-900">{field}</span>
                          <Badge variant={details.can_fill ? 'success' : 'destructive'}>
                            {details.can_fill ? 'Fillable' : 'Missing'}
                          </Badge>
                        </div>
                        <div className="text-sm text-gray-600">
                          {details.can_fill ? (
                            <span className="flex items-center space-x-2">
                              <span>
                                Confidence: {typeof details.confidence === 'number' && !isNaN(details.confidence) ? (details.confidence * 100).toFixed(1) : 'N/A'}%
                              </span>
                              <span className="text-gray-400">•</span>
                              <span>({details.sources || 0} sources)</span>
                            </span>
                          ) : (
                            <span className="text-red-600">No matching content found</span>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Template Processing Section */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <FiRefreshCw className="h-5 w-5 text-green-600" />
              </div>
              <span>Process Template</span>
            </CardTitle>
            <CardDescription>
              Upload a template to automatically fill it with information from Device {deviceId}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-4">
                <div className="space-y-3">
                  <Input 
                    ref={processInputRef} 
                    type="file" 
                    accept=".docx" 
                    onChange={handleProcessTemplate} 
                    disabled={processing} 
                    className="hidden" 
                  />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Select Template to Process
                    </label>
                    <div className="flex items-center space-x-3">
                      <Button 
                        onClick={() => processInputRef.current?.click()} 
                        disabled={processing}
                        className="flex items-center space-x-2"
                      >
                        {processing ? (
                          <FiLoader className="h-4 w-4 animate-spin" />
                        ) : (
                          <FiUpload className="h-4 w-4" />
                        )}
                        <span>{processing ? 'Processing...' : 'Choose & Process'}</span>
                      </Button>
                      <Badge variant="secondary" className="text-xs">
                        Auto-fill on upload
                      </Badge>
                    </div>
                  </div>

                  <AnimatePresence>
                    {processing && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="flex items-center space-x-3 p-4 bg-green-50 rounded-lg border border-green-200"
                      >
                        <FiLoader className="h-5 w-5 text-green-600 animate-spin" />
                        <span className="text-sm text-green-800 font-medium">Processing template...</span>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <AnimatePresence>
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="p-4 bg-red-50 border border-red-200 rounded-lg"
                      >
                        <div className="flex items-center space-x-2">
                          <FiXCircle className="h-5 w-5 text-red-500" />
                          <span className="text-sm text-red-700 font-medium">{error}</span>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <AnimatePresence>
                    {success && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="p-4 bg-green-50 border border-green-200 rounded-lg"
                      >
                        <div className="flex items-center space-x-2 mb-3">
                          <FiCheckCircle className="h-5 w-5 text-green-500" />
                          <span className="text-sm text-green-700 font-medium">{success}</span>
                        </div>
                        {downloadUrl && (
                          <Button 
                            onClick={downloadTemplate} 
                            size="sm"
                            className="flex items-center space-x-2"
                          >
                            <FiDownload className="h-4 w-4" />
                            <span>Download Filled Template</span>
                          </Button>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Progress Panel */}
              <AnimatePresence>
                {processing && (
                  <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border border-green-200"
                  >
                    <div className="space-y-6">
                      <div className="text-center">
                        <h4 className="font-semibold text-green-900 mb-2">Processing Progress</h4>
                        <div className="flex items-center justify-center space-x-2 text-green-700">
                          <FiLoader className="h-5 w-5 animate-spin" />
                          <span className="text-sm font-medium">{Math.round(progress)}% Complete</span>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <Progress 
                          value={progress} 
                          max={100} 
                          variant="gradient"
                          className="h-2"
                        />
                        
                        <div className="p-3 bg-white/70 rounded-lg border border-green-200">
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            <span className="text-sm text-green-800 font-medium">{progressStage}</span>
                          </div>
                        </div>

                        {estimatedTime > 0 && (
                          <div className="text-center">
                            <div className="text-sm text-green-700">
                              <span className="font-medium">Time remaining: </span>
                              {estimatedTime > 60 ? `${Math.floor(estimatedTime / 60)}m ${estimatedTime % 60}s` : `${estimatedTime}s`}
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-1 gap-2 text-xs">
                          {[
                            { label: 'Template Analysis', threshold: 30 },
                            { label: 'Knowledge Search', threshold: 60 },
                            { label: 'Content Generation', threshold: 85 }
                          ].map((stage, index) => (
                            <div key={index} className="flex items-center justify-between p-2 bg-white/50 rounded">
                              <span className="text-green-800">{stage.label}</span>
                              {progress >= stage.threshold ? (
                                <FiCheckCircle className="h-4 w-4 text-green-600" />
                              ) : (
                                <div className="w-4 h-4 border-2 border-green-200 rounded-full"></div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* CSV Analysis Section */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <FiBarChart className="h-5 w-5 text-orange-600" />
              </div>
              <span>Analyze CSV</span>
            </CardTitle>
            <CardDescription>
              Upload a CSV file to see which empty cells can be filled with the available documents for Device {deviceId}. 
              <strong className="text-orange-600"> Note:</strong> This only analyzes the file - use &quot;Process CSV&quot; below to actually fill the cells.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <Input 
                ref={csvAnalyzeInputRef} 
                type="file" 
                accept=".csv" 
                onChange={handleAnalyzeCsv} 
                disabled={analyzingCsv} 
                className="hidden" 
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select CSV File to Analyze
                </label>
                <div className="flex items-center space-x-3">
                  <Button 
                    onClick={() => csvAnalyzeInputRef.current?.click()} 
                    disabled={analyzingCsv}
                    variant="outline"
                    className="flex items-center space-x-2"
                  >
                    {analyzingCsv ? (
                      <FiLoader className="h-4 w-4 animate-spin" />
                    ) : (
                      <FiUpload className="h-4 w-4" />
                    )}
                    <span>{analyzingCsv ? 'Analyzing...' : 'Choose File'}</span>
                  </Button>
                  <Badge variant="secondary" className="text-xs">
                    Analysis only - no file changes
                  </Badge>
                </div>
              </div>
              
              <AnimatePresence>
                {csvError && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-4 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-2">
                      <FiXCircle className="h-5 w-5 text-red-500" />
                      <span className="text-sm text-red-700">{csvError}</span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              
              <AnimatePresence>
                {csvAnalysis && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-6"
                  >
                    <div className="flex items-center space-x-3 mb-4">
                      <FiCheckCircle className="h-6 w-6 text-green-600" />
                      <h4 className="text-lg font-semibold text-green-800">CSV Analysis Results</h4>
                    </div>
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div className="bg-white/70 rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-700">File</div>
                          <div className="text-green-800 font-semibold truncate">{csvAnalysis.csv_filename}</div>
                        </div>
                        <div className="bg-white/70 rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-700">Rows</div>
                          <div className="text-green-800 font-semibold">{csvAnalysis.summary.total_rows}</div>
                        </div>
                        <div className="bg-white/70 rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-700">Columns</div>
                          <div className="text-green-800 font-semibold">{csvAnalysis.summary.total_columns}</div>
                        </div>
                        <div className="bg-white/70 rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-700">Empty Cells</div>
                          <div className="text-green-800 font-semibold">{csvAnalysis.summary.total_empty_cells}</div>
                        </div>
                      </div>
                      
                      <div className="bg-white/70 rounded-xl p-4 border border-green-200">
                        <div className="flex justify-between items-center mb-3">
                          <span className="font-semibold text-gray-800">Fillability Analysis</span>
                          <Badge variant="success" className="text-sm">
                            {csvAnalysis.summary.fillable_cells}/{csvAnalysis.summary.total_empty_cells} cells
                          </Badge>
                        </div>
                        <Progress 
                          value={csvAnalysis.summary.total_empty_cells > 0 ? (csvAnalysis.summary.fillable_cells / csvAnalysis.summary.total_empty_cells) * 100 : 0}
                          max={100}
                          variant="gradient"
                          className="h-3 mb-2"
                        />
                        <p className="text-sm text-gray-700">
                          {csvAnalysis.summary.total_empty_cells > 0 ? Math.round((csvAnalysis.summary.fillable_cells / csvAnalysis.summary.total_empty_cells) * 100) : 0}% of empty cells can be filled
                        </p>
                      </div>
                      
                      {csvAnalysis.column_analysis && Object.keys(csvAnalysis.column_analysis).length > 0 && (
                        <div className="space-y-3">
                          <h5 className="font-semibold text-gray-800 flex items-center space-x-2">
                            <FiDatabase className="h-5 w-5" />
                            <span>Column Analysis</span>
                          </h5>
                          <div className="space-y-2">
                            {Object.entries(csvAnalysis.column_analysis).map(([column, data], index) => (
                              <motion.div
                                key={column}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="flex items-center justify-between p-3 bg-white rounded-lg border border-green-200 hover:border-green-300 transition-all duration-200"
                              >
                                <div className="flex items-center space-x-3">
                                  <div className={`w-3 h-3 rounded-full ${data.fill_rate > 0 ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                  <span className="font-medium text-gray-900">{column}</span>
                                  <Badge variant={data.fill_rate > 0 ? 'success' : 'destructive'}>
                                    {data.fill_rate > 0 ? 'Fillable' : 'Cannot Fill'}
                                  </Badge>
                                </div>
                                {data.fill_rate > 0 && (
                                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                                    <span>{Math.round(data.fill_rate * 100)}% fill rate</span>
                                    <span>{Math.round(data.average_confidence * 100)}% confidence</span>
                                    <span>{data.empty_cells_in_column} empty cells</span>
                                  </div>
                                )}
                              </motion.div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {csvAnalysis.recommendations && (
                        <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
                          <h5 className="font-semibold text-blue-900 mb-3 flex items-center space-x-2">
                            <FiTarget className="h-5 w-5" />
                            <span>Recommendations</span>
                          </h5>
                          <div className="space-y-2 text-sm">
                            <div className="flex items-center space-x-2">
                              <FiCheckCircle className="h-4 w-4 text-green-600" />
                              <span className="font-medium text-blue-900">High fillability:</span>
                              <span className="text-blue-800">{csvAnalysis.recommendations.high_fill_rate_columns.join(', ') || 'None'}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <FiXCircle className="h-4 w-4 text-red-600" />
                              <span className="font-medium text-blue-900">Low fillability:</span>
                              <span className="text-blue-800">{csvAnalysis.recommendations.low_fill_rate_columns.join(', ') || 'None'}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <FiDatabase className="h-4 w-4 text-blue-600" />
                              <span className="font-medium text-blue-900">Processable columns:</span>
                              <span className="text-blue-800">{csvAnalysis.recommendations.total_processable} out of {csvAnalysis.summary.columns_with_empty_cells}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* CSV Processing Section */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <FiDatabase className="h-5 w-5 text-purple-600" />
              </div>
              <span>Process CSV</span>
            </CardTitle>
            <CardDescription>
              Upload a CSV file to automatically fill missing values with information from Device {deviceId}&apos;s documents. 
              <strong className="text-purple-600"> This creates a new filled CSV file that you can download.</strong>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <Input 
                ref={csvInputRef} 
                type="file" 
                accept=".csv" 
                onChange={handleProcessCsv} 
                disabled={processingCsv} 
                className="hidden" 
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select CSV File to Process
                </label>
                <div className="flex items-center space-x-3">
                  <Button 
                    onClick={() => csvInputRef.current?.click()} 
                    disabled={processingCsv}
                    className="flex items-center space-x-2"
                  >
                    {processingCsv ? (
                      <FiLoader className="h-4 w-4 animate-spin" />
                    ) : (
                      <FiUpload className="h-4 w-4" />
                    )}
                    <span>{processingCsv ? 'Processing...' : 'Choose & Process'}</span>
                  </Button>
                  <Badge variant="secondary" className="text-xs">
                    Creates filled CSV file
                  </Badge>
                </div>
              </div>
              
              <AnimatePresence>
                {csvError && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-4 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-2">
                      <FiXCircle className="h-5 w-5 text-red-500" />
                      <span className="text-sm text-red-700">{csvError}</span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              
              <AnimatePresence>
                {csvSuccess && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-4 bg-green-50 border border-green-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-2 mb-3">
                      <FiCheckCircle className="h-5 w-5 text-green-500" />
                      <span className="text-sm text-green-700 font-medium">{csvSuccess}</span>
                    </div>
                    {csvDownloadUrl && (
                      <Button 
                        onClick={downloadCsv}
                        size="sm"
                        className="flex items-center space-x-2"
                      >
                        <FiDownload className="h-4 w-4" />
                        <span>Download Filled CSV</span>
                      </Button>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
              
              <AnimatePresence>
                {processingCsv && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="flex items-center space-x-3 p-4 bg-purple-50 rounded-lg border border-purple-200"
                  >
                    <FiLoader className="h-5 w-5 text-purple-600 animate-spin" />
                    <span className="text-sm text-purple-800 font-medium">Processing CSV...</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Document Reverse Processing Section */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-indigo-100 rounded-lg">
                <FiRefreshCw className="h-5 w-5 text-indigo-600" />
              </div>
              <span>Create Blank Template</span>
            </CardTitle>
            <CardDescription>
              Upload a <strong>filled document</strong> (PDF or Word) to automatically create a blank template. 
              PDFs will be processed using OCR and converted to Word format. Answers will be removed and replaced with blank fields.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <Input 
                ref={reverseInputRef} 
                type="file" 
                accept=".pdf,.docx,.doc" 
                onChange={handleReverseProcessing} 
                disabled={reverseProcessing} 
                className="hidden" 
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select Filled Document to Convert
                </label>
                <div className="flex items-center space-x-3">
                  <Button 
                    onClick={() => reverseInputRef.current?.click()} 
                    disabled={reverseProcessing}
                    variant="outline"
                    className="flex items-center space-x-2"
                  >
                    {reverseProcessing ? (
                      <FiLoader className="h-4 w-4 animate-spin" />
                    ) : (
                      <FiUpload className="h-4 w-4" />
                    )}
                    <span>{reverseProcessing ? 'Processing...' : 'Choose Filled Document'}</span>
                  </Button>
                  <Badge variant="secondary" className="text-xs">
                    PDF, Word (.docx, .doc)
                  </Badge>
                </div>
              </div>
              
              <AnimatePresence>
                {reverseError && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-4 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-2">
                      <FiXCircle className="h-5 w-5 text-red-500" />
                      <span className="text-sm text-red-700">{reverseError}</span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              
              <AnimatePresence>
                {reverseSuccess && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-4 bg-green-50 border border-green-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-2 mb-3">
                      <FiCheckCircle className="h-5 w-5 text-green-500" />
                      <span className="text-sm text-green-700 font-medium">{reverseSuccess}</span>
                    </div>
                    {reverseDownloadUrl && (
                      <Button 
                        onClick={downloadBlankTemplate}
                        size="sm"
                        className="flex items-center space-x-2"
                      >
                        <FiDownload className="h-4 w-4" />
                        <span>Download Blank Template</span>
                      </Button>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
              
              <AnimatePresence>
                {reverseProcessing && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="flex items-center space-x-3 p-4 bg-indigo-50 rounded-lg border border-indigo-200"
                  >
                    <FiLoader className="h-5 w-5 text-indigo-600 animate-spin" />
                    <span className="text-sm text-indigo-800 font-medium">
                      Creating blank template...
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Feature Details */}
              <div className="bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl p-4 border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center space-x-2">
                  <FiSettings className="h-4 w-4" />
                  <span>How it works</span>
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-gray-700">
                  <div className="space-y-2">
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5"></div>
                      <div>
                        <strong>PDF files:</strong> Uses advanced OCR to extract text, then creates blank template in Word format
                      </div>
                    </div>
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
                      <div>
                        <strong>Word files:</strong> Analyzes content and removes answers while preserving question structure
                      </div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mt-1.5"></div>
                      <div>
                        <strong>Smart detection:</strong> Automatically identifies form fields, labels, and answers
                      </div>
                    </div>
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5"></div>
                      <div>
                        <strong>Word output:</strong> All blank templates are saved as editable Word documents
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Instructions */}
      <motion.div variants={itemVariants}>
        <Card variant="glass" className="border-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3 text-blue-900">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <FiFileText className="h-5 w-5 text-blue-600" />
              </div>
              <span>How to Use Templates, CSV Processing & Document Reverse</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* RAG Filling Modes */}
            <div className="bg-white/70 rounded-xl p-4 border border-white/50">
              <div className="flex items-center space-x-3 mb-3">
                <FiSettings className="h-5 w-5 text-blue-600" />
                <h4 className="font-semibold text-blue-900">RAG Filling Modes</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="flex items-start space-x-3">
                  <FiZap className="h-5 w-5 text-blue-500 mt-0.5" />
                  <div>
                    <p className="font-medium text-blue-800 mb-1">General Mode</p>
                    <p className="text-gray-700">Provides accurate data with descriptive context for better readability. Best for most documents.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <FiTarget className="h-5 w-5 text-purple-500 mt-0.5" />
                  <div>
                    <p className="font-medium text-purple-800 mb-1">Accurate Mode</p>
                    <p className="text-gray-700">Uses only exact values from knowledge base without interpretation. Ideal for regulatory forms and sensitive documents.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Template Processing */}
            <div className="bg-white/70 rounded-xl p-4 border border-white/50">
              <div className="flex items-center space-x-3 mb-3">
                <FiFileText className="h-5 w-5 text-green-600" />
                <h4 className="font-semibold text-green-900">Template Processing</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="bg-green-100 text-green-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">1</span>
                    <strong>Create Template:</strong> Use Word to create a .docx template with placeholders like {`{name}`}, {`{date}`}, {`{amount}`}, etc.
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-green-100 text-green-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">2</span>
                    <strong>Analyze First:</strong> Use the analyze function to see which fields can be filled with your uploaded documents.
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="bg-green-100 text-green-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">3</span>
                    <strong>Process Template:</strong> Upload your template to automatically fill placeholders with relevant information.
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-green-100 text-green-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">4</span>
                    <strong>Download Result:</strong> Get your filled template ready for use.
                  </div>
                </div>
              </div>
            </div>

            {/* CSV Processing */}
            <div className="bg-white/70 rounded-xl p-4 border border-white/50">
              <div className="flex items-center space-x-3 mb-3">
                <FiDatabase className="h-5 w-5 text-purple-600" />
                <h4 className="font-semibold text-purple-900">CSV Processing</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="bg-purple-100 text-purple-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">1</span>
                    <strong>Prepare CSV:</strong> Create a CSV file with headers and some empty cells that need to be filled.
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-purple-100 text-purple-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">2</span>
                    <strong>Analyze First (Optional):</strong> Use &quot;Analyze CSV&quot; to see which empty cells can be filled without creating a file.
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="bg-purple-100 text-purple-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">3</span>
                    <strong>Process CSV:</strong> Use &quot;Process CSV&quot; to actually fill empty cells and create a new downloadable file.
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-purple-100 text-purple-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">4</span>
                    <strong>Download Enhanced CSV:</strong> Get your completed CSV with all available fields filled from the file history.
                  </div>
                </div>
              </div>
            </div>

            {/* Document Reverse */}
            <div className="bg-white/70 rounded-xl p-4 border border-white/50">
              <div className="flex items-center space-x-3 mb-3">
                <FiRefreshCw className="h-5 w-5 text-indigo-600" />
                <h4 className="font-semibold text-indigo-900">Create Blank Template</h4>
                <Badge variant="outline" className="text-xs">NEW</Badge>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="bg-indigo-100 text-indigo-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">1</span>
                    <strong>Upload Filled Document:</strong> Upload a PDF or Word document that already has answers filled in.
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-indigo-100 text-indigo-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">2</span>
                    <strong>Automatic Processing:</strong> The system will use OCR (for PDFs) or direct text extraction (for Word) to analyze the content.
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="bg-indigo-100 text-indigo-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">3</span>
                    <strong>Smart Field Detection:</strong> Automatically identifies questions and answers, then removes answers while keeping questions.
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-indigo-100 text-indigo-800 rounded-full w-5 h-5 text-xs flex items-center justify-center font-medium">4</span>
                    <strong>Download Blank Template:</strong> Get a clean Word document template ready for reuse with blank fields for answers.
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
