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
    <nav className="bg-white/90 backdrop-blur-lg border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-lg animate-float">
              <svg
                className="h-6 w-6 text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M21 7L12 13 3 7l9-6 9 6z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <div className="text-lg font-bold text-gray-900 leading-tight tracking-tight">
                RAG System
              </div>
              <div className="text-xs text-gray-600 hidden sm:block font-medium">
                Intelligent Document Assistant
              </div>
            </div>
          </div>

          {/* User menu */}
          <div className="flex items-center">
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                aria-expanded={showUserMenu}
                className="flex items-center space-x-3 text-sm rounded-xl focus:outline-none hover:bg-gray-50 px-3 py-2 transition-all duration-200 hover:shadow-sm border border-transparent hover:border-gray-200"
              >
                <div className="h-8 w-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-blue-600 to-blue-700 shadow-sm">
                  <span className="text-white font-semibold text-sm">
                    {user?.email ? user.email.charAt(0).toUpperCase() : 'U'}
                  </span>
                </div>
                <span className="text-gray-700 font-medium hidden sm:block truncate max-w-[200px]">
                  {user?.email || 'Unknown'}
                </span>
                <svg
                  className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${
                    showUserMenu ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-72 z-50 animate-in slide-in-from-top-5 duration-200">
                  <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-1">
                    <div className="px-4 py-3 text-sm border-b border-gray-100">
                      <div className="font-semibold text-gray-900 truncate">{user?.email}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        Member since{' '}
                        {user?.created_at
                          ? new Date(user.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric'
                            })
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="p-1">
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg flex items-center gap-3 transition-all duration-200 group"
                      >
                        <svg
                          className="h-4 w-4 text-gray-400 group-hover:text-red-500 transition-colors"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                          />
                        </svg>
                        <span className="font-medium">Sign out</span>
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
