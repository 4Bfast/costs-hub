import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys, queryConfigs, invalidateQueries } from '@/lib/query-client';
import { CloudProviderAccount } from '@/types/api';
import { toast } from 'sonner';

// Get all provider accounts
export const useProviderAccounts = () => {
  return useQuery({
    queryKey: queryKeys.accounts.all(),
    queryFn: async () => {
      const response = await apiClient.get<CloudProviderAccount[]>('/accounts');
      return response.data;
    },
    ...queryConfigs.frequent,
  });
};

// Get accounts by provider
export const useAccountsByProvider = (provider: string) => {
  return useQuery({
    queryKey: queryKeys.accounts.byProvider(provider),
    queryFn: async () => {
      const response = await apiClient.get<CloudProviderAccount[]>(`/accounts?provider=${provider}`);
      return response.data;
    },
    ...queryConfigs.frequent,
    enabled: !!provider,
  });
};

// Get account details
export const useAccountDetails = (accountId: string) => {
  return useQuery({
    queryKey: queryKeys.accounts.detail(accountId),
    queryFn: async () => {
      const response = await apiClient.get<CloudProviderAccount>(`/accounts/${accountId}`);
      return response.data;
    },
    ...queryConfigs.stable,
    enabled: !!accountId,
  });
};

// Get account status and health
export const useAccountStatus = (accountId: string) => {
  return useQuery({
    queryKey: queryKeys.accounts.status(accountId),
    queryFn: async () => {
      const response = await apiClient.get<{
        status: 'active' | 'inactive' | 'error' | 'pending';
        last_sync: string | null;
        sync_status: {
          is_syncing: boolean;
          last_successful_sync: string | null;
          last_error: string | null;
          next_sync: string | null;
        };
        health_check: {
          connection_status: 'healthy' | 'unhealthy' | 'unknown';
          permissions_valid: boolean;
          last_checked: string;
          issues: string[];
        };
      }>(`/accounts/${accountId}/status`);
      return response.data;
    },
    ...queryConfigs.realTime,
    enabled: !!accountId,
    refetchInterval: 30000, // Refetch every 30 seconds for status
  });
};

// Create new provider account
export const useCreateAccount = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (accountData: {
      provider: 'aws' | 'gcp' | 'azure';
      account_id: string;
      account_name: string;
      configuration: Record<string, any>;
    }) => {
      const response = await apiClient.post<CloudProviderAccount>('/accounts', accountData);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate accounts queries
      invalidateQueries.accounts();
      
      // Add optimistic update
      queryClient.setQueryData(queryKeys.accounts.all(), (old: CloudProviderAccount[] = []) => [
        ...old,
        data,
      ]);
      
      toast.success('Account connected successfully');
    },
    onError: (error) => {
      console.error('Failed to create account:', error);
    },
  });
};

// Update account configuration
export const useUpdateAccount = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      accountId, 
      updates 
    }: { 
      accountId: string; 
      updates: Partial<CloudProviderAccount> 
    }) => {
      const response = await apiClient.patch<CloudProviderAccount>(`/accounts/${accountId}`, updates);
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Update specific account in cache
      queryClient.setQueryData(queryKeys.accounts.detail(variables.accountId), data);
      
      // Update account in the list
      queryClient.setQueryData(queryKeys.accounts.all(), (old: CloudProviderAccount[] = []) =>
        old.map((account) => (account.id === variables.accountId ? data : account))
      );
      
      toast.success('Account updated successfully');
    },
    onError: (error) => {
      console.error('Failed to update account:', error);
    },
  });
};

// Delete account
export const useDeleteAccount = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (accountId: string) => {
      await apiClient.delete(`/accounts/${accountId}`);
      return accountId;
    },
    onSuccess: (accountId) => {
      // Remove account from cache
      queryClient.setQueryData(queryKeys.accounts.all(), (old: CloudProviderAccount[] = []) =>
        old.filter((account) => account.id !== accountId)
      );
      
      // Remove account detail from cache
      queryClient.removeQueries({ queryKey: queryKeys.accounts.detail(accountId) });
      queryClient.removeQueries({ queryKey: queryKeys.accounts.status(accountId) });
      
      // Invalidate related queries
      invalidateQueries.costs();
      invalidateQueries.dashboard();
      
      toast.success('Account disconnected successfully');
    },
    onError: (error) => {
      console.error('Failed to delete account:', error);
    },
  });
};

// Test account connection
export const useTestConnection = () => {
  return useMutation({
    mutationFn: async (accountId: string) => {
      const response = await apiClient.post<{
        success: boolean;
        connection_status: 'healthy' | 'unhealthy';
        permissions_valid: boolean;
        issues: string[];
        test_results: {
          authentication: boolean;
          permissions: boolean;
          data_access: boolean;
        };
      }>(`/accounts/${accountId}/test`);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success('Connection test successful');
      } else {
        toast.error(`Connection test failed: ${data.issues.join(', ')}`);
      }
    },
    onError: (error) => {
      console.error('Connection test failed:', error);
    },
  });
};

// Sync account data
export const useSyncAccount = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (accountId: string) => {
      const response = await apiClient.post<{
        sync_job_id: string;
        status: 'started' | 'queued';
        estimated_duration: number;
      }>(`/accounts/${accountId}/sync`);
      return response.data;
    },
    onSuccess: (data, accountId) => {
      // Invalidate account status to show sync in progress
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts.status(accountId) });
      
      toast.success('Data sync started');
    },
    onError: (error) => {
      console.error('Failed to start sync:', error);
    },
  });
};

// Get discovered accounts (from FOCUS data)
export const useDiscoveredAccounts = (provider?: string) => {
  return useQuery({
    queryKey: ['accounts', 'discovered', provider],
    queryFn: async () => {
      const params = provider ? `?provider=${provider}` : '';
      const response = await apiClient.get<Array<{
        account_id: string;
        account_name?: string;
        provider: string;
        total_cost: number;
        last_seen: string;
        is_connected: boolean;
        suggested_configuration?: Record<string, any>;
      }>>(`/accounts/discovered${params}`);
      return response.data;
    },
    ...queryConfigs.frequent,
  });
};

// Refresh discovered accounts
export const useRefreshDiscoveredAccounts = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<{
        job_id: string;
        status: 'started';
        estimated_duration: number;
      }>('/accounts/discovered/refresh');
      return response.data;
    },
    onSuccess: () => {
      // Invalidate discovered accounts query
      queryClient.invalidateQueries({ queryKey: ['accounts', 'discovered'] });
      
      toast.success('Account discovery started');
    },
    onError: (error) => {
      console.error('Failed to refresh discovered accounts:', error);
    },
  });
};

// Get account cost summary
export const useAccountCostSummary = (accountId: string, period = '30d') => {
  return useQuery({
    queryKey: ['accounts', accountId, 'cost-summary', period],
    queryFn: async () => {
      const response = await apiClient.get<{
        total_cost: number;
        currency: string;
        period_start: string;
        period_end: string;
        cost_trend: Array<{ date: string; cost: number }>;
        top_services: Array<{
          service: string;
          cost: number;
          percentage: number;
        }>;
        month_over_month_change: number;
      }>(`/accounts/${accountId}/cost-summary?period=${period}`);
      return response.data;
    },
    ...queryConfigs.frequent,
    enabled: !!accountId,
  });
};