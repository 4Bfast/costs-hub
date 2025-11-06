'use client';

import { useEffect, useCallback, useRef } from 'react';
import { usePerformanceMonitor } from '@/lib/performance';
import { useBundleAnalyzer, initBundleMonitoring } from '@/lib/bundle-analyzer';
import { initWebVitals } from '@/lib/web-vitals';
// import { preloadCriticalComponents } from '@/lib/dynamic-imports';

export function usePerformanceOptimization() {
  const performanceMonitor = usePerformanceMonitor();
  const bundleAnalyzer = useBundleAnalyzer();
  const initRef = useRef(false);

  // Initialize performance monitoring
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    // Initialize Web Vitals tracking
    initWebVitals();

    // Initialize bundle monitoring
    const cleanup = initBundleMonitoring();

    // Preload critical components
    // preloadCriticalComponents();

    return cleanup;
  }, []);

  // Measure component render performance
  const measureRender = useCallback((componentName: string) => {
    return performanceMonitor.measureRender(componentName);
  }, [performanceMonitor]);

  // Measure API call performance
  const measureApiCall = useCallback((endpoint: string) => {
    return performanceMonitor.measureApiCall(endpoint);
  }, [performanceMonitor]);

  // Track chunk loading
  const trackChunkLoad = useCallback((chunkName: string) => {
    return bundleAnalyzer.trackChunkLoad(chunkName);
  }, [bundleAnalyzer]);

  // Get performance metrics
  const getMetrics = useCallback(() => {
    return {
      performance: performanceMonitor.getMetrics(),
      bundle: bundleAnalyzer.getLoadingStats(),
    };
  }, [performanceMonitor, bundleAnalyzer]);

  // Optimize images based on viewport
  const getOptimizedImageSizes = useCallback((breakpoints?: Record<string, string>) => {
    const defaultBreakpoints = {
      mobile: '(max-width: 768px) 100vw',
      tablet: '(max-width: 1200px) 50vw',
      desktop: '33vw',
    };

    const sizes = breakpoints || defaultBreakpoints;
    return Object.values(sizes).join(', ');
  }, []);

  // Preload critical resources
  const preloadResource = useCallback((href: string, as: string, type?: string) => {
    if (typeof window === 'undefined') return;

    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = href;
    link.as = as;
    if (type) link.type = type;
    if (as === 'font') link.crossOrigin = 'anonymous';
    
    document.head.appendChild(link);
  }, []);

  // Lazy load component with intersection observer
  const createLazyLoader = useCallback((
    callback: () => void,
    options: IntersectionObserverInit = {}
  ) => {
    if (typeof window === 'undefined') return () => {};

    const defaultOptions = {
      root: null,
      rootMargin: '50px',
      threshold: 0.1,
      ...options,
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          callback();
          observer.unobserve(entry.target);
        }
      });
    }, defaultOptions);

    return (element: Element) => {
      if (element) observer.observe(element);
      return () => observer.disconnect();
    };
  }, []);

  // Optimize bundle loading
  const optimizeBundleLoading = useCallback(() => {
    if (typeof window === 'undefined') return;

    // Preload critical chunks based on current route
    const path = window.location.pathname;
    const criticalChunks: Record<string, string[]> = {
      '/dashboard': ['dashboard', 'charts'],
      '/analysis': ['analysis', 'charts', 'tables'],
      '/insights': ['insights', 'ai'],
      '/connections': ['connections', 'forms'],
      '/alarms': ['alarms', 'notifications'],
    };

    const chunks = criticalChunks[path] || [];
    chunks.forEach(chunk => {
      preloadResource(`/_next/static/chunks/${chunk}.js`, 'script');
    });
  }, [preloadResource]);

  // Performance budget monitoring
  const monitorPerformanceBudget = useCallback(() => {
    const budgets = {
      LCP: 2500, // Largest Contentful Paint
      FID: 100,  // First Input Delay
      CLS: 0.1,  // Cumulative Layout Shift
      bundleSize: 1024 * 1024, // 1MB
    };

    const checkBudget = () => {
      const metrics = getMetrics();
      const violations: string[] = [];

      if (metrics.bundle.totalBundleSize > budgets.bundleSize) {
        violations.push(`Bundle size exceeds budget: ${(metrics.bundle.totalBundleSize / 1024 / 1024).toFixed(2)}MB > ${(budgets.bundleSize / 1024 / 1024).toFixed(2)}MB`);
      }

      if (violations.length > 0) {
        console.warn('Performance budget violations:', violations);
      }

      return violations;
    };

    // Check budget after page load
    if (document.readyState === 'complete') {
      setTimeout(checkBudget, 1000);
    } else {
      window.addEventListener('load', () => {
        setTimeout(checkBudget, 1000);
      });
    }
  }, [getMetrics]);

  return {
    measureRender,
    measureApiCall,
    trackChunkLoad,
    getMetrics,
    getOptimizedImageSizes,
    preloadResource,
    createLazyLoader,
    optimizeBundleLoading,
    monitorPerformanceBudget,
  };
}

// Hook for component-level performance monitoring
export function useComponentPerformance(componentName: string) {
  const { measureRender } = usePerformanceOptimization();
  const renderStartRef = useRef<number>();

  useEffect(() => {
    renderStartRef.current = performance.now();
    
    return () => {
      if (renderStartRef.current) {
        measureRender(componentName);
      }
    };
  });

  const startMeasurement = useCallback(() => {
    renderStartRef.current = performance.now();
  }, []);

  const endMeasurement = useCallback(() => {
    if (renderStartRef.current) {
      return measureRender(componentName);
    }
    return 0;
  }, [componentName, measureRender]);

  return {
    startMeasurement,
    endMeasurement,
  };
}

// Hook for image optimization
export function useImageOptimization() {
  const { getOptimizedImageSizes } = usePerformanceOptimization();

  const getResponsiveSizes = useCallback((
    sizes?: { mobile?: string; tablet?: string; desktop?: string }
  ) => {
    const defaultSizes = {
      mobile: '100vw',
      tablet: '50vw',
      desktop: '33vw',
    };

    const finalSizes = { ...defaultSizes, ...sizes };
    
    return [
      `(max-width: 768px) ${finalSizes.mobile}`,
      `(max-width: 1200px) ${finalSizes.tablet}`,
      finalSizes.desktop,
    ].join(', ');
  }, []);

  const getOptimizedProps = useCallback((
    src: string,
    alt: string,
    options: {
      width?: number;
      height?: number;
      priority?: boolean;
      quality?: number;
      sizes?: { mobile?: string; tablet?: string; desktop?: string };
    } = {}
  ) => {
    return {
      src,
      alt,
      width: options.width,
      height: options.height,
      priority: options.priority || false,
      quality: options.quality || 85,
      sizes: getResponsiveSizes(options.sizes),
      loading: options.priority ? 'eager' as const : 'lazy' as const,
      placeholder: 'blur' as const,
      blurDataURL: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAIAAoDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMDBQAAAAAAAAAAAAABAgMABAUGIWGRkqGx0f/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJagyeH0AthI5xdrLcNM91BF5pX2HaH9bcfaSXWGaRmknyJckliyjqTzSlT54b6bk+h0R//2Q==',
    };
  }, [getResponsiveSizes]);

  return {
    getResponsiveSizes,
    getOptimizedProps,
  };
}