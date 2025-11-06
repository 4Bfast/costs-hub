import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys, queryConfigs, invalidateQueries } from '@/lib/query-client';
import { CostRecord, CostSummary, CostFilters, QueryParams, CostTrendPoint, CloudProvider, PaginatedResponse } from '@/types/models';

// Cost summary hook - using real /costs/records endpoint
export const useCostSummary = (filters?: CostFilters) => {
  return useQuery({
    queryKey: queryKeys.costs.summary(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', '1000'); // Get more records for summary
      
      if (filters?.date_range) {
        params.append('start_date', filters.date_range.start);
        params.append('end_date', filters.date_range.end);
      }
      if (filters?.providers?.length) {
        params.append('providers', filters.providers.join(','));
      }
      if (filters?.services?.length) {
        params.append('services', filters.services.join(','));
      }
      if (filters?.accounts?.length) {
        params.append('accounts', filters.accounts.join(','));
      }
      
      // Use real endpoint and calculate summary from records
      const response = await apiClient.get<PaginatedResponse<CostRecord>>(`/costs/records?${params.toString()}`);
      
      // Calculate summary from records with fallbacks
      const records = response.data?.data || [];
      const totalCost = records.reduce((sum, record) => sum + (record.cost || 0), 0);
      
      // Group by service with fallbacks
      const serviceBreakdown = records.reduce((acc, record) => {
        const service = record.service || 'Unknown';
        acc[service] = (acc[service] || 0) + (record.cost || 0);
        return acc;
      }, {} as Record<string, number>);
      
      // Group by provider with fallbacks
      const providerBreakdown = records.reduce((acc, record) => {
        const provider = record.provider || 'Unknown';
        acc[provider] = (acc[provider] || 0) + (record.cost || 0);
        return acc;
      }, {} as Record<string, number>);
      
      // Group by account with fallbacks
      const accountBreakdown = records.reduce((acc, record) => {
        const account = record.account_id || 'Unknown';
        acc[account] = (acc[account] || 0) + (record.cost || 0);
        return acc;
      }, {} as Record<string, number>);
      
      return {
        total_cost: totalCost,
        month_over_month_change: 0, // Would need historical data
        service_breakdown: Object.entries(serviceBreakdown).map(([service, cost]) => ({
          service,
          cost,
          percentage: totalCost > 0 ? (cost / totalCost) * 100 : 0
        })),
        provider_breakdown: Object.entries(providerBreakdown).map(([provider, cost]) => ({
          provider,
          cost,
          percentage: totalCost > 0 ? (cost / totalCost) * 100 : 0
        })),
        account_breakdown: Object.entries(accountBreakdown).map(([account, cost]) => ({
          account,
          cost,
          percentage: totalCost > 0 ? (cost / totalCost) * 100 : 0
        }))
      };
    },
    ...queryConfigs.frequent,
  });
};

// Cost records hook with pagination
export const useCostRecords = (params?: QueryParams & { filters?: CostFilters }) => {
  return useQuery({
    queryKey: queryKeys.costs.records(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      
      // Pagination
      if (params?.page) searchParams.append('page', params.page.toString());
      if (params?.limit) searchParams.append('limit', params.limit.toString());
      if (params?.sort) searchParams.append('sort', params.sort);
      if (params?.order) searchParams.append('order', params.order);
      if (params?.search) searchParams.append('search', params.search);
      
      // Filters
      if (params?.filters?.date_range) {
        searchParams.append('start_date', params.filters.date_range.start);
        searchParams.append('end_date', params.filters.date_range.end);
      }
      if (params?.filters?.providers?.length) {
        searchParams.append('providers', params.filters.providers.join(','));
      }
      if (params?.filters?.services?.length) {
        searchParams.append('services', params.filters.services.join(','));
      }
      if (params?.filters?.accounts?.length) {
        searchParams.append('accounts', params.filters.accounts.join(','));
      }
      if (params?.filters?.cost_range) {
        searchParams.append('min_cost', params.filters.cost_range.min.toString());
        searchParams.append('max_cost', params.filters.cost_range.max.toString());
      }
      
      return await apiClient.getPaginated<CostRecord>(`/costs/records?${searchParams.toString()}`);
    },
    ...queryConfigs.frequent,
  });
};

// Cost trends hook - using /costs/records to calculate trends
export const useCostTrends = (period: string, filters?: CostFilters) => {
  return useQuery({
    queryKey: queryKeys.costs.trends(period, filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', '1000');
      params.append('sort', 'usage_date');
      params.append('order', 'asc');
      
      if (filters?.date_range) {
        params.append('start_date', filters.date_range.start);
        params.append('end_date', filters.date_range.end);
      }
      if (filters?.providers?.length) {
        params.append('providers', filters.providers.join(','));
      }
      if (filters?.services?.length) {
        params.append('services', filters.services.join(','));
      }
      if (filters?.accounts?.length) {
        params.append('accounts', filters.accounts.join(','));
      }
      
      // Get records and calculate daily trends
      const response = await apiClient.get<PaginatedResponse<CostRecord>>(`/costs/records?${params.toString()}`);
      const records = response.data?.data || [];
      
      // Group by date and calculate daily costs
      const dailyCosts = records.reduce((acc, record) => {
        const date = record.usage_date || new Date().toISOString().split('T')[0];
        acc[date] = (acc[date] || 0) + (record.cost || 0);
        return acc;
      }, {} as Record<string, number>);
      
      // Convert to trend points
      return Object.entries(dailyCosts)
        .map(([date, cost]) => ({ date, cost }))
        .sort((a, b) => a.date.localeCompare(b.date));
    },
    ...queryConfigs.frequent,
  });
};

