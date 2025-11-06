'use client';

import { Suspense, lazy, ComponentType } from 'react';
import { Skeleton } from './skeleton';
import { createIntersectionObserver } from '@/lib/performance';
import { useState, useRef, useEffect } from 'react';

interface LazyComponentProps {
  fallback?: React.ReactNode;
  children: React.ReactNode;
  threshold?: number;
  rootMargin?: string;
}

// Generic lazy loading wrapper with intersection observer
export function LazyComponent({ 
  fallback = <Skeleton className="h-32 w-full" />, 
  children, 
  threshold = 0.1,
  rootMargin = '50px'
}: LazyComponentProps) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = createIntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer?.disconnect();
          }
        });
      },
      { threshold, rootMargin }
    );

    if (ref.current && observer) {
      observer.observe(ref.current);
    }

    return () => observer?.disconnect();
  }, [threshold, rootMargin]);

  return (
    <div ref={ref}>
      {isVisible ? children : fallback}
    </div>
  );
}

// HOC for lazy loading components
export function withLazyLoading<P extends object>(
  Component: ComponentType<P>,
  fallback?: React.ReactNode
) {
  return function LazyLoadedComponent(props: P) {
    return (
      <LazyComponent fallback={fallback}>
        <Component {...props} />
      </LazyComponent>
    );
  };
}

// Lazy loading wrapper for dynamic imports
export function createLazyComponent<P extends Record<string, any>>(
  importFn: () => Promise<{ default: ComponentType<P> }>,
  fallback?: React.ReactNode
) {
  const LazyComp = lazy(importFn);
  
  return function LazyWrapper(props: P) {
    return (
      <Suspense fallback={fallback || <Skeleton className="h-32 w-full" />}>
        <LazyComp {...(props as any)} />
      </Suspense>
    );
  };
}

// Preload component for critical above-the-fold content
export function PreloadComponent({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

// Progressive loading component for lists
interface ProgressiveListProps {
  items: any[];
  renderItem: (item: any, index: number) => React.ReactNode;
  batchSize?: number;
  loadingComponent?: React.ReactNode;
}

export function ProgressiveList({ 
  items, 
  renderItem, 
  batchSize = 10,
  loadingComponent = <Skeleton className="h-16 w-full" />
}: ProgressiveListProps) {
  const [visibleCount, setVisibleCount] = useState(batchSize);
  const [isLoading, setIsLoading] = useState(false);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = createIntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && visibleCount < items.length && !isLoading) {
            setIsLoading(true);
            // Simulate loading delay for better UX
            setTimeout(() => {
              setVisibleCount(prev => Math.min(prev + batchSize, items.length));
              setIsLoading(false);
            }, 100);
          }
        });
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current && observer) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer?.disconnect();
  }, [visibleCount, items.length, batchSize, isLoading]);

  return (
    <div>
      {items.slice(0, visibleCount).map((item, index) => (
        <div key={index}>
          {renderItem(item, index)}
        </div>
      ))}
      
      {visibleCount < items.length && (
        <div ref={loadMoreRef} className="py-4">
          {isLoading ? loadingComponent : null}
        </div>
      )}
    </div>
  );
}