'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { API_BASE_URL, API_CONFIG } from '@/config/api'; // use centralized config and timeout

interface User {
  id: string;
  email: string;
  created_at: string;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // normalize backend base (use the exact env-driven API_BASE_URL)
  const BACKEND_BASE = (API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

  // fetch helper with timeout to avoid infinite hanging requests
  const fetchWithTimeout = async (input: RequestInfo, init?: RequestInit, timeout = API_CONFIG.TIMEOUT) => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(input, { ...init, signal: controller.signal });
      return response;
    } finally {
      clearTimeout(id);
    }
  };

  // Check for stored token on component mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
      setToken(storedToken);
      verifyToken(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const verifyToken = async (tokenToVerify: string) => {
    try {
      // Try fetching the current user directly (common endpoint)
      const userResponse = await fetchWithTimeout(`${BACKEND_BASE}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${tokenToVerify}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUser(userData);
      } else {
        // Fallback: if /me is not present, try verify-token endpoint if available
        try {
          const verifyResp = await fetchWithTimeout(`${BACKEND_BASE}/api/auth/verify-token`, {
            headers: { 'Authorization': `Bearer ${tokenToVerify}` },
          });
          if (!verifyResp.ok) {
            localStorage.removeItem('auth_token');
            setToken(null);
            setUser(null);
          }
        } catch (inner) {
          // If fallback also fails or times out, clear token
          localStorage.removeItem('auth_token');
          setToken(null);
          setUser(null);
        }
      }
    } catch (error) {
      // Network error or timeout -> consider token invalid / unreachable backend
      console.error('Token verification failed (network/timeout):', error);
      localStorage.removeItem('auth_token');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await fetchWithTimeout(`${BACKEND_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        // Try to parse error body, otherwise throw generic
        let msg = 'Login failed';
        try {
          const errorData = await response.json();
          msg = errorData.detail || msg;
        } catch {
          // ignore parse error
        }
        throw new Error(msg);
      }

      const data = await response.json();
      const newToken = data.access_token;

      // Store token
      localStorage.setItem('auth_token', newToken);
      setToken(newToken);

      // Try to fetch user info with timeout; if it fails, don't hang — leave user null
      try {
        const userResponse = await fetchWithTimeout(`${BACKEND_BASE}/api/auth/me`, {
          headers: { 'Authorization': `Bearer ${newToken}` },
        });
        if (userResponse.ok) {
          const userData = await userResponse.json();
          setUser(userData);
        }
      } catch (e) {
        console.warn('Failed to fetch user after login (network/timeout). Token stored.', e);
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    try {
      const response = await fetch(`${BACKEND_BASE}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Registration failed');
      }

      // After successful registration, automatically log in
      await login(email, password);
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    isLoading,
    login,
    register,
    logout,
    isAuthenticated: !!token && !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
