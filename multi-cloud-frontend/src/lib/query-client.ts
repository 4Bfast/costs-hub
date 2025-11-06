import { QueryClient, DefaultOptions } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiError, NetworkError, ValidationError } from './api-client';

// Default query options
const defaultOptions: DefaultOptions = {
  queries: {
    // Stale time: 5 minutes for most data
    staleTime: 5 * 60 * 1000,
    // Cache time: 10 minutes
    gcTime: 10 * 60 * 1000,
    // Retry configuration
    retry: (failureCount, error) => {
      // Don't retry on client errors (4xx)
      if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
        return false;
      }
      // Retry up to 3 times for server errors and network errors
      return failureCount < 3;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    // Refetch on window focus for critical data
    refetchOnWindowFocus: false,
    // Refetch on reconnect
    refetchOnReconnect: true,
  },
  mutations: {
    retry: (failureCount, error) => {
      // Don't retry mutations on client errors
      if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
        return false;
      }
      // Retry once for server errors
      return failureCount < 1;
    },
    onError: (error) => {
      // Global error handling for mutations
      if (error instanceof ValidationError) {
        // Handle validation errors
        const firstError = Object.values(error.errors)[0]?.[0];
        toast.error(firstError || 'Validation failed');
      } else if (error instanceof ApiError) {
        // Handle API errors
        toast.error(error.message);
      } else if (error instanceof NetworkError) {
        // Handle network errors
        toast.error('Network error. Please check your connection.');
      } else {
        // Handle unknown errors
        toast.error('An unexpected error occurred');
      }
    },
  },
};

// Create query client with custom configuration
export const queryClient = new QueryClient({
  defaultOptions,
});

// Query key factories for consistent cache keys
export const queryKeys = {
  // Auth
  auth: {
    profile: () => ['auth', 'profile'] as const,
    organization: () => ['auth', 'organization'] as const,
  },
  
  // Cost data
  costs: {
    all: () => ['costs'] as const,
    summary: (filters?: any) => ['costs', 'summary', filters] as const,
    records: (filters?: any) => ['costs', 'records', filters] as const,
    trends: (period: string, filters?: any) => ['costs', 'trends', period, filters] as const,
    breakdown: (type: string, filters?: any) => ['costs', 'breakdown', type, filters] as const,
  },
  
  // Provider accounts
  accounts: {
    all: () => ['accounts'] as const,
    byProvider: (provider: string) => ['accounts', 'provider', provider] as const,
    detail: (id: string) => ['accounts', 'detail', id] as const,
    status: (id: string) => ['accounts', 'status', id] as const,
  },
  
  // AI Insights
  insights: {
    all: () => ['insights'] as const,
    list: (filters?: any) => ['insights', 'list', filters] as const,
    detail: (id: string) => ['insights', 'detail', id] as const,
    summary: () => ['insights', 'summary'] as const,
  },
  
  // Alarms
  alarms: {
    all: () => ['alarms'] as const,
    list: (filters?: any) => ['alarms', 'list', filters] as const,
    detail: (id: string) => ['alarms', 'detail', id] as const,
    events: (alarmId?: string) => ['alarms', 'events', alarmId] as const,
  },
  
  // Users and organization
  users: {
    all: () => ['users'] as const,
    list: () => ['users', 'list'] as const,
    detail: (id: string) => ['users', 'detail', id] as const,
  },
  
  // Dashboard
  dashboard: {
    data: (period?: string) => ['dashboard', 'data', period] as const,
    metrics: () => ['dashboard', 'metrics'] as const,
  },
  
  // Notifications
  notifications: {
    all: () => ['notifications'] as const,
    unread: () => ['notifications', 'unread'] as const,
  },
  
  // Settings
  settings: {
    user: () => ['settings', 'user'] as const,
    organization: () => ['settings', 'organization'] as const,
    notifications: () => ['settings', 'notifications'] as const,
  },
};

