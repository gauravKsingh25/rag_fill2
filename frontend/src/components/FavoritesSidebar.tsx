'use client';

import React, { useEffect, useState, useRef } from 'react';
import { FiDownload } from 'react-icons/fi';
import type { FileHistoryItem } from './FileHistory';
import { API_BASE_URL } from '@/config/api';

export default function FavoritesSidebar() {
  const [favorites, setFavorites] = useState<FileHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || '').trim() || 'http://localhost:8000';

  async function loadFavorites() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/favorites/`);
      if (!res.ok) throw new Error(`Failed to load favorites (${res.status})`);
      const items = await res.json();
      setFavorites(items);
    } catch (e) {
      setError((e as Error).message || 'Failed to load favorites');
      setFavorites([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFavorites();
  }, []);

  const DEFAULT_FAVORITE_TYPE = 'filled';

  async function uploadFavorite(file: File /*, type omitted - use default */) {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('type', DEFAULT_FAVORITE_TYPE);
      form.append('timestamp', new Date().toISOString());

      const res = await fetch(`${API_BASE}/api/favorites/`, {
        method: 'POST',
        body: form,
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || `Upload failed (${res.status})`);
      }
      const added = await res.json();
      setFavorites(prev => [added, ...prev]);
    } catch (e) {
      setError((e as Error).message || 'Upload failed');
      console.error('Upload favorite failed', e);
    } finally {
      setUploading(false);
    }
  }

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await uploadFavorite(file);
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <div className="card p-4">
      <h3 className="text-lg font-semibold mb-1 text-gray-900">Favorites</h3>
      <div className="text-xs text-muted mb-3">Quick access to uploaded templates and filled files</div>

      <div className="mb-3 flex gap-2 items-center">
        <button onClick={() => fileRef.current?.click()} disabled={uploading} className="btn-primary text-sm">
          {uploading ? 'Uploading...' : 'Add File'}
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md,.csv" onChange={onFileChange} className="hidden" />
      </div>

      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}

      {loading ? (
        <div className="text-sm text-muted">Loading favorites...</div>
      ) : favorites.length === 0 ? (
        <div className="text-sm text-muted">No favorites yet. Add a file to get started.</div>
      ) : (
        <div className="space-y-2">
          {favorites.map(f => {
            const localUrl = `${typeof window !== 'undefined' ? window.location.origin : ''}/local_storage/favorites_uploads/${encodeURIComponent(f.filename)}`;
            const href = f.url && f.url !== '' ? (f.url.startsWith('http') ? f.url : `${API_BASE}${f.url}`) : localUrl;
            return (
              <div key={(f.timestamp || '') + f.filename} className="file-item">
                <div className="meta">
                  <div className="filename">{f.filename}</div>
                  <div className="sub">{new Date(f.timestamp).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`badge ${f.type === 'filled' ? 'filled' : 'analyzed'}`}>{f.type === 'filled' ? 'Filled' : 'Analyzed'}</span>
                  <a href={href} download className="download-btn" title={`Download ${f.filename}`}>
                    <FiDownload className="h-4 w-4" />
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
