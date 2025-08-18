'use client';

import React, { useEffect, useState, useRef } from 'react';
import { FiDownload } from 'react-icons/fi';
import type { FileHistoryItem } from './FileHistory';

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

  // Always use a single default type for favorites uploads
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
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <h3 className="text-lg font-semibold mb-3">Favorites</h3>

      <div className="mb-3 flex gap-2 items-center">
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700 disabled:opacity-50"
        >
          {uploading ? 'Uploading...' : 'Add File'}
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md,.csv" onChange={onFileChange} className="hidden" />
      </div>

      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}

      {loading ? (
        <div className="text-sm text-gray-500">Loading favorites...</div>
      ) : favorites.length === 0 ? (
        <div className="text-sm text-gray-400">No favorites yet.</div>
      ) : (
        <div className="space-y-2">
          {favorites.map(f => (
            <div key={(f.timestamp || '') + f.filename} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div className="text-sm">
                <div className="font-medium">{f.filename}</div>
                <div className="text-xs text-gray-500">{new Date(f.timestamp).toLocaleString()}</div>
              </div>
              <a href={f.url || '#'} download={!!f.url} className="text-blue-600 hover:text-blue-800 p-2">
                <FiDownload className="h-4 w-4" />
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
         