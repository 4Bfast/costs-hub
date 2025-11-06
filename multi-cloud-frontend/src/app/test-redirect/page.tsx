"use client";

import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function TestRedirectPage() {
  const router = useRouter();
  const [log, setLog] = useState<string[]>([]);

  const addLog = (message: string) => {
    console.log(message);
    setLog(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  const testRouterPush = () => {
    addLog('Testing router.push("/dashboard")...');
    try {
      router.push("/dashboard");
      addLog('✅ router.push called successfully');
    } catch (error) {
      addLog(`❌ router.push failed: ${error}`);
    }
  };

  const testWindowLocation = () => {
    addLog('Testing window.location.href = "/dashboard"...');
    try {
      window.location.href = '/dashboard';
      addLog('✅ window.location.href set successfully');
    } catch (error) {
      addLog(`❌ window.location.href failed: ${error}`);
    }
  };

  const testLogin = async () => {
    addLog('Testing login flow...');
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'test123'
        })
      });
      
      const data = await response.json();
      addLog(`Login response: ${JSON.stringify(data)}`);
      
      if (data.success) {
        addLog('✅ Login successful, testing redirect...');
        setTimeout(() => {
          router.push("/dashboard");
        }, 100);
      }
    } catch (error) {
      addLog(`❌ Login failed: ${error}`);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Test Redirect Page</h1>
      
      <div className="space-y-4 mb-8">
        <button 
          onClick={testRouterPush}
          className="bg-blue-500 text-white px-4 py-2 rounded mr-4"
        >
          Test router.push()
        </button>
        
        <button 
          onClick={testWindowLocation}
          className="bg-green-500 text-white px-4 py-2 rounded mr-4"
        >
          Test window.location
        </button>
        
        <button 
          onClick={testLogin}
          className="bg-purple-500 text-white px-4 py-2 rounded"
        >
          Test Login + Redirect
        </button>
      </div>

      <div className="bg-gray-100 p-4 rounded">
        <h2 className="font-bold mb-2">Log:</h2>
        <div className="space-y-1">
          {log.map((entry, index) => (
            <div key={index} className="text-sm font-mono">
              {entry}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}