import React from 'react';
import { LoadingState } from './loading-state';
import { ErrorState } from './error-state';
import { EmptyState } from './empty-state';

interface DataWrapperProps {
  isLoading?: boolean;
  error?: Error | string | null;
  data?: any;
  isEmpty?: boolean;
  children: React.ReactNode;
  
  // Loading props
  loadingType?: 'cards' | 'table' | 'chart' | 'page';
  loadingCount?: number;
  
  // Error props
  errorTitle?: string;
  errorMessage?: string;
  onRetry?: () => void;
  
  // Empty props
  emptyTitle?: string;
  emptyMessage?: string;
  emptyIcon?: 'file' | 'search' | 'plus';
  emptyActionLabel?: string;
  onEmptyAction?: () => void;
  showEmptyAction?: boolean;
  
  // Custom empty check function
  checkEmpty?: (data: any) => boolean;
}

export function DataWrapper({
  isLoading = false,
  error = null,
  data,
  isEmpty,
  children,
  
  // Loading props
  loadingType = 'cards',
  loadingCount = 3,
  
  // Error props
  errorTitle = "Failed to load data",
  errorMessage = "We couldn't load the data. Please try again.",
  onRetry,
  
  // Empty props
  emptyTitle = "No data available",
  emptyMessage = "There's no data to display at the moment.",
  emptyIcon = 'file',
  emptyActionLabel = "Add Data",
  onEmptyAction,
  showEmptyAction = false,
  
  // Custom empty check
  checkEmpty
}: DataWrapperProps) {
  
  // Handle loading state
  if (isLoading) {
    return <LoadingState type={loadingType} count={loadingCount} />;
  }
  
  // Handle error state
  if (error) {
    const errorMsg = typeof error === 'string' ? error : error.message;
    return (
      <ErrorState
        title={errorTitle}
        message={errorMsg || errorMessage}
        onRetry={onRetry}
        showRetry={!!onRetry}
      />
    );
  }
  
  // Handle empty state
  const isDataEmpty = isEmpty !== undefined 
    ? isEmpty 
    : checkEmpty 
      ? checkEmpty(data)
      : !data || 
        (Array.isArray(data) && data.length === 0) ||
        (typeof data === 'object' && Object.keys(data).length === 0);
  
  if (isDataEmpty) {
    return (
      <EmptyState
        title={emptyTitle}
        message={emptyMessage}
        icon={emptyIcon}
        actionLabel={emptyActionLabel}
        onAction={onEmptyAction}
        showAction={showEmptyAction}
      />
    );
  }
  
  // Render children when data is available
  return <>{children}</>;
}

// Convenience hooks for common patterns
export function useDataState<T>(
  data: T | undefined,
  isLoading: boolean,
  error: Error | null
) {
  const isEmpty = !data || 
    (Array.isArray(data) && data.length === 0) ||
    (typeof data === 'object' && Object.keys(data).length === 0);
  
  return {
    isLoading,
    error,
    isEmpty,
    hasData: !isEmpty && !isLoading && !error
  };
}
