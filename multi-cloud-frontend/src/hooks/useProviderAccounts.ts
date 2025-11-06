import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CloudProviderAccount } from '@/types/models';
import { ApiResponse } from '@/types/api';
import { apiClient } from '@/lib/api-client';

interface ConnectionTestResult {
  success: boolean;
  error?: string;
  details?: {
    permissions: string[];
    regions: string[];
    services: string[];
  };
}

interface ProviderAccountsResponse extends ApiResponse<CloudProviderAccount[]> {}
interface ProviderAccountResponse extends ApiResponse<CloudProviderAccount> {}
interface ConnectionTestResponse extends ApiResponse<ConnectionTestResult> {}

export function useProviderAccounts() {
  const queryClient = useQueryClient();

  // Fetch all provider accounts
  const {
    data: accountsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<ProviderAccountsResponse>({
    queryKey: ['provider-accounts'],
    queryFn: () => apiClient.get('/accounts'),
  });

  const accounts = accountsResponse?.data || [];

  // Create new provider account
  const createAccountMutation = useMutation({
    mutationFn: (accountData: Partial<CloudProviderAccount>) =>
      apiClient.post<ProviderAccountResponse>('/accounts', accountData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['provider-accounts'] });
    },
  });

  // Update provider account
  const updateAccountMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CloudProviderAccount> }) =>
      apiClient.put<ProviderAccountResponse>(`/accounts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['provider-accounts'] });
    },
  });

  // Delete provider account
  const deleteAccountMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`/accounts/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['provider-accounts'] });
    },
  });

  // Test connection
  const testConnectionMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.post<ConnectionTestResponse>(`/accounts/${id}/test`),
  });

  // Refresh account data
  const refreshAccountMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.post(`/accounts/${id}/refresh`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['provider-accounts'] });
    },
  });

  return {
    // Data
    accounts,
    isLoading,
    error,

    // Actions
    refetch,
    createAccount: createAccountMutation.mutateAsync,
    updateAccount: updateAccountMutation.mutateAsync,
    deleteAccount: deleteAccountMutation.mutateAsync,
    testConnection: async (id: string) => {
      const response = await testConnectionMutation.mutateAsync(id);
      return response.data;
    },
    refreshAccount: refreshAccountMutation.mutateAsync,

    // Loading states
    isCreating: createAccountMutation.isPending,
    isUpdating: updateAccountMutation.isPending,
    isDeleting: deleteAccountMutation.isPending,
    isTesting: testConnectionMutation.isPending,
    isRefreshing: refreshAccountMutation.isPending,
  };
}

// Hook for a single provider account
export function useProviderAccount(id: string) {
  const queryClient = useQueryClient();

  const {
    data: accountResponse,
    isLoading,
    error,
  } = useQuery<ProviderAccountResponse>({
    queryKey: ['provider-account', id],
    queryFn: () => apiClient.get(`/accounts/${id}`),
    enabled: !!id,
  });

  const account = accountResponse?.data;

  return {
    account,
    isLoading,
    error,
    refetch: () => queryClient.invalidateQueries({ queryKey: ['provider-account', id] }),
  };
}

// This hook is now moved to useDiscoveredAccounts.ts for better organization