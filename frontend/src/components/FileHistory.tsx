import { useState, useEffect } from 'react';
import { FiDownload } from 'react-icons/fi';
import { API_BASE_URL } from '@/config/api';

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

export default function FileHistory({ history }: FileHistoryProps) {
  const [remoteHistory, setRemoteHistory] = useState<FileHistoryItem[] | null>(null);
  const [loading, setLoading] = useState(false);

  const API_BASE = API_BASE_URL || 'https://rag-fill2-1.onrender.com';
  const [apiBaseError, setApiBaseError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    if (!API_BASE || API_BASE.trim() === '') {
      setApiBaseError('API base URL is not configured. Please set NEXT_PUBLIC_API_BASE in your environment.');
      setLoading(false);
      return;
    }
    setApiBaseError(null);
    setLoading(true);
    fetch(`${API_BASE}/api/file-history/`)
      .then(res => res.ok ? res.json() : [])
      .then(items => {
        if (mounted) setRemoteHistory(items as FileHistoryItem[]);
      })
      .catch(e => {
        if (mounted) setRemoteHistory([]);
        console.error('Failed to load file history', e);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [API_BASE]);

  const combinedHistory = remoteHistory ?? history;

  return (
    <div className="card p-6 file-history-card w-full">
      <div className="file-history-header mb-4">
        <div>
          <div className="text-lg font-semibold text-gray-900">File History</div>
          <div className="text-xs text-muted">Recent analyzed &amp; filled files · {combinedHistory?.length ?? 0}</div>
        </div>
      </div>
      {apiBaseError ? (
        <div className="text-red-600 text-sm text-center py-8">{apiBaseError}</div>
      ) : (
        <>
          <div className="space-y-3">
            {loading ? (
              <div className="text-blue-400 text-sm text-center py-8">Loading file history...</div>
            ) : !combinedHistory || combinedHistory.length === 0 ? (
              <div className="file-empty text-gray-400 text-sm text-center py-8">
                No file history yet. Use the Upload or Template tools to generate history items.
              </div>
            ) : (
              combinedHistory.map(item => {
                const key = `${item.filename || 'file'}_${item.timestamp || ''}`;
                const sizeKb = item.size_bytes ? `${Math.round((item.size_bytes || 0) / 1024)} KB` : null;
                const displayTime = item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Unknown';
                return (
                  <div key={key} className="file-item">
                    <div className="meta">
                      <div className="filename truncate" title={item.filename}>{item.filename}</div>
                      <div className="sub">
                        {displayTime}
                        {sizeKb ? ` · ${sizeKb}` : ''}
                        {item.content_type ? ` · ${item.content_type}` : ''}
                      </div>
                    </div>

                    <div className="actions flex items-center gap-3">
                      <div className={`badge ${item.type === 'filled' ? 'filled' : 'analyzed'}`}>
                        {item.type === 'filled' ? 'Filled' : 'Analyzed'}
                      </div>
                      {item.url ? (
                        <a href={item.url} download className="download-btn" title={`Download ${item.filename}`}>
                          <FiDownload className="h-4 w-4" />
                        </a>
                      ) : (
                        <button disabled className="download-btn opacity-40" title="No file URL available">
                          <FiDownload className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}
