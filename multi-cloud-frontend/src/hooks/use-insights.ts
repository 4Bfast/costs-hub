import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys, queryConfigs, invalidateQueries } from '@/lib/query-client';
import { AIInsight, QueryParams, PaginatedResponse } from '@/types/models';
import { toast } from 'sonner';

// Get all AI insights with filtering
export const useInsights = (params?: QueryParams & {
  filters?: {
    type?: string[];
    severity?: string[];
    status?: string[];
    date_range?: { start: string; end: string };
  };
}) => {
  return useQuery({
    queryKey: queryKeys.insights.list(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      
      // Pagination
      if (params?.page) searchParams.append('page', params.page.toString());
      if (params?.limit) searchParams.append('limit', params.limit.toString());
      if (params?.sort) searchParams.append('sort', params.sort);
      if (params?.order) searchParams.append('order', params.order);
      if (params?.search) searchParams.append('search', params.search);
      
      // Filters
      if (params?.filters?.type?.length) {
        searchParams.append('type', params.filters.type.join(','));
      }
      if (params?.filters?.severity?.length) {
        searchParams.append('severity', params.filters.severity.join(','));
      }
      if (params?.filters?.status?.length) {
        searchParams.append('status', params.filters.status.join(','));
      }
      if (params?.filters?.date_range) {
        searchParams.append('start_date', params.filters.date_range.start);
        searchParams.append('end_date', params.filters.date_range.end);
      }
      
      return await apiClient.getPaginated<AIInsight>(`/insights?${searchParams.toString()}`);
    },
    ...queryConfigs.frequent,
  });
};

// Get insight details
export const useInsightDetails = (insightId: string) => {
  return useQuery({
    queryKey: queryKeys.insights.detail(insightId),
    queryFn: async () => {
      const response = await apiClient.get<AIInsight>(`/insights/${insightId}`);
      return response.data;
    },
    ...queryConfigs.stable,
    enabled: !!insightId,
  });
};

// Get insights summary for dashboard
export const useInsightsSummary = () => {
  return useQuery({
    queryKey: queryKeys.insights.summary(),
    queryFn: async () => {
      const response = await apiClient.get<{
        total_insights: number;
        by_severity: {
          critical: number;
          high: number;
          medium: number;
          low: number;
        };
        by_type: {
          anomaly: number;
          recommendation: number;
          forecast: number;
          optimization: number;
        };
        by_status: {
          new: number;
          acknowledged: number;
          dismissed: number;
          implemented: number;
        };
        recent_insights: AIInsight[];
        potential_savings: number;
        top_recommendations: Array<{
          title: string;
          potential_savings: number;
          effort_level: 'low' | 'medium' | 'high';
          affected_services: string[];
        }>;
      }>('/insights/summary');
      return response.data;
    },
    ...queryConfigs.frequent,
  });
};

// Generate new insights
export const useGenerateInsights = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (options?: {
      providers?: string[];
      services?: string[];
      accounts?: string[];
      date_range?: { start: string; end: string };
      insight_types?: string[];
    }) => {
      const response = await apiClient.post<{
        job_id: string;
        status: 'started' | 'queued';
        estimated_duration: number;
        insights_generated?: number;
      }>('/insights/generate', options);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate insights queries after generation
      setTimeout(() => {
        invalidateQueries.insights();
      }, 5000); // Wait 5 seconds before invalidating
      
      toast.success('AI insight generation started');
    },
    onError: (error) => {
      console.error('Failed to generate insights:', error);
    },
  });
};

// Update insight status
export const useUpdateInsightStatus = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      insightId,
      status,
      notes,
    }: {
      insightId: string;
      status: 'acknowledged' | 'dismissed' | 'implemented';
      notes?: string;
    }) => {
      const response = await apiClient.patch<AIInsight>(`/insights/${insightId}/status`, {
        status,
        notes,
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Update insight in cache
      queryClient.setQueryData(queryKeys.insights.detail(variables.insightId), data);
      
      // Update insight in list
      queryClient.setQueryData(queryKeys.insights.list(), (old: any) => {
        if (!old) return old;
        return {
          ...old,
          data: old.data.map((insight: AIInsight) =>
            insight.id === variables.insightId ? data : insight
          ),
        };
      });
      
      // Invalidate summary
      queryClient.invalidateQueries({ queryKey: queryKeys.insights.summary() });
      
      const statusMessages = {
        acknowledged: 'Insight acknowledged',
        dismissed: 'Insight dismissed',
        implemented: 'Insight marked as implemented',
      };
      
      toast.success(statusMessages[variables.status]);
    },
    onError: (error) => {
      console.error('Failed to update insight status:', error);
    },
  });
};

