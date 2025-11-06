import axios, { AxiosResponse } from 'axios';
import { 
  AuthResponse, 
  LoginCredentials, 
  RegisterData, 
  RefreshTokenResponse,
  User 
} from '@/types/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

// Create axios instance for auth API
const authApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for httpOnly cookies
});

// Auth API functions
export const authService = {
  /**
   * Login user with email and password
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    // Transform email to username for API compatibility
    const loginData = {
      username: credentials.email,
      password: credentials.password
    };
    const response: AxiosResponse<AuthResponse> = await authApi.post('/auth/login', loginData);
    return response.data;
  },

  /**
   * Register new organization and admin user
   */
  async register(data: RegisterData): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await authApi.post('/auth/register', data);
    return response.data;
  },

  /**
   * Logout user and clear tokens
   */
  async logout(): Promise<void> {
    await authApi.post('/auth/logout');
  },

  /**
   * Refresh access token using httpOnly refresh token
   */
  async refreshToken(): Promise<RefreshTokenResponse> {
    const response: AxiosResponse<RefreshTokenResponse> = await authApi.post('/auth/refresh');
    return response.data;
  },

  /**
   * Get current user profile
   */
  async getProfile(): Promise<User> {
    const response: AxiosResponse<User> = await authApi.get('/auth/me');
    return response.data;
  },

  /**
   * Verify email address
   */
  async verifyEmail(token: string): Promise<void> {
    await authApi.post('/auth/verify-email', { token });
  },

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    await authApi.post('/auth/forgot-password', { email });
  },

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await authApi.post('/auth/reset-password', { token, password: newPassword });
  },

  /**
   * Change password for authenticated user
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await authApi.post('/auth/change-password', { 
      currentPassword, 
      newPassword 
    });
  },
};

// No automatic interceptor to avoid loops
// Token refresh will be handled manually when needed