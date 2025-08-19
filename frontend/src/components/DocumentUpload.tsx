'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { documentApi, ApiError } from '@/lib/api';

interface Document {
  document_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  upload_timestamp: string;
  chunk_count: number;
  processed: boolean;
}

interface DocumentUploadProps {
  deviceId: string;
}

export default function DocumentUpload({ deviceId }: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = useCallback(async () => {
    if (!deviceId) return;
    
    setLoading(true);
    try {
      const data = await documentApi.listByDevice(deviceId);
      setDocuments(data.documents || []);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to fetch documents');
      }
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchDocuments();
  }, [deviceId, fetchDocuments]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFileName(file.name);

    // Validate file type
    const allowedTypes = ['.pdf', '.docx', '.txt', '.md', '.csv'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!allowedTypes.includes(fileExtension)) {
      setError(`File type not supported. Allowed types: ${allowedTypes.join(', ')}`);
      return;
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setError('File too large. Maximum size: 10MB');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await documentApi.upload(file, deviceId, (progress) => {
        // You can use progress for a progress bar if needed
        console.log(`Upload progress: ${progress}%`);
      });

      // Extract chunks created from the message or use 0 as fallback
      const chunksCreated = result.message.match(/Created (\d+) chunks/)?.[1] || '0';
      setSuccess(`Document "${result.filename}" uploaded and processed successfully! Created ${chunksCreated} chunks.`);
      
      // Refresh document list
      await fetchDocuments();
      
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
        setSelectedFileName(null);
      }
      
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : 'Upload failed');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return;
    }

    try {
      await documentApi.delete(documentId);
      setSuccess('Document deleted successfully');
      await fetchDocuments();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to delete document');
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Upload Documents to Device {deviceId}
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
               Select Document
             </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md,.csv"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
            <div className="flex items-center gap-3">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="btn-primary"
              >
                {uploading ? 'Uploading...' : 'Choose file'}
              </button>
               <div className="text-sm text-gray-600">
                 {selectedFileName ? <span className="font-medium">{selectedFileName}</span> : <span className="italic text-gray-400">No file selected</span>}
               </div>
              {selectedFileName && (
                <button
                  onClick={() => { if (fileInputRef.current) fileInputRef.current.value = ''; setSelectedFileName(null); }}
                  className="text-sm text-red-500 hover:underline"
                >
                  Clear
                </button>
              )}
            </div>
              <p className="text-xs text-gray-500 mt-1">
                Supported formats: PDF, DOCX, TXT, MD, CSV (max 10MB)
              </p>
            </div>

          {uploading && (
            <div className="flex items-center space-x-2 text-blue-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-sm">Processing document...</span>
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
            </div>
          )}
        </div>
      </div>

      {/* Documents List */}
      <div className="card">
        <div className="px-6 py-4 border-b">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900">
              Uploaded Documents
            </h3>
            <button
              onClick={fetchDocuments}
              disabled={loading}
              className="btn-ghost"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {documents.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <div className="text-gray-400 mb-2">
                <svg className="mx-auto h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-gray-600">No documents uploaded yet</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.document_id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        <div className={`w-2 h-2 rounded-full ${doc.processed ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">{doc.filename}</h4>
                        <div className="text-xs text-gray-500 space-x-4">
                          <span>{formatFileSize(doc.file_size)}</span>
                          <span>{doc.file_type.toUpperCase()}</span>
                          <span>{doc.chunk_count} chunks</span>
                          <span>{formatTimestamp(doc.upload_timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      doc.processed 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {doc.processed ? 'Processed' : 'Processing'}
                    </span>
                    <button
                      onClick={() => handleDeleteDocument(doc.document_id)}
                      className="text-sm text-red-600 hover:text-red-800 btn-ghost"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
