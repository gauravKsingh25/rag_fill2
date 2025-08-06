'use client';

import { useState, useRef, useEffect } from 'react';

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

interface TemplateProcessorProps {
  deviceId: string;
}

export default function TemplateProcessor({ deviceId }: TemplateProcessorProps) {
  const [processing, setProcessing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<TemplateAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressStage, setProgressStage] = useState('');
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const processInputRef = useRef<HTMLInputElement>(null);
  const activeIntervalsRef = useRef<NodeJS.Timeout[]>([]);

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

  const handleAnalyzeTemplate = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
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

      const response = await fetch('http://localhost:8000/api/templates/analyze', {
        method: 'POST',
        body: formData,
      });

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
  };

  const handleProcessTemplate = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
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

      // Manual progress updates for real API interaction
      setProgress(5);
      setProgressStage('Uploading template...');

      // Start the fetch request
      const response = await fetch('http://localhost:8000/api/templates/upload-and-fill', {
        method: 'POST',
        body: formData,
      });

      setProgress(15);
      setProgressStage('Template uploaded, analyzing...');

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Processing failed');
      }

      // Let the simulated progress continue running while we wait for response
      // The useEffect will handle the detailed progress stages from 15% to 92%
      // We just set the final real stages here

      const result = await response.json();
      
      // Override the simulation at the end with real completion
      setProgress(100);
      setProgressStage('Template processing completed!');
      setSuccess(`Template processed successfully! Filled ${Object.keys(result.filled_fields).length} fields.`);
      setDownloadUrl(`http://localhost:8000${result.filled_template_url}`);
      
      // Clear file input
      if (processInputRef.current) {
        processInputRef.current.value = '';
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
      setProgress(0);
      setProgressStage('');
    } finally {
      setProcessing(false);
    }
  };

  const downloadTemplate = () => {
    if (downloadUrl) {
      window.open(downloadUrl, '_blank');
    }
  };

  return (
    <div className="space-y-6">
      {/* Template Analysis Section */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Analyze Template
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Upload a template to see which fields can be filled with the available documents for Device {deviceId}.
        </p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Template to Analyze
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx"
              onChange={handleAnalyzeTemplate}
              disabled={analyzing}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
            />
            <p className="text-xs text-gray-500 mt-1">
              Only .docx files are supported for template analysis
            </p>
          </div>

          {analyzing && (
            <div className="flex items-center space-x-2 text-blue-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-sm">Analyzing template...</span>
            </div>
          )}
        </div>
      </div>

      {/* Analysis Results */}
      {analysis && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Analysis Results
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-blue-600">{analysis.total_fields}</div>
              <div className="text-sm text-blue-800">Total Fields</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-green-600">{analysis.fillable_fields}</div>
              <div className="text-sm text-green-800">Fillable Fields</div>
            </div>
            <div className="bg-red-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-red-600">
                {analysis.total_fields - analysis.fillable_fields}
              </div>
              <div className="text-sm text-red-800">Missing Fields</div>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium text-gray-900">Field Details:</h4>
            <div className="space-y-2">
              {Object.entries(analysis.field_analysis).map(([field, details]) => (
                <div key={field} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      details.can_fill ? 'bg-green-500' : 'bg-red-500'
                    }`}></div>
                    <span className="font-medium">{field}</span>
                  </div>
                  <div className="text-sm text-gray-600">
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
          {/* Main Processing Content */}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Process Template
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Upload a template to automatically fill it with information from Device {deviceId}&apos;s documents.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Template to Process
                </label>
                <input
                  ref={processInputRef}
                  type="file"
                  accept=".docx"
                  onChange={handleProcessTemplate}
                  disabled={processing}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100 disabled:opacity-50"
                />
                <p className="text-xs text-gray-500 mt-1">
                  The template will be processed and placeholders filled automatically
                </p>
              </div>

              {processing && (
                <div className="flex items-center space-x-2 text-green-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></div>
                  <span className="text-sm">Processing template...</span>
                </div>
              )}

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <div className="text-red-700 text-sm">{error}</div>
                </div>
              )}

              {success && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                  <div className="text-green-700 text-sm">{success}</div>
                  {downloadUrl && (
                    <button
                      onClick={downloadTemplate}
                      className="mt-2 px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                    >
                      Download Filled Template
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Progress Indicator */}
          {processing && (
            <div className="w-80 bg-gray-50 rounded-lg p-4 border-l-4 border-green-500">
              <h4 className="font-semibold text-gray-900 mb-3 text-center">
                Processing Progress
              </h4>
              
              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between text-sm text-gray-600 mb-1">
                  <span>Progress</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className="bg-gradient-to-r from-green-500 to-green-600 h-3 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>

              {/* Current Stage */}
              <div className="mb-4">
                <div className="text-sm font-medium text-gray-700 mb-1">
                  Current Stage:
                </div>
                <div className="text-sm text-gray-600 flex items-center">
                  <div className="animate-pulse w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  {progressStage}
                </div>
              </div>

              {/* Estimated Time */}
              {estimatedTime > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-gray-700 mb-1">
                    Estimated Time Remaining:
                  </div>
                  <div className="text-sm text-gray-600">
                    {estimatedTime > 60 
                      ? `${Math.floor(estimatedTime / 60)}m ${estimatedTime % 60}s`
                      : `${estimatedTime}s`
                    }
                  </div>
                </div>
              )}

              {/* Progress Stats */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Template Analysis</span>
                  <span>{progress >= 30 ? '✓' : '○'}</span>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Knowledge Search</span>
                  <span>{progress >= 60 ? '✓' : '○'}</span>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Content Generation</span>
                  <span>{progress >= 85 ? '✓' : '○'}</span>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Document Assembly</span>
                  <span>{progress >= 95 ? '✓' : '○'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          How to Use Templates
        </h3>
        <div className="text-sm text-blue-800 space-y-2">
          <p><strong>1. Create Template:</strong> Use Word to create a .docx template with placeholders like {`{name}`}, {`{date}`}, {`{amount}`}, etc.</p>
          <p><strong>2. Analyze First:</strong> Use the analyze function to see which fields can be filled with your uploaded documents.</p>
          <p><strong>3. Process Template:</strong> Upload your template to automatically fill placeholders with relevant information.</p>
          <p><strong>4. Download Result:</strong> Get your filled template ready for use.</p>
        </div>
      </div>
    </div>
  );
}
