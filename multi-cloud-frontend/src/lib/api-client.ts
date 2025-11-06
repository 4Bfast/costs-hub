import axios, { 
  AxiosInstance, 
  AxiosResponse, 
  AxiosError, 
  InternalAxiosRequestConfig 
} from 'axios';
import { toast } from 'sonner';

import { ApiResponse, PaginatedResponse } from '@/types/api';
import { tokenManager } from './token-manager';

// Error types
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class NetworkError extends Error {
  constructor(message: string, public originalError: Error) {
    super(message);
    this.name = 'NetworkError';
  }
}

class ValidationError extends Error {
  constructor(message: string, public errors: Record<string, string[]>) {
    super(message);
    this.name = 'ValidationError';
  }
}

// Retry configuration
interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  retryCondition: (error: AxiosError) => boolean;
}

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  retryDelay: 1000,
  retryCondition: (error: AxiosError) => {
    // Retry on network errors or 5xx server errors
    return !error.response || (error.response.status >= 500 && error.response.status < 600);
  },
};

class ApiClient {
  private client: AxiosInstance;
  private retryConfig: RetryConfig;

  constructor() {
    const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api-costhub.4bfast.com.br';
    
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 second timeout
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: false, // API Gateway doesn't need cookies
    });

    this.retryConfig = defaultRetryConfig;
    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor for authentication
    this.client.interceptors.request.use(
      async (config: InternalAxiosRequestConfig & { metadata?: { startTime: number } }) => {
        // Add request timestamp for debugging
        config.metadata = { startTime: Date.now() };
        
        // Add client-side request ID for tracing
        config.headers['X-Request-ID'] = this.generateRequestId();
        
        // Add Bearer token based on environment
        const environment = process.env.NEXT_PUBLIC_ENVIRONMENT;
        
        if (environment === 'production') {
          // Use Cognito tokens in production
          const { cognitoTokenManager } = await import('./cognito-token-manager');
          const token = await cognitoTokenManager.getAccessToken();
          if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
          }
        } else {
          // Use JWT tokens in other environments
          const token = tokenManager.getAccessToken();
          if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
          }
        }
        
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling and token refresh
    this.client.interceptors.response.use(
      (response: AxiosResponse & { config: InternalAxiosRequestConfig & { metadata?: { startTime: number } } }) => {
        // Log successful requests in development
        if (process.env.NODE_ENV === 'development') {
          const duration = Date.now() - (response.config.metadata?.startTime || Date.now());
          console.log(`✅ ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`);
        }
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean; _retryCount?: number };

        // Handle token refresh for 401 errors
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // Try to refresh the token
            await this.refreshToken();
            
            // Retry the original request
            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.handleAuthenticationFailure();
            return Promise.reject(new ApiError('Authentication failed', 401, 'AUTH_FAILED'));
          }
        }

        // Handle retry logic for retryable errors
        if (this.shouldRetry(error, originalRequest)) {
          return this.retryRequest(originalRequest, error);
        }

        // Transform error to our custom error types
        throw this.transformError(error);
      }
    );
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private async refreshToken(): Promise<void> {
    try {
      await this.client.post('/auth/refresh');
    } catch (error) {
      throw new ApiError('Token refresh failed', 401, 'REFRESH_FAILED');
    }
  }

  private handleAuthenticationFailure(): void {
    if (typeof window !== 'undefined') {
      // Clear JWT tokens
      tokenManager.clearTokens();
      
      // Show error message
      toast.error('Your session has expired. Please log in again.');
      
      // Redirect to login page
      window.location.href = '/login';
    }
  }

  private shouldRetry(error: AxiosError, config: InternalAxiosRequestConfig & { _retryCount?: number }): boolean {
    const retryCount = config._retryCount || 0;
    return retryCount < this.retryConfig.maxRetries && this.retryConfig.retryCondition(error);
  }

  private async retryRequest(
    config: InternalAxiosRequestConfig & { _retryCount?: number }, 
    lastError: AxiosError
  ): Promise<AxiosResponse> {
    config._retryCount = (config._retryCount || 0) + 1;
    
    // Exponential backoff with jitter
    const delay = this.retryConfig.retryDelay * Math.pow(2, config._retryCount - 1);
    const jitter = Math.random() * 1000;
    
    await new Promise(resolve => setTimeout(resolve, delay + jitter));
    
    console.warn(`Retrying request (${config._retryCount}/${this.retryConfig.maxRetries}):`, config.url);
    
    return this.client(config);
  }

  private transformError(error: AxiosError): Error {
    if (!error.response) {
      // Network error
      return new NetworkError('Network error occurred', error);
    }

    const { status, data } = error.response;
    const apiResponse = data as ApiResponse;

    // Handle validation errors (422)
    if (status === 422 && apiResponse?.errors) {
      const validationErrors: Record<string, string[]> = {};
      apiResponse.errors.forEach(errorMsg => {
        // Parse validation error format: "field: message"
        const [field, ...messageParts] = errorMsg.split(': ');
        const message = messageParts.join(': ');
        if (!validationErrors[field]) {
          validationErrors[field] = [];
        }
        validationErrors[field].push(message);
      });
      return new ValidationError('Validation failed', validationErrors);
    }

    // Handle other API errors
    const message = apiResponse?.errors?.[0] || error.message || 'An error occurred';
    return new ApiError(message, status, 'API_ERROR', apiResponse);
  }

  // Generic request methods
  async get<T>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.get<ApiResponse<T>>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.post<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.put<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.patch<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.delete<ApiResponse<T>>(url, config);
    return response.data;
  }

  // Paginated requests
  async getPaginated<T>(
    url: string, 
    params?: { page?: number; limit?: number; [key: string]: any }
  ): Promise<PaginatedResponse<T>> {
    const response = await this.client.get<PaginatedResponse<T>>(url, { params });
    return response.data;
  }

  // File upload
  async uploadFile<T>(url: string, file: File, onProgress?: (progress: number) => void): Promise<ApiResponse<T>> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<ApiResponse<T>>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  }

  // Download file
  async downloadFile(url: string, filename?: string): Promise<void> {
    const response = await this.client.get(url, {
      responseType: 'blob',
    });

    // Create download link
    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.get('/health');
      return true;
    } catch {
      return false;
    }
  }

  // Update retry configuration
  updateRetryConfig(config: Partial<RetryConfig>): void {
    this.retryConfig = { ...this.retryConfig, ...config };
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Export error types for use in components
export { ApiError, NetworkError, ValidationError };