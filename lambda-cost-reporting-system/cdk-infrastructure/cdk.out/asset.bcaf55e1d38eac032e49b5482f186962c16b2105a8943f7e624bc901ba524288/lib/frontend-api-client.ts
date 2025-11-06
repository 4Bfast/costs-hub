// Frontend API Gateway Client - Minimal implementation
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://g7zg773vde.execute-api.us-east-1.amazonaws.com/dev';

// Simple JWT token (for testing)
const getAuthToken = () => {
  // For now, return a simple test token
  return 'Bearer test-token';
};

// Basic API client
export const frontendApiClient = {
  async get(endpoint: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1${endpoint}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': getAuthToken(),
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  }
};
