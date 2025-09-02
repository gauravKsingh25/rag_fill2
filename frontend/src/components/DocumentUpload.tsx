'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FiUpload, 
  FiX, 
  FiLoader, 
  FiFile, 
  FiRefreshCw,
  FiDatabase,
  FiCheckCircle,
  FiAlertCircle,
  FiTrash2,
  FiClock
} from 'react-icons/fi';
import { documentApi, ApiError } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface DocumentUploadProps {
  deviceId: string;
}

interface Document {
  document_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  upload_timestamp: string;
  processed: boolean;
  chunk_count: number;
}

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4 }
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: { duration: 0.3 }
  }
};

export default function DocumentUpload({ deviceId }: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
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
    setUploadProgress(0);

    try {
      const result = await documentApi.upload(file, deviceId, (progress) => {
        setUploadProgress(progress);
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
      setUploadProgress(0);
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

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="w-full space-y-6"
    >
      {/* Upload Section */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <FiUpload className="h-5 w-5 text-blue-600" />
              </div>
              <span>Document Upload</span>
              {documents.length > 0 && (
                <Badge variant="secondary">
                  {documents.length} document{documents.length !== 1 ? 's' : ''}
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Upload documents to device <strong>{deviceId}</strong> for intelligent processing and vector indexing. 
              Supported formats: PDF, DOCX, TXT, MD, CSV (max 10MB)
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            <div className="space-y-6">
              {/* File Upload Area */}
              <div className="relative group">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md,.csv"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
                />
                <motion.div 
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                    uploading 
                      ? 'border-blue-300 bg-blue-50' 
                      : 'border-gray-300 bg-gray-50 group-hover:border-blue-400 group-hover:bg-blue-50'
                  }`}
                >
                  <div className="flex flex-col items-center gap-4">
                    <motion.div
                      animate={uploading ? { rotate: 360 } : {}}
                      transition={{ duration: 1, repeat: uploading ? Infinity : 0, ease: "linear" }}
                    >
                      {uploading ? (
                        <FiLoader className="w-8 h-8 text-blue-500" />
                      ) : (
                        <FiUpload className="w-8 h-8 text-gray-400 group-hover:text-blue-500 transition-colors" />
                      )}
                    </motion.div>
                    <div>
                      <div className="font-medium text-gray-700">
                        {uploading ? 'Processing document...' : 'Click to upload or drag and drop'}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        PDF, DOCX, TXT, MD, CSV files supported (max 10MB)
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>

              {/* Upload Progress */}
              <AnimatePresence>
                {uploading && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="p-4 bg-blue-50 border border-blue-200 rounded-lg"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <FiLoader className="w-4 h-4 text-blue-500 animate-spin" />
                      <span className="text-sm font-medium text-gray-700">
                        Uploading {selectedFileName}...
                      </span>
                      <span className="text-sm text-gray-500 ml-auto">
                        {uploadProgress}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <motion.div
                        className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${uploadProgress}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Messages */}
              <AnimatePresence>
                {(error || success) && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className={`p-4 rounded-lg border ${
                      error 
                        ? 'bg-red-50 border-red-200 text-red-800' 
                        : 'bg-green-50 border-green-200 text-green-800'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {error ? (
                        <FiAlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      ) : (
                        <FiCheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="font-medium">{error || success}</div>
                      </div>
                      <button
                        onClick={clearMessages}
                        className="text-current hover:opacity-70 transition-opacity"
                      >
                        <FiX className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Documents Library */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center space-x-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <FiDatabase className="h-5 w-5 text-green-600" />
                  </div>
                  <span>Document Library</span>
                </CardTitle>
                <CardDescription>
                  {documents.length} document{documents.length !== 1 ? 's' : ''} in knowledge base
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                onClick={fetchDocuments}
                disabled={loading}
                className="h-9 w-9 p-0"
                title="Refresh documents"
              >
                <FiRefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </CardHeader>
          
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="flex items-center gap-3 text-gray-500">
                  <FiLoader className="w-5 h-5 animate-spin" />
                  <span>Loading documents...</span>
                </div>
              </div>
            ) : documents.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-12"
              >
                <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <FiFile className="w-8 h-8 text-gray-400" />
                </div>
                <h4 className="text-lg font-semibold text-gray-700 mb-2">No documents yet</h4>
                <p className="text-gray-500">Upload your first document to get started</p>
              </motion.div>
            ) : (
              <div className="space-y-4">
                <AnimatePresence mode="popLayout">
                  {documents.map((doc) => (
                    <motion.div
                      key={doc.document_id}
                      variants={itemVariants}
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      layout
                      className="group relative"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 rounded-xl opacity-0 group-hover:opacity-100 transition-all duration-300" />
                      
                      <div className="relative p-5 bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-xl hover:shadow-lg hover:border-gray-300/50 transition-all duration-300">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4 flex-1 min-w-0">
                            {/* Status Icon */}
                            <div className="flex-shrink-0">
                              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                                doc.processed ? 'bg-green-100 border border-green-200' : 'bg-yellow-100 border border-yellow-200'
                              }`}>
                                {doc.processed ? (
                                  <FiCheckCircle className="w-6 h-6 text-green-600" />
                                ) : (
                                  <FiClock className="w-6 h-6 text-yellow-600" />
                                )}
                              </div>
                            </div>

                            {/* Document Info */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-3 mb-2">
                                <h4 className="text-sm font-semibold text-gray-900 truncate" title={doc.filename}>
                                  {doc.filename}
                                </h4>
                                <Badge variant={doc.processed ? "success" : "warning"}>
                                  {doc.processed ? 'Processed' : 'Processing'}
                                </Badge>
                              </div>
                              
                              <div className="flex items-center space-x-4 text-xs text-gray-500">
                                <span>{formatFileSize(doc.file_size)}</span>
                                <span className="px-2 py-1 bg-gray-100 rounded-md font-medium uppercase">
                                  {doc.file_type}
                                </span>
                                <span>{doc.chunk_count} chunks</span>
                                <span className="flex items-center space-x-1">
                                  <FiClock className="h-3 w-3" />
                                  <span>{formatTimestamp(doc.upload_timestamp)}</span>
                                </span>
                              </div>
                            </div>
                          </div>
                          
                          {/* Actions */}
                          <div className="flex items-center space-x-2 ml-4">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteDocument(doc.document_id)}
                              className="h-9 w-9 p-0 hover:bg-red-50 hover:text-red-600"
                              title="Delete document"
                            >
                              <FiTrash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
