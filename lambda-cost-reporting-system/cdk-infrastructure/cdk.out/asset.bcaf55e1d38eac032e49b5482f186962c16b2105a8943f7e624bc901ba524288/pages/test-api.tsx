// Test page for new Frontend API (optional)
import { useState } from 'react';

export default function TestAPI() {
  const [result, setResult] = useState('');

  const testAPI = async () => {
    try {
      const response = await fetch('/api/test-frontend-api');
      const data = await response.text();
      setResult(data);
    } catch (error) {
      setResult(`Error: ${error.message}`);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Frontend API Test</h1>
      <button 
        onClick={testAPI}
        className="bg-blue-500 text-white px-4 py-2 rounded mb-4"
      >
        Test API
      </button>
      <pre className="bg-gray-100 p-4 rounded">{result}</pre>
    </div>
  );
}
