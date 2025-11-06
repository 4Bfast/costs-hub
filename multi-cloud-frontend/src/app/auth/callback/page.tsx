'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';

function AuthCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code');
        const error = searchParams.get('error');

        if (error) {
          setStatus('error');
          setError(`Authentication error: ${error}`);
          setTimeout(() => router.push('/login'), 3000);
          return;
        }

        if (code) {
          // Handle Cognito callback with authorization code
          const { cognitoAuth } = await import('@/lib/auth-cognito');
          
          // Exchange code for tokens
          const tokens = await cognitoAuth.exchangeCodeForTokens(code);
          
          // Get user info
          const userInfo = await cognitoAuth.getUserInfo(tokens.access_token);
          
          // Store tokens in localStorage for now (in production, use secure storage)
          localStorage.setItem('access_token', tokens.access_token);
          localStorage.setItem('id_token', tokens.id_token);
          localStorage.setItem('refresh_token', tokens.refresh_token);
          
          setStatus('success');
          
          // Redirect to dashboard after a short delay
          setTimeout(() => {
            router.push('/dashboard');
          }, 1000);
          
        } else {
          // No code parameter, redirect to login
          router.push('/login');
        }
      } catch (err: any) {
        console.error('Callback error:', err);
        setStatus('error');
        setError(err.message || 'Authentication failed');
        setTimeout(() => router.push('/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, router, login]);

  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Authentication Error</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <p className="text-sm text-gray-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-green-600 text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Login Successful!</h1>
          <p className="text-gray-600 mb-4">Welcome to CostsHub</p>
          <p className="text-sm text-gray-500">Redirecting to dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Processing authentication...</p>
      </div>
    </div>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      </div>
    }>
      <AuthCallbackInner />
    </Suspense>
  );
}