// Cache invalidation helpers
export const invalidateQueries = {
  // Invalidate all cost-related queries
  costs: () => queryClient.invalidateQueries({ queryKey: queryKeys.costs.all() }),
  
  // Invalidate all account-related queries
  accounts: () => queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all() }),
  
  // Invalidate all insight-related queries
  insights: () => queryClient.invalidateQueries({ queryKey: queryKeys.insights.all() }),
  
  // Invalidate all alarm-related queries
  alarms: () => queryClient.invalidateQueries({ queryKey: queryKeys.alarms.all() }),
  
  // Invalidate dashboard data
  dashboard: () => queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.data() }),
  
  // Invalidate all user-related queries
  users: () => queryClient.invalidateQueries({ queryKey: queryKeys.users.all() }),
  
  // Invalidate notifications
  notifications: () => queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all() }),
};

// Prefetch helpers for common data
export const prefetchQueries = {
  // Prefetch dashboard data
  dashboard: async (period = '30d') => {
    await queryClient.prefetchQuery({
      queryKey: queryKeys.dashboard.data(period),
      staleTime: 2 * 60 * 1000, // 2 minutes for dashboard data
    });
  },
  
  // Prefetch user profile
  profile: async () => {
    await queryClient.prefetchQuery({
      queryKey: queryKeys.auth.profile(),
      staleTime: 10 * 60 * 1000, // 10 minutes for profile data
    });
  },
  
  // Prefetch provider accounts
  accounts: async () => {
    await queryClient.prefetchQuery({
      queryKey: queryKeys.accounts.all(),
      staleTime: 5 * 60 * 1000, // 5 minutes for account data
    });
  },
};

// Optimistic update helpers
export const optimisticUpdates = {
  // Update user profile optimistically
  updateUserProfile: (updates: any) => {
    queryClient.setQueryData(queryKeys.auth.profile(), (old: any) => ({
      ...old,
      ...updates,
    }));
  },
  
  // Update account status optimistically
  updateAccountStatus: (accountId: string, status: string) => {
    queryClient.setQueryData(queryKeys.accounts.all(), (old: any[]) =>
      old?.map((account) =>
        account.id === accountId ? { ...account, status } : account
      )
    );
  },
  
  // Update alarm status optimistically
  updateAlarmStatus: (alarmId: string, status: string) => {
    queryClient.setQueryData(queryKeys.alarms.all(), (old: any[]) =>
      old?.map((alarm) =>
        alarm.id === alarmId ? { ...alarm, status } : alarm
      )
    );
  },
  
  // Mark notification as read optimistically
  markNotificationRead: (notificationId: string) => {
    queryClient.setQueryData(queryKeys.notifications.all(), (old: any[]) =>
      old?.map((notification) =>
        notification.id === notificationId
          ? { ...notification, read: true }
          : notification
      )
    );
  },
};

// Error boundary for React Query
export class QueryErrorBoundary extends Error {
  constructor(message: string, public originalError: Error) {
    super(message);
    this.name = 'QueryErrorBoundary';
  }
}

// Global error handler for queries
export const handleQueryError = (error: Error) => {
  console.error('Query error:', error);
  
  if (error instanceof ApiError) {
    // Handle specific API errors
    if (error.status === 401) {
      // Authentication error - handled by API client
      return;
    } else if (error.status === 403) {
      toast.error('You do not have permission to access this resource');
    } else if (error.status >= 500) {
      toast.error('Server error. Please try again later.');
    }
  } else if (error instanceof NetworkError) {
    toast.error('Network error. Please check your connection.');
  } else {
    toast.error('An unexpected error occurred');
  }
};

// Query client configuration for different data types
export const queryConfigs = {
  // Real-time data (short cache)
  realTime: {
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 60 * 1000, // Refetch every minute
  },
  
  // Frequently changing data
  frequent: {
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
  },
  
  // Stable data (long cache)
  stable: {
    staleTime: 15 * 60 * 1000, // 15 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  },
  
  // Static data (very long cache)
  static: {
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  },
};