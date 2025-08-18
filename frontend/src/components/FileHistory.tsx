import { useState, useEffect } from 'react';
import { FiDownload } from 'react-icons/fi';

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
  const [filter, setFilter] = useState<'all' | 'analyzed' | 'filled'>('all');
  const [remoteHistory, setRemoteHistory] = useState<FileHistoryItem[] | null>(null);
  const [loading, setLoading] = useState(false);

  // Use NEXT_PUBLIC_API_BASE for correct backend endpoint
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
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
  const filteredHistory =
    filter === 'all' ? combinedHistory : combinedHistory.filter(item => item.type === filter);

  // Upload file + metadata to backend. Backend will upload to GCS when configured.
  // helper to upload files to backend; currently may be called by parent components
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async function uploadToHistory(file: File, type: 'analyzed' | 'filled') {
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('type', type);

      const res = await fetch(`${API_BASE}/api/file-history/`, {
        method: 'POST',
        body: form,
      });
      if (res.ok) {
        const added = await res.json();
        setRemoteHistory(prev => prev ? [added, ...prev] : [added]);
      } else {
        console.error('Upload failed', await res.text());
      }
    } catch (e) {
      console.error('Error uploading file', e);
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6 min-w-[340px]">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        File History
      </h3>
      {apiBaseError ? (
        <div className="text-red-600 text-sm text-center py-8">{apiBaseError}</div>
      ) : (
        <>
          <div className="mb-4 flex gap-2">
            <button
              className={`px-3 py-1 rounded text-sm font-medium border ${filter === 'all' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button
              className={`px-3 py-1 rounded text-sm font-medium border ${filter === 'analyzed' ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}
              onClick={() => setFilter('analyzed')}
            >
              Analyzed
            </button>
            <button
              className={`px-3 py-1 rounded text-sm font-medium border ${filter === 'filled' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}
              onClick={() => setFilter('filled')}
            >
              Filled
            </button>
          </div>
          <div className="space-y-3">
            {loading ? (
              <div className="text-blue-400 text-sm text-center py-8">
                Loading file history...
              </div>
            ) : filteredHistory.length === 0 ? (
              <div className="text-gray-400 text-sm text-center py-8">
                No file history yet.
              </div>
            ) : (
              filteredHistory.map(item => (
                <div key={item.url} className="flex items-center justify-between bg-gray-50 rounded p-3 border border-gray-100">
                  <div>
                    <div className="font-medium text-gray-900 text-sm">{item.filename}</div>
                    <div className="text-xs text-gray-500">
                      {item.type === 'analyzed' ? 'Analyzed' : 'Filled'} · {new Date(item.timestamp).toLocaleString()}
                      {item.size_bytes ? ` · ${Math.round(item.size_bytes / 1024)} KB` : ''}
                      {item.content_type ? ` · ${item.content_type}` : ''}
                    </div>
                  </div>
                  <a
                    href={item.url}
                    download
                    className="ml-2 text-blue-600 hover:text-blue-800 p-2 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                    title={`Download ${item.filename}`}
                  >
                    <FiDownload className="h-5 w-5" />
                  </a>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
