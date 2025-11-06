'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AuthLogout() {
  const router = useRouter();

  useEffect(() => {
    // Clear any remaining tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('id_token');
    localStorage.removeItem('refresh_token');
    
    // Redirect to login after a short delay
    setTimeout(() => {
      router.push('/login');
    }, 2000);
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="text-blue-600 text-6xl mb-4">👋</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Logged Out</h1>
        <p className="text-gray-600 mb-4">You have been successfully logged out</p>
        <p className="text-sm text-gray-500">Redirecting to login...</p>
      </div>
    </div>
  );
}
