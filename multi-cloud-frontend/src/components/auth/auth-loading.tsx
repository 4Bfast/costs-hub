"use client";

import { Loader2 } from 'lucide-react';

interface AuthLoadingProps {
  message?: string;
}

export function AuthLoading({ message = "Checking authentication..." }: AuthLoadingProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 via-blue-800 to-blue-700">
      <div className="text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-white/10 backdrop-blur-sm">
          <Loader2 className="h-8 w-8 animate-spin text-white" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          CostsHub
        </h2>
        <p className="text-blue-100">
          {message}
        </p>
      </div>
    </div>
  );
}

export function PageLoading({ message = "Loading..." }: AuthLoadingProps) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
        <p className="text-gray-600">{message}</p>
      </div>
    </div>
  );
}