// Cost breakdown hook - using real /costs/breakdown endpoints
export const useCostBreakdown = (type: 'provider' | 'service' | 'account', filters?: CostFilters) => {
  return useQuery({
    queryKey: queryKeys.costs.breakdown(type, filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      
      if (filters?.date_range) {
        params.append('start_date', filters.date_range.start);
        params.append('end_date', filters.date_range.end);
      }
      if (filters?.providers?.length) {
        params.append('providers', filters.providers.join(','));
      }
      if (filters?.services?.length) {
        params.append('services', filters.services.join(','));
      }
      if (filters?.accounts?.length) {
        params.append('accounts', filters.accounts.join(','));
      }
      
      // Use real breakdown endpoint
      const response = await apiClient.get<Array<{ 
        name: string; 
        cost: number; 
        percentage: number; 
        trend?: number 
      }>>(`/costs/breakdown/${type}?${params.toString()}`);
      
      return response.data || [];
    },
    ...queryConfigs.frequent,
  });
};

// Export cost data mutation - using real /costs/export endpoint
export const useExportCosts = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (exportRequest: {
      format: 'csv' | 'excel' | 'pdf';
      filters?: CostFilters;
      columns?: string[];
    }) => {
      const response = await apiClient.post<{ 
        job_id: string; 
        status: string;
        download_url?: string;
        message?: string;
      }>('/costs/export', exportRequest);
      return response.data;
    },
    onSuccess: () => {
      // Optionally invalidate related queries
      // invalidateQueries.costs();
    },
  });
};

// Cost forecast hook
export const useCostForecast = (period: string, filters?: CostFilters) => {
  return useQuery({
    queryKey: ['costs', 'forecast', period, filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('period', period);
      
      if (filters?.providers?.length) {
        params.append('providers', filters.providers.join(','));
      }
      if (filters?.services?.length) {
        params.append('services', filters.services.join(','));
      }
      if (filters?.accounts?.length) {
        params.append('accounts', filters.accounts.join(','));
      }
      
      const response = await apiClient.get<Array<{
        date: string;
        predicted_cost: number;
        confidence_lower: number;
        confidence_upper: number;
      }>>(`/costs/forecast?${params.toString()}`);
      return response.data;
    },
    ...queryConfigs.stable,
  });
};

// Top services hook
export const useTopServices = (limit = 10, filters?: CostFilters) => {
  return useQuery({
    queryKey: ['costs', 'top-services', limit, filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', limit.toString());
      
      if (filters?.date_range) {
        params.append('start_date', filters.date_range.start);
        params.append('end_date', filters.date_range.end);
      }
      if (filters?.providers?.length) {
        params.append('providers', filters.providers.join(','));
      }
      if (filters?.accounts?.length) {
        params.append('accounts', filters.accounts.join(','));
      }
      
      const response = await apiClient.get<Array<{
        service: string;
        cost: number;
        percentage: number;
        trend: number;
        account_count: number;
      }>>(`/costs/top-services?${params.toString()}`);
      return response.data;
    },
    ...queryConfigs.frequent,
  });
};

// Cost comparison hook
export const useCostComparison = (
  currentPeriod: { start: string; end: string },
  comparisonPeriod: { start: string; end: string },
  filters?: CostFilters
) => {
  return useQuery({
    queryKey: ['costs', 'comparison', currentPeriod, comparisonPeriod, filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('current_start', currentPeriod.start);
      params.append('current_end', currentPeriod.end);
      params.append('comparison_start', comparisonPeriod.start);
      params.append('comparison_end', comparisonPeriod.end);
      
      if (filters?.providers?.length) {
        params.append('providers', filters.providers.join(','));
      }
      if (filters?.services?.length) {
        params.append('services', filters.services.join(','));
      }
      if (filters?.accounts?.length) {
        params.append('accounts', filters.accounts.join(','));
      }
      
      const response = await apiClient.get<{
        current_total: number;
        comparison_total: number;
        change_amount: number;
        change_percentage: number;
        breakdown: Array<{
          category: string;
          current_cost: number;
          comparison_cost: number;
          change_amount: number;
          change_percentage: number;
        }>;
      }>(`/costs/comparison?${params.toString()}`);
      return response.data;
    },
    ...queryConfigs.frequent,
  });
};