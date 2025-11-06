import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  DiscoveredAccount, 
  AccountLinkingSuggestion, 
  DiscoveredAccountsFilters,
  DiscoveredAccountsStats 
} from '@/types/discovered-accounts';
import { ApiResponse, PaginatedResponse } from '@/types/models';
import { apiClient } from '@/lib/api-client';

interface DiscoveredAccountsResponse extends PaginatedResponse<DiscoveredAccount> {}
interface DiscoveredAccountResponse extends ApiResponse<DiscoveredAccount> {}
interface LinkingSuggestionsResponse extends ApiResponse<AccountLinkingSuggestion[]> {}
interface DiscoveredAccountsStatsResponse extends ApiResponse<DiscoveredAccountsStats> {}

export function useDiscoveredAccounts(filters?: DiscoveredAccountsFilters) {
  const queryClient = useQueryClient();

  // Build query parameters from filters
  const queryParams = new URLSearchParams();
  if (filters?.providers?.length) {
    queryParams.append('providers', filters.providers.join(','));
  }
  if (filters?.status?.length) {
    queryParams.append('status', filters.status.join(','));
  }
  if (filters?.cost_threshold) {
    queryParams.append('cost_threshold', filters.cost_threshold.toString());
  }
  if (filters?.date_range) {
    queryParams.append('start_date', filters.date_range.start);
    queryParams.append('end_date', filters.date_range.end);
  }
  if (filters?.sort_by) {
    queryParams.append('sort_by', filters.sort_by);
  }
  if (filters?.sort_order) {
    queryParams.append('sort_order', filters.sort_order);
  }

  // Fetch discovered accounts
  const {
    data: accountsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<DiscoveredAccountsResponse>({
    queryKey: ['discovered-accounts', filters],
    queryFn: async () => {
      const url = `/accounts/discovered${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      const response = await apiClient.get<DiscoveredAccount[]>(url);
      return {
        ...response,
        pagination: {
          page: 1,
          limit: 50,
          total: response.data.length,
          totalPages: 1,
          hasNext: false,
          hasPrev: false,
        }
      } as DiscoveredAccountsResponse;
    },
  });

  const accounts = accountsResponse?.data || [];
  const pagination = accountsResponse?.pagination;

  // Refresh discovered accounts (trigger new scan)
  const refreshMutation = useMutation({
    mutationFn: () => apiClient.post('/accounts/discovered/refresh'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovered-accounts'] });
      queryClient.invalidateQueries({ queryKey: ['discovered-accounts-stats'] });
    },
  });

  // Update account status (link, ignore, etc.)
  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'linked' | 'ignored' | 'discovered' }) =>
      apiClient.patch<DiscoveredAccountResponse>(`/accounts/discovered/${id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovered-accounts'] });
      queryClient.invalidateQueries({ queryKey: ['discovered-accounts-stats'] });
    },
  });

  // Link discovered account to existing provider account
  const linkAccountMutation = useMutation({
    mutationFn: ({ 
      discoveredAccountId, 
      providerAccountId 
    }: { 
      discoveredAccountId: string; 
      providerAccountId: string; 
    }) =>
      apiClient.post(`/accounts/discovered/${discoveredAccountId}/link`, {
        provider_account_id: providerAccountId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovered-accounts'] });
      queryClient.invalidateQueries({ queryKey: ['provider-accounts'] });
    },
  });

  return {
    // Data
    accounts,
    pagination,
    isLoading,
    error,

    // Actions
    refetch,
    refreshAccounts: refreshMutation.mutateAsync,
    updateStatus: updateStatusMutation.mutateAsync,
    linkAccount: linkAccountMutation.mutateAsync,

    // Loading states
    isRefreshing: refreshMutation.isPending,
    isUpdating: updateStatusMutation.isPending,
    isLinking: linkAccountMutation.isPending,
  };
}

// Hook for discovered accounts statistics
export function useDiscoveredAccountsStats() {
  const {
    data: statsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<DiscoveredAccountsStatsResponse>({
    queryKey: ['discovered-accounts-stats'],
    queryFn: () => apiClient.get('/accounts/discovered/stats'),
  });

  const stats = statsResponse?.data;

  return {
    stats,
    isLoading,
    error,
    refetch,
  };
}

// Hook for account linking suggestions
export function useAccountLinkingSuggestions() {
  const {
    data: suggestionsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<LinkingSuggestionsResponse>({
    queryKey: ['account-linking-suggestions'],
    queryFn: () => apiClient.get('/accounts/discovered/suggestions'),
  });

  const suggestions = suggestionsResponse?.data || [];

  return {
    suggestions,
    isLoading,
    error,
    refetch,
  };
}

// Hook for a single discovered account
export function useDiscoveredAccount(id: string) {
  const queryClient = useQueryClient();

  const {
    data: accountResponse,
    isLoading,
    error,
  } = useQuery<DiscoveredAccountResponse>({
    queryKey: ['discovered-account', id],
    queryFn: () => apiClient.get(`/accounts/discovered/${id}`),
    enabled: !!id,
  });

  const account = accountResponse?.data;

  return {
    account,
    isLoading,
    error,
    refetch: () => queryClient.invalidateQueries({ queryKey: ['discovered-account', id] }),
  };
}