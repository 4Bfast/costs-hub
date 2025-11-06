import { useQuery } from '@tanstack/react-query';
import { useCostSummary, useCostTrends, useCostBreakdown, useCostRecords } from './use-costs';
import { CostFilters } from '@/types/models';

export const useCostAnalysis = (filters: CostFilters) => {
  // Get cost summary
  const {
    data: costSummary,
    isLoading: isSummaryLoading,
    error: summaryError,
    refetch: refetchSummary
  } = useCostSummary(filters);

  // Get cost trends (last 12 months by default)
  const {
    data: costTrends,
    isLoading: isTrendsLoading,
    error: trendsError,
    refetch: refetchTrends
  } = useCostTrends('12months', filters);

  // Get cost breakdown by service and provider
  const {
    data: serviceBreakdown,
    isLoading: isServiceBreakdownLoading,
    error: serviceBreakdownError,
    refetch: refetchServiceBreakdown
  } = useCostBreakdown('service', filters);

  const {
    data: providerBreakdown,
    isLoading: isProviderBreakdownLoading,
    error: providerBreakdownError,
    refetch: refetchProviderBreakdown
  } = useCostBreakdown('provider', filters);

  // Get cost records for data table
  const {
    data: costRecords,
    isLoading: isRecordsLoading,
    error: recordsError,
    refetch: refetchRecords
  } = useCostRecords({
    page: 1,
    limit: 50,
    sort: 'usage_date',
    order: 'desc',
    filters
  });

  // Combine loading states
  const isLoading = isSummaryLoading || isTrendsLoading || isServiceBreakdownLoading || 
                   isProviderBreakdownLoading || isRecordsLoading;

  // Combine errors
  const error = summaryError || trendsError || serviceBreakdownError || 
               providerBreakdownError || recordsError;

  // Refetch all data
  const refetch = () => {
    refetchSummary();
    refetchTrends();
    refetchServiceBreakdown();
    refetchProviderBreakdown();
    refetchRecords();
  };

  // Combine breakdown data
  const costBreakdown = {
    services: serviceBreakdown,
    providers: providerBreakdown
  };

  return {
    costSummary,
    costTrends,
    costBreakdown,
    costRecords,
    isLoading,
    error,
    refetch
  };
};