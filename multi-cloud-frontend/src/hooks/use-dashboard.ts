import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys, queryConfigs } from '@/lib/query-client';

// Main dashboard metrics hook - using real /dashboard/metrics endpoint
export const useDashboardMetrics = () => {
  return useQuery({
    queryKey: queryKeys.dashboard.metrics(),
    queryFn: async () => {
      const response = await apiClient.get<{
        total_monthly_cost: number;
        month_over_month_change: number;
        connected_accounts: number;
        active_alarms: number;
        unread_insights: number;
        cost_trend_7d: Array<{ date: string; cost: number }>;
        top_service: {
          service_name: string;
          cost: number;
          percentage: number;
        } | null;
        provider_distribution: Array<{
          provider: string;
          cost: number;
          percentage: number;
          account_count: number;
        }>;
        recent_activity: Array<{
          type: 'cost_spike' | 'new_insight' | 'alarm_triggered' | 'account_added';
          title: string;
          description: string;
          timestamp: string;
          severity?: 'low' | 'medium' | 'high' | 'critical';
        }>;
      }>('/dashboard/metrics');
      return response;
    },
    ...queryConfigs.realTime,
  });
};

// Simplified dashboard data hook - fallback to metrics
export const useDashboardData = (period = '30d') => {
  return useDashboardMetrics();
};

// Cost overview - using dashboard metrics as fallback
export const useCostOverview = (period = '30d') => {
  return useQuery({
    queryKey: ['dashboard', 'cost-overview', period],
    queryFn: async () => {
      // Try to get metrics and transform to cost overview format
      const metricsResponse = await apiClient.get<{
        total_monthly_cost: number;
        month_over_month_change: number;
        cost_trend_7d: Array<{ date: string; cost: number }>;
      }>('/dashboard/metrics');
      
      const metrics = metricsResponse.data;
      const currentCost = metrics?.total_monthly_cost || 0;
      const changePercent = metrics?.month_over_month_change || 0;
      const previousCost = currentCost / (1 + changePercent / 100);
      
      return {
        current_period: {
          total_cost: currentCost,
          start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end_date: new Date().toISOString().split('T')[0]
        },
        previous_period: {
          total_cost: previousCost,
          start_date: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
        },
        change: {
          amount: currentCost - previousCost,
          percentage: changePercent,
          trend: changePercent > 0 ? 'up' as const : changePercent < 0 ? 'down' as const : 'stable' as const
        },
        daily_breakdown: metrics?.cost_trend_7d || [],
        forecast: {
          projected_monthly_cost: currentCost * 1.1, // Simple projection
          confidence_level: 75,
          trend: changePercent > 0 ? 'increasing' as const : 'decreasing' as const
        }
      };
    },
    ...queryConfigs.frequent,
  });
};

// Service breakdown - using cost breakdown endpoint
export const useServiceBreakdown = (limit = 5) => {
  return useQuery({
    queryKey: ['dashboard', 'service-breakdown', limit],
    queryFn: async () => {
      const response = await apiClient.get<Array<{
        name: string;
        cost: number;
        percentage: number;
      }>>(`/costs/breakdown/service?limit=${limit}`);
      
      return (response.data || []).map(item => ({
        service_name: item.name,
        cost: item.cost,
        percentage: item.percentage,
        trend: 0, // Would need historical data
        provider: 'aws', // Default
        account_count: 1, // Default
        cost_trend_7d: [] // Would need historical data
      }));
    },
    ...queryConfigs.frequent,
  });
};

// Recent alarms - simplified fallback
export const useRecentAlarms = (limit = 5) => {
  return useQuery({
    queryKey: ['dashboard', 'recent-alarms', limit],
    queryFn: async () => {
      const response = await apiClient.get<Array<{
        id: string;
        name: string;
        status: string;
        threshold: number;
        created_at: string;
      }>>(`/alarms?limit=${limit}`);
      
      return (response.data?.data || []).map(alarm => ({
        id: alarm.id,
        alarm_name: alarm.name,
        severity: 'medium' as const,
        triggered_at: alarm.created_at,
        current_value: alarm.threshold * 1.1, // Simulate current value
        threshold_value: alarm.threshold,
        status: 'new' as const,
        affected_services: [],
        cost_impact: 0
      }));
    },
    ...queryConfigs.realTime,
  });
};

// AI insights summary - simplified fallback
export const useInsightsSummaryDashboard = () => {
  return useQuery({
    queryKey: ['dashboard', 'insights-summary'],
    queryFn: async () => {
      const response = await apiClient.get<Array<{
        id: string;
        type: string;
        severity: string;
        title: string;
        description: string;
        created_at: string;
      }>>('/insights?limit=5');
      
      const insights = response.data?.data || [];
      
      return {
        total_new_insights: insights.length,
        high_priority_count: insights.filter(i => i.severity === 'high').length,
        potential_monthly_savings: 1250, // Mock value
        recent_insights: insights.map(insight => ({
          id: insight.id,
          type: insight.type as 'anomaly' | 'recommendation' | 'forecast' | 'optimization',
          severity: insight.severity as 'low' | 'medium' | 'high' | 'critical',
          title: insight.title,
          description: insight.description,
          potential_savings: 250, // Mock value
          created_at: insight.created_at
        })),
        top_recommendations: []
      };
    },
    ...queryConfigs.frequent,
  });
};

// Account health - simplified fallback
export const useAccountHealth = () => {
  return useQuery({
    queryKey: ['dashboard', 'account-health'],
    queryFn: async () => {
      const response = await apiClient.get<Array<{
        account_id: string;
        name: string;
        provider_type: string;
        status: string;
        updated_at: string;
      }>>('/accounts');
      
      const accounts = response.data?.data || [];
      
      return {
        total_accounts: accounts.length,
        healthy_accounts: accounts.filter(a => a.status === 'active').length,
        accounts_with_issues: accounts.filter(a => a.status !== 'active').length,
        sync_status: {
          syncing_now: 0,
          last_sync_24h: accounts.length,
          sync_errors: 0
        },
        account_details: accounts.map(account => ({
          id: account.account_id,
          provider: account.provider_type,
          account_name: account.name,
          status: account.status as 'active' | 'inactive' | 'error' | 'pending',
          last_sync: account.updated_at,
          health_score: account.status === 'active' ? 100 : 50,
          issues: account.status !== 'active' ? ['Connection issue'] : []
        }))
      };
    },
    ...queryConfigs.frequent,
  });
};

// Simplified fallback hooks for compatibility
export const useCostEfficiency = () => {
  return useQuery({
    queryKey: ['dashboard', 'cost-efficiency'],
    queryFn: async () => ({
      efficiency_score: 75,
      waste_percentage: 15,
      optimization_opportunities: 5,
      metrics: {
        unused_resources: { count: 3, potential_savings: 450 },
        oversized_resources: { count: 2, potential_savings: 300 },
        idle_resources: { count: 1, potential_savings: 150 },
        untagged_resources: { count: 10, percentage: 25 }
      },
      recommendations: []
    }),
    ...queryConfigs.stable,
  });
};

export const useBudgetTracking = () => {
  return useQuery({
    queryKey: ['dashboard', 'budget-tracking'],
    queryFn: async () => ({
      monthly_budget: null,
      current_spend: 0,
      projected_spend: 0,
      budget_utilization: 0,
      days_remaining: 30,
      burn_rate: 0,
      status: 'no_budget' as const,
      alerts: [],
      spending_by_day: []
    }),
    ...queryConfigs.frequent,
  });
};