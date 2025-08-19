'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';

export default function Navigation() {
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
  };

  return (
    <nav className="bg-white border-b border-[var(--border)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-md bg-gradient-to-br from-indigo-50 to-white flex items-center justify-center text-[var(--primary)] shadow-sm">
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <div className="text-lg font-semibold text-gray-900 leading-tight">
                RAG System
              </div>
              <div className="text-xs text-muted hidden sm:block">
                Device-focused document assistant
              </div>
            </div>
          </div>

          {/* User menu */}
          <div className="flex items-center">
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                aria-expanded={showUserMenu}
                className="flex items-center space-x-3 text-sm rounded-full focus:outline-none btn-ghost px-2 py-1"
              >
                <div
                  className="h-8 w-8 rounded-full flex items-center justify-center"
                  style={{ background: 'var(--primary)' }}
                >
                  <span className="text-white font-medium">
                    {user?.email ? user.email.charAt(0).toUpperCase() : 'U'}
                  </span>
                </div>
                <span className="text-gray-700 font-medium hidden sm:block truncate max-w-[200px]">
                  {user?.email || 'Unknown'}
                </span>
                <svg
                  className={`h-4 w-4 text-gray-400 transition-transform ${
                    showUserMenu ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-60 z-50">
                  <div className="card p-2 shadow-md">
                    <div className="px-4 py-2 text-sm text-gray-800 border-b border-[var(--border)]">
                      <div className="font-medium truncate">{user?.email}</div>
                      <div className="text-xs text-muted">
                        Joined{' '}
                        {user?.created_at
                          ? new Date(user.created_at).toLocaleDateString()
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="px-2 py-2">
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded flex items-center gap-3"
                      >
                        <svg
                          className="h-4 w-4 text-gray-400"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                          />
                        </svg>
                        Sign out
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showUserMenu && (
        <div
          className="fixed inset-0 z-40 sm:hidden"
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </nav>
  );
}
