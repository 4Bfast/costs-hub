/**
 * Token Manager for handling JWT tokens
 * Uses httpOnly cookies for security, with localStorage fallback for development
 */

const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export const tokenManager = {
  /**
   * Get access token from storage
   * In production, this would be handled by httpOnly cookies
   */
  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    
    // In development, we might use localStorage
    // In production, tokens should be in httpOnly cookies
    return localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Set access token in storage
   * In production, this would be handled by the server setting httpOnly cookies
   */
  setAccessToken(token: string): void {
    if (typeof window === 'undefined') return;
    
    localStorage.setItem(TOKEN_KEY, token);
  },

  /**
   * Get refresh token from storage
   */
  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  /**
   * Set refresh token in storage
   */
  setRefreshToken(token: string): void {
    if (typeof window === 'undefined') return;
    
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },

  /**
   * Clear all tokens from storage
   */
  clearTokens(): void {
    if (typeof window === 'undefined') return;
    
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  /**
   * Check if access token exists
   */
  hasAccessToken(): boolean {
    return !!this.getAccessToken();
  },

  /**
   * Check if refresh token exists
   */
  hasRefreshToken(): boolean {
    return !!this.getRefreshToken();
  },

  /**
   * Decode JWT token payload (without verification)
   * This is for client-side use only - never trust this data for security
   */
  decodeToken(token: string): any {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Error decoding token:', error);
      return null;
    }
  },

  /**
   * Check if token is expired
   */
  isTokenExpired(token: string): boolean {
    const decoded = this.decodeToken(token);
    if (!decoded || !decoded.exp) return true;
    
    const currentTime = Date.now() / 1000;
    return decoded.exp < currentTime;
  },

  /**
   * Get token expiration time
   */
  getTokenExpiration(token: string): Date | null {
    const decoded = this.decodeToken(token);
    if (!decoded || !decoded.exp) return null;
    
    return new Date(decoded.exp * 1000);
  },

  /**
   * Check if access token needs refresh (expires in less than 5 minutes)
   */
  shouldRefreshToken(): boolean {
    const token = this.getAccessToken();
    if (!token) return false;
    
    const decoded = this.decodeToken(token);
    if (!decoded || !decoded.exp) return true;
    
    const currentTime = Date.now() / 1000;
    const timeUntilExpiry = decoded.exp - currentTime;
    
    // Refresh if token expires in less than 5 minutes (300 seconds)
    return timeUntilExpiry < 300;
  },
};