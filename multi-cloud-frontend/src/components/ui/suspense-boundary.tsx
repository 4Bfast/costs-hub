'use client';

import { Suspense, ReactNode } from 'react';
import { ErrorBoundary } from '@/components/error-boundary';
import { 
  Skeleton, 
  SkeletonSpinner, 
  ChartSkeleton, 
  TableSkeleton, 
  CardSkeleton,
  PageSkeleton,
  ProgressiveSkeleton 
} from '@/components/ui/skeleton';

interface SuspenseBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  errorFallback?: ReactNode;
  name?: string;
}

// Generic suspense boundary with error handling
export function SuspenseBoundary({ 
  children, 
  fallback, 
  errorFallback,
  name = 'Component'
}: SuspenseBoundaryProps) {
  const defaultFallback = (
    <div className="flex items-center justify-center p-8">
      <SkeletonSpinner size="lg" />
    </div>
  );

  const defaultErrorFallback = (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="text-muted-foreground mb-2">
        Failed to load {name}
      </div>
      <button 
        onClick={() => window.location.reload()}
        className="text-primary hover:underline text-sm"
      >
        Try again
      </button>
    </div>
  );

  return (
    <ErrorBoundary fallback={errorFallback || defaultErrorFallback}>
      <Suspense fallback={fallback || defaultFallback}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}

// Specialized suspense boundaries for different content types
export function ChartSuspense({ children, name = 'Chart' }: { children: ReactNode; name?: string }) {
  return (
    <SuspenseBoundary
      fallback={<ChartSkeleton />}
      errorFallback={
        <div className="flex items-center justify-center h-64 border border-dashed border-muted-foreground/25 rounded-lg">
          <div className="text-center text-muted-foreground">
            <div className="mb-2">Failed to load {name}</div>
            <button 
              onClick={() => window.location.reload()}
              className="text-primary hover:underline text-sm"
            >
              Retry
            </button>
          </div>
        </div>
      }
      name={name}
    >
      {children}
    </SuspenseBoundary>
  );
}

export function TableSuspense({ children, name = 'Table' }: { children: ReactNode; name?: string }) {
  return (
    <SuspenseBoundary
      fallback={<TableSkeleton />}
      errorFallback={
        <div className="flex items-center justify-center p-8 border border-dashed border-muted-foreground/25 rounded-lg">
          <div className="text-center text-muted-foreground">
            <div className="mb-2">Failed to load {name}</div>
            <button 
              onClick={() => window.location.reload()}
              className="text-primary hover:underline text-sm"
            >
              Retry
            </button>
          </div>
        </div>
      }
      name={name}
    >
      {children}
    </SuspenseBoundary>
  );
}

export function CardSuspense({ children, name = 'Card' }: { children: ReactNode; name?: string }) {
  return (
    <SuspenseBoundary
      fallback={<CardSkeleton />}
      errorFallback={
        <div className="p-6 border border-dashed border-muted-foreground/25 rounded-lg">
          <div className="text-center text-muted-foreground">
            <div className="mb-2">Failed to load {name}</div>
            <button 
              onClick={() => window.location.reload()}
              className="text-primary hover:underline text-sm"
            >
              Retry
            </button>
          </div>
        </div>
      }
      name={name}
    >
      {children}
    </SuspenseBoundary>
  );
}

export function PageSuspense({ children, name = 'Page' }: { children: ReactNode; name?: string }) {
  return (
    <SuspenseBoundary
      fallback={<PageSkeleton />}
      errorFallback={
        <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
          <div className="text-lg font-medium text-muted-foreground mb-2">
            Failed to load {name}
          </div>
          <div className="text-sm text-muted-foreground mb-4">
            Something went wrong while loading this page
          </div>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Reload Page
          </button>
        </div>
      }
      name={name}
    >
      {children}
    </SuspenseBoundary>
  );
}

// Progressive loading suspense with stages
export function ProgressiveSuspense({ 
  children, 
  stages = 3,
  name = 'Content'
}: { 
  children: ReactNode; 
  stages?: number;
  name?: string;
}) {
  return (
    <SuspenseBoundary
      fallback={<ProgressiveSkeleton totalStages={stages} stage={1} />}
      errorFallback={
        <div className="flex items-center justify-center p-8">
          <div className="text-center text-muted-foreground">
            <div className="mb-2">Failed to load {name}</div>
            <button 
              onClick={() => window.location.reload()}
              className="text-primary hover:underline text-sm"
            >
              Try again
            </button>
          </div>
        </div>
      }
      name={name}
    >
      {children}
    </SuspenseBoundary>
  );
}

// Lazy loading wrapper with intersection observer
export function LazyLoadSuspense({ 
  children, 
  fallback,
  rootMargin = '100px',
  name = 'Component'
}: { 
  children: ReactNode; 
  fallback?: ReactNode;
  rootMargin?: string;
  name?: string;
}) {
  return (
    <div className="lazy-load-container">
      <SuspenseBoundary
        fallback={fallback || <Skeleton className="h-32" />}
        name={name}
      >
        {children}
      </SuspenseBoundary>
    </div>
  );
}

// Nested suspense for complex layouts
export function NestedSuspense({ 
  children,
  level = 1,
  name = 'Nested Content'
}: { 
  children: ReactNode;
  level?: number;
  name?: string;
}) {
  const getFallback = (level: number) => {
    switch (level) {
      case 1:
        return <PageSkeleton />;
      case 2:
        return <CardSkeleton />;
      case 3:
        return <Skeleton className="h-16" />;
      default:
        return <SkeletonSpinner />;
    }
  };

  return (
    <SuspenseBoundary
      fallback={getFallback(level)}
      name={`${name} (Level ${level})`}
    >
      {children}
    </SuspenseBoundary>
  );
}