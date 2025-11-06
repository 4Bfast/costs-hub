"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, Organization, LoginCredentials, RegisterData } from '@/types/auth';
import { authService } from '@/lib/auth-api';

// Simple auth state
interface AuthState {
  user: User | null;
  organization: Organization | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// Auth context type
interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth provider component
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    organization: null,
    isAuthenticated: false,
    isLoading: false, // Start with loading false to prevent SSR issues
    error: null,
  });

  // Check for existing authentication on mount - only on client side
  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;
    
    const checkExistingAuth = async () => {
      setState(prev => ({ ...prev, isLoading: true }));
      
      try {
        const environment = process.env.NEXT_PUBLIC_ENVIRONMENT;
        
        if (environment === 'production') {
          // Check Cognito session
          const { cognitoAuth } = await import('@/lib/auth-cognito');
          const session = await cognitoAuth.getCurrentSession();
          
          if (session && session.isValid()) {
            const userAttributes = await cognitoAuth.getUserAttributes();
            
            const user: User = {
              id: userAttributes.sub,
              email: userAttributes.email,
              name: userAttributes.name || userAttributes.email,
              organizationId: '1',
              role: 'ADMIN', // Use uppercase for consistency
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            };

            const organization: Organization = {
              id: '1',
              name: 'Default Organization',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            };

            setState({
              user,
              organization,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
            return;
          }
        }
        
        setState(prev => ({ ...prev, isLoading: false }));
      } catch (error) {
        console.error('Error checking existing auth:', error);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    // Add a small delay to ensure proper hydration
    const timer = setTimeout(checkExistingAuth, 100);
    return () => clearTimeout(timer);
  }, []);

  const login = async (credentials: LoginCredentials) => {
    try {
      console.log('🔐 Starting login process...');
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      // Check environment
      const environment = process.env.NEXT_PUBLIC_ENVIRONMENT;
      
      if (environment === 'production') {
        console.log('🌐 Using Cognito direct authentication');
        
        // Use direct Cognito authentication
        const { cognitoAuth } = await import('@/lib/auth-cognito');
        const session = await cognitoAuth.signIn(credentials.email, credentials.password);
        
        // Get user attributes
        const userAttributes = await cognitoAuth.getUserAttributes();
        
        const user: User = {
          id: userAttributes.sub,
          email: userAttributes.email,
          name: userAttributes.name || userAttributes.email,
          organizationId: '1',
          role: 'ADMIN',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        const organization: Organization = {
          id: '1',
          name: 'Default Organization',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        setState({
          user,
          organization,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
        
        console.log('✅ Cognito login successful');
        return;
      }
      
      // Fallback to other environments
      let response;
      if (environment === 'aws-dev') {
        console.log('🌐 Using AWS environment');
        const { awsApiAdapter } = await import('@/lib/aws-api-adapter');
        response = await awsApiAdapter.login(credentials);
      } else {
        console.log('🏠 Using local environment');
        response = await authService.login(credentials);
      }
      
      console.log('📡 Login response:', response);
      
      if (response.success && response.data) {
        const user: User = {
          id: response.data.user.id, email: response.data.user.email, name: response.data.user.name,
          organizationId: response.data.user.organization_id,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        const organization: Organization = {
          ...response.data.organization,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        setState({
          user,
          organization,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
        
        console.log('✅ Login successful');
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error: any) {
      console.error('❌ Login error:', error);
      
      // Handle Cognito-specific errors
      let errorMessage = 'Login failed';
      if (error.code) {
        switch (error.code) {
          case 'UserNotConfirmedException':
            errorMessage = 'Please confirm your email address before signing in.';
            break;
          case 'NotAuthorizedException':
            errorMessage = 'Incorrect email or password.';
            break;
          case 'UserNotFoundException':
            errorMessage = 'User not found. Please check your email address.';
            break;
          case 'TooManyRequestsException':
            errorMessage = 'Too many failed attempts. Please try again later.';
            break;
          default:
            errorMessage = error.message || 'Login failed';
        }
      } else {
        errorMessage = error.response?.data?.errors?.[0] || error.message || 'Login failed';
      }
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      const response = await authService.register(data);
      
      if (response.success && response.data) {
        const user: User = {
          id: response.data.user.id, email: response.data.user.email, name: response.data.user.name,
          organizationId: response.data.user.organization_id,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        const organization: Organization = {
          ...response.data.organization,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        setState({
          user,
          organization,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.message || 'Registration failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const logout = async () => {
    try {
      const environment = process.env.NEXT_PUBLIC_ENVIRONMENT;
      
      if (environment === 'production') {
        const { cognitoAuth } = await import('@/lib/auth-cognito');
        cognitoAuth.signOut();
      } else {
        await authService.logout();
      }
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setState({
        user: null,
        organization: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  };

  const clearError = () => {
    setState(prev => ({ ...prev, error: null }));
  };

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}