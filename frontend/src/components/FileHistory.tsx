'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiDownload, FiTrash2, FiClock, FiAlertCircle, FiFile, FiCheckCircle, FiXCircle, FiLoader, FiDatabase } from 'react-icons/fi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export interface FileHistoryItem {
  filename: string;
  type: 'analyzed' | 'filled';
  url: string;
  timestamp: string;
  content_type?: string | null;
  size_bytes?: number | null;
}

interface FileHistoryProps {
  history: FileHistoryItem[];
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

export default function FileHistory({ history }: FileHistoryProps) {
  const [remoteHistory, setRemoteHistory] = useState<FileHistoryItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
  const [apiBaseError, setApiBaseError] = useState<string | null>(null);

  const loadFileHistory = useCallback(async () => {
    if (!API_BASE || API_BASE.trim() === '') {
      setApiBaseError('API base URL is not configured. Please set NEXT_PUBLIC_API_BASE in your environment.');
      setLoading(false);
      return;
    }
    setApiBaseError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/file-history/`);
      const items = res.ok ? await res.json() : [];
      setRemoteHistory(items as FileHistoryItem[]);
    } catch (e) {
      setRemoteHistory([]);
      console.error('Failed to load file history', e);
    } finally {
      setLoading(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    loadFileHistory();
  }, [loadFileHistory]);

  const deleteHistoryItem = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}" from file history?`)) {
      return;
    }

    setIsDeleting(filename);

    try {
      const res = await fetch(`${API_BASE}/api/file-history/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || `Delete failed (${res.status})`);
      }

      // Remove from local state
      setRemoteHistory(prev => prev ? prev.filter(item => item.filename !== filename) : []);
      setError(null);
    } catch (e) {
      setError((e as Error).message || 'Delete failed');
      console.error('Delete file history item failed', e);
    } finally {
      setIsDeleting(null);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getFileTypeIcon = (contentType: string | null | undefined, filename: string) => {
    if (contentType?.includes('pdf') || filename.toLowerCase().includes('.pdf')) {
      return '📄';
    } else if (contentType?.includes('doc') || filename.toLowerCase().includes('.doc')) {
      return '📝';
    } else if (contentType?.includes('csv') || filename.toLowerCase().includes('.csv')) {
      return '📊';
    }
    return '📁';
  };

  const getTypeBadge = (type: 'analyzed' | 'filled') => {
    if (type === 'filled') {
      return <Badge variant="success">Filled</Badge>;
    }
    return <Badge variant="secondary">Analyzed</Badge>;
  };

  const getTypeIcon = (type: 'analyzed' | 'filled') => {
    if (type === 'filled') {
      return <FiCheckCircle className="h-4 w-4 text-green-500" />;
    }
    return <FiDatabase className="h-4 w-4 text-blue-500" />;
  };

  const formatFileSize = (bytes: number | null | undefined) => {
    if (!bytes) return '';
    return `${Math.round(bytes / 1024)} KB`;
  };

  const combinedHistory = remoteHistory ?? history;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="w-full"
    >
      <Card className="backdrop-blur-lg bg-white/90 border-0 shadow-xl">
        <CardHeader className="border-b border-gray-100/50">
          <CardTitle className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-br from-purple-100 to-blue-100 rounded-lg">
              <FiClock className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                File History
              </h2>
              <p className="text-sm text-gray-500 font-normal mt-1">
                Recent analyzed & filled files • {combinedHistory?.length ?? 0} files
              </p>
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent className="p-6">
          {/* Error Display */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg"
              >
                <div className="flex items-center space-x-2">
                  <FiAlertCircle className="h-5 w-5 text-red-500" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* API Base Error */}
          {apiBaseError ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-12"
            >
              <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-red-100 to-red-200 rounded-2xl flex items-center justify-center">
                <FiXCircle className="h-10 w-10 text-red-500" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Configuration Error</h3>
              <p className="text-red-600 text-sm max-w-md mx-auto">{apiBaseError}</p>
            </motion.div>
          ) : (
            <>
              {/* Loading State */}
              {loading ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-12"
                >
                  <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl flex items-center justify-center">
                    <FiLoader className="h-10 w-10 text-blue-500 animate-spin" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Loading</h3>
                  <p className="text-blue-600 text-sm">Fetching file history...</p>
                </motion.div>
              ) : !combinedHistory || combinedHistory.length === 0 ? (
                /* Empty State */
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center py-12"
                >
                  <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center">
                    <FiFile className="h-10 w-10 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No files yet</h3>
                  <p className="text-gray-500 max-w-sm mx-auto">
                    Use the Upload or Template tools to generate history items. Processed files will appear here.
                  </p>
                </motion.div>
              ) : (
                /* File List */
                <div className="space-y-4">
                  <AnimatePresence mode="popLayout">
                    {combinedHistory.map((item) => {
                      const key = `${item.filename || 'file'}_${item.timestamp || ''}`;
                      const sizeDisplay = formatFileSize(item.size_bytes);
                      const displayTime = formatDate(item.timestamp || '');
                      
                      return (
                        <motion.div
                          key={key}
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
                              <div className="flex items-center space-x-4 flex-1 min-w-0">
                                {/* File Icon */}
                                <div className="flex-shrink-0">
                                  <div className="w-12 h-12 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg flex items-center justify-center text-xl border border-blue-100">
                                    {getFileTypeIcon(item.content_type, item.filename)}
                                  </div>
                                </div>

                                {/* File Info */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center space-x-3 mb-2">
                                    <h3 className="text-sm font-semibold text-gray-900 truncate" title={item.filename}>
                                      {item.filename}
                                    </h3>
                                    {getTypeIcon(item.type)}
                                    {getTypeBadge(item.type)}
                                  </div>
                                  
                                  <div className="flex items-center space-x-4 text-xs text-gray-500">
                                    <span className="flex items-center space-x-1">
                                      <FiClock className="h-3 w-3" />
                                      <span>{displayTime}</span>
                                    </span>
                                    
                                    {sizeDisplay && (
                                      <span className="px-2 py-1 bg-gray-100 rounded-md font-medium">
                                        {sizeDisplay}
                                      </span>
                                    )}
                                    
                                    {item.content_type && (
                                      <span className="px-2 py-1 bg-gray-100 rounded-md font-medium uppercase">
                                        {item.content_type.split('/')[1] || item.content_type}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              {/* Action Buttons */}
                              <div className="flex items-center space-x-2 ml-4">
                                <AnimatePresence>
                                  {item.url ? (
                                    <motion.div
                                      initial={{ opacity: 0, scale: 0.8 }}
                                      animate={{ opacity: 1, scale: 1 }}
                                      exit={{ opacity: 0, scale: 0.8 }}
                                    >
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        asChild
                                        className="h-9 w-9 p-0 hover:bg-blue-50 hover:text-blue-600"
                                        title={`Download ${item.filename}`}
                                      >
                                        <a href={item.url} download>
                                          <FiDownload className="h-4 w-4" />
                                        </a>
                                      </Button>
                                    </motion.div>
                                  ) : (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      disabled
                                      className="h-9 w-9 p-0 opacity-40"
                                      title="No file URL available"
                                    >
                                      <FiDownload className="h-4 w-4" />
                                    </Button>
                                  )}
                                </AnimatePresence>
                                
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => deleteHistoryItem(item.filename)}
                                  disabled={isDeleting === item.filename}
                                  className="h-9 w-9 p-0 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                                  title={`Delete ${item.filename}`}
                                >
                                  {isDeleting === item.filename ? (
                                    <FiLoader className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <FiTrash2 className="h-4 w-4" />
                                  )}
                                </Button>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
