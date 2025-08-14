'use client';

import { useAuth } from '@/contexts/AuthContext';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import { useState } from 'react';

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginMode, setIsLoginMode] = useState(true);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return isLoginMode ? (
      <LoginForm onToggleMode={() => setIsLoginMode(false)} />
    ) : (
      <RegisterForm onToggleMode={() => setIsLoginMode(true)} />
    );
  }

  return <>{children}</>;
}