// Bulk update insight status
export const useBulkUpdateInsights = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      insightIds,
      status,
      notes,
    }: {
      insightIds: string[];
      status: 'acknowledged' | 'dismissed' | 'implemented';
      notes?: string;
    }) => {
      const response = await apiClient.patch<{
        updated_count: number;
        failed_count: number;
        updated_insights: AIInsight[];
      }>('/insights/bulk-update', {
        insight_ids: insightIds,
        status,
        notes,
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Invalidate insights queries
      invalidateQueries.insights();
      
      toast.success(`${data.updated_count} insights updated successfully`);
      
      if (data.failed_count > 0) {
        toast.warning(`${data.failed_count} insights failed to update`);
      }
    },
    onError: (error) => {
      console.error('Failed to bulk update insights:', error);
    },
  });
};

// Get insight recommendations
export const useInsightRecommendations = (insightId: string) => {
  return useQuery({
    queryKey: ['insights', insightId, 'recommendations'],
    queryFn: async () => {
      const response = await apiClient.get<{
        recommendations: Array<{
          id: string;
          action: string;
          description: string;
          estimated_savings: number;
          effort_level: 'low' | 'medium' | 'high';
          implementation_steps: string[];
          risks: string[];
          prerequisites: string[];
          priority: number;
          category: string;
        }>;
        total_potential_savings: number;
      }>(`/insights/${insightId}/recommendations`);
      return response.data;
    },
    ...queryConfigs.stable,
    enabled: !!insightId,
  });
};

// Get anomaly details
export const useAnomalyDetails = (insightId: string) => {
  return useQuery({
    queryKey: ['insights', insightId, 'anomaly'],
    queryFn: async () => {
      const response = await apiClient.get<{
        anomaly_type: 'cost_spike' | 'usage_anomaly' | 'billing_anomaly';
        detection_method: string;
        confidence_score: number;
        baseline_data: {
          average_cost: number;
          standard_deviation: number;
          historical_range: { min: number; max: number };
        };
        anomaly_data: {
          detected_cost: number;
          deviation_percentage: number;
          affected_period: { start: string; end: string };
        };
        contributing_factors: Array<{
          factor: string;
          impact_percentage: number;
          description: string;
        }>;
        similar_incidents: Array<{
          date: string;
          cost_impact: number;
          resolution: string;
        }>;
      }>(`/insights/${insightId}/anomaly`);
      return response.data;
    },
    ...queryConfigs.stable,
    enabled: !!insightId,
  });
};

// Export insights
export const useExportInsights = () => {
  return useMutation({
    mutationFn: async (options: {
      format: 'csv' | 'excel' | 'json';
      filters?: {
        type?: string[];
        severity?: string[];
        status?: string[];
        date_range?: { start: string; end: string };
      };
      include_recommendations?: boolean;
    }) => {
      const response = await apiClient.post<{
        job_id: string;
        download_url?: string;
        expires_at?: string;
      }>('/insights/export', options);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.download_url) {
        // Direct download
        window.open(data.download_url, '_blank');
        toast.success('Insights exported successfully');
      } else {
        toast.success('Export started. You will be notified when ready.');
      }
    },
    onError: (error) => {
      console.error('Failed to export insights:', error);
    },
  });
};

// Get insight history
export const useInsightHistory = (insightId: string) => {
  return useQuery({
    queryKey: ['insights', insightId, 'history'],
    queryFn: async () => {
      const response = await apiClient.get<Array<{
        id: string;
        action: 'created' | 'status_changed' | 'updated' | 'deleted';
        timestamp: string;
        user_id?: string;
        user_name?: string;
        details: {
          old_status?: string;
          new_status?: string;
          notes?: string;
          changes?: Record<string, any>;
        };
      }>>(`/insights/${insightId}/history`);
      return response.data;
    },
    ...queryConfigs.stable,
    enabled: !!insightId,
  });
};

// Get insights by service
export const useInsightsByService = (service: string, limit = 10) => {
  return useQuery({
    queryKey: ['insights', 'by-service', service, limit],
    queryFn: async () => {
      const response = await apiClient.get<AIInsight[]>(`/insights/by-service/${service}?limit=${limit}`);
      return response.data || [];
    },
    ...queryConfigs.frequent,
    enabled: !!service,
  });
};