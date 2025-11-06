import { useQuery } from '@tanstack/react-query';
import { awsApiAdapter } from '@/lib/aws-api-adapter';

// Check if we're using AWS backend
const isAWSEnvironment = process.env.NEXT_PUBLIC_ENVIRONMENT === 'aws-dev';

export const useAWSDashboardMetrics = () => {
  return useQuery({
    queryKey: ['aws-dashboard-metrics'],
    queryFn: () => awsApiAdapter.getDashboardMetrics(),
    enabled: isAWSEnvironment,
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  });
};

export const useAWSServiceBreakdown = () => {
  return useQuery({
    queryKey: ['aws-service-breakdown'],
    queryFn: () => awsApiAdapter.getServiceBreakdown(),
    enabled: isAWSEnvironment,
    refetchInterval: 60000, // Refetch every minute
  });
};

export const useAWSRecentAlarms = () => {
  return useQuery({
    queryKey: ['aws-recent-alarms'],
    queryFn: () => awsApiAdapter.getRecentAlarms(),
    enabled: isAWSEnvironment,
    refetchInterval: 30000,
  });
};

export const useAWSInsightsSummary = () => {
  return useQuery({
    queryKey: ['aws-insights-summary'],
    queryFn: () => awsApiAdapter.getInsightsSummary(),
    enabled: isAWSEnvironment,
    refetchInterval: 60000,
  });
};

export const useAWSCostOverview = () => {
  return useQuery({
    queryKey: ['aws-cost-overview'],
    queryFn: () => awsApiAdapter.getCostOverview(),
    enabled: isAWSEnvironment,
    refetchInterval: 60000,
  });
};
