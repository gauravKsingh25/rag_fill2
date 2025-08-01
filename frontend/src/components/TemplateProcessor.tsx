'use client';

import { useState, useRef } from 'react';

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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const processInputRef = useRef<HTMLInputElement>(null);

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

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('device_id', deviceId);

      const response = await fetch('http://localhost:8000/api/templates/upload-and-fill', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Processing failed');
      }

      const result = await response.json();
      setSuccess(`Template processed successfully! Filled ${Object.keys(result.filled_fields).length} fields.`);
      setDownloadUrl(`http://localhost:8000${result.filled_template_url}`);
      
      // Clear file input
      if (processInputRef.current) {
        processInputRef.current.value = '';
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
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
                        Confidence: {(details.confidence * 100).toFixed(1)}% 
                        ({details.sources} sources)
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
