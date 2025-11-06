export interface User {
  id: string;
  email: string;
  name: string;
  role: 'ADMIN' | 'MEMBER';
  organizationId: string;
  createdAt: string;
  updatedAt: string;
}

export interface Organization {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuthState {
  user: User | null;
  organization: Organization | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  organizationName: string;
  adminName: string;
  adminEmail: string;
  password: string;
}

export interface AuthResponse {
  success: boolean;
  data: {
    user: {
      id: string;
      name: string;
      email: string;
      role: 'ADMIN' | 'MEMBER';
      organization_id: string;
    };
    organization: {
      id: string;
      name: string;
    };
    token: string;
  };
  errors?: string[];
}

export interface RefreshTokenResponse {
  accessToken: string;
  refreshToken: string;
}