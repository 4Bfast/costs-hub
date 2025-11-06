'use client';

// Performance monitoring utilities
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics: Map<string, number> = new Map();
  private observers: Map<string, PerformanceObserver> = new Map();

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  // Measure component render time
  measureRender(componentName: string, startTime: number) {
    const endTime = performance.now();
    const duration = endTime - startTime;
    this.metrics.set(`render_${componentName}`, duration);
    
    // Log slow renders (>100ms)
    if (duration > 100) {
      console.warn(`Slow render detected: ${componentName} took ${duration.toFixed(2)}ms`);
    }
    
    return duration;
  }

  // Measure API call performance
  measureApiCall(endpoint: string, startTime: number, success: boolean = true) {
    const endTime = performance.now();
    const duration = endTime - startTime;
    const metricKey = `api_${endpoint}_${success ? 'success' : 'error'}`;
    this.metrics.set(metricKey, duration);
    
    // Log slow API calls (>2s)
    if (duration > 2000) {
      console.warn(`Slow API call: ${endpoint} took ${duration.toFixed(2)}ms`);
    }
    
    return duration;
  }

  // Measure bundle loading time
  measureBundleLoad(bundleName: string) {
    const startTime = performance.now();
    return () => {
      const duration = performance.now() - startTime;
      this.metrics.set(`bundle_${bundleName}`, duration);
      return duration;
    };
  }

  // Get Web Vitals
  observeWebVitals() {
    if (typeof window === 'undefined') return;

    // Largest Contentful Paint
    this.observeMetric('largest-contentful-paint', (entry) => {
      console.log('LCP:', entry.value);
      this.metrics.set('lcp', entry.value);
    });

    // First Input Delay
    this.observeMetric('first-input', (entry) => {
      console.log('FID:', entry.processingStart - entry.startTime);
      this.metrics.set('fid', entry.processingStart - entry.startTime);
    });

    // Cumulative Layout Shift
    this.observeMetric('layout-shift', (entry) => {
      if (!entry.hadRecentInput) {
        console.log('CLS:', entry.value);
        this.metrics.set('cls', entry.value);
      }
    });
  }

  private observeMetric(type: string, callback: (entry: any) => void) {
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          callback(entry);
        }
      });
      
      observer.observe({ type, buffered: true });
      this.observers.set(type, observer);
    } catch (error) {
      console.warn(`Failed to observe ${type}:`, error);
    }
  }

  // Get all metrics
  getMetrics() {
    return Object.fromEntries(this.metrics);
  }

  // Clear metrics
  clearMetrics() {
    this.metrics.clear();
  }

  // Disconnect all observers
  disconnect() {
    this.observers.forEach(observer => observer.disconnect());
    this.observers.clear();
  }
}

// React hook for performance monitoring
export function usePerformanceMonitor() {
  const monitor = PerformanceMonitor.getInstance();
  
  const measureRender = (componentName: string) => {
    const startTime = performance.now();
    return () => monitor.measureRender(componentName, startTime);
  };

  const measureApiCall = (endpoint: string) => {
    const startTime = performance.now();
    return (success: boolean = true) => monitor.measureApiCall(endpoint, startTime, success);
  };

  return {
    measureRender,
    measureApiCall,
    getMetrics: () => monitor.getMetrics(),
    clearMetrics: () => monitor.clearMetrics(),
  };
}

// Image optimization utilities
export function getOptimizedImageProps(src: string, alt: string, width?: number, height?: number) {
  return {
    src,
    alt,
    width,
    height,
    loading: 'lazy' as const,
    placeholder: 'blur' as const,
    blurDataURL: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAIAAoDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMDBQAAAAAAAAAAAAABAgMABAUGIWGRkqGx0f/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJagyeH0AthI5xdrLcNM91BF5pX2HaH9bcfaSXWGaRmknyJckliyjqTzSlT54b6bk+h0R//2Q==',
    sizes: width && height ? `${width}px` : '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw',
  };
}

// Preload critical resources
export function preloadCriticalResources() {
  if (typeof window === 'undefined') return;

  // Preload critical fonts
  const fontLink = document.createElement('link');
  fontLink.rel = 'preload';
  fontLink.href = '/fonts/inter-var.woff2';
  fontLink.as = 'font';
  fontLink.type = 'font/woff2';
  fontLink.crossOrigin = 'anonymous';
  document.head.appendChild(fontLink);

  // Preload critical images
  const logoLink = document.createElement('link');
  logoLink.rel = 'preload';
  logoLink.href = '/logo.svg';
  logoLink.as = 'image';
  document.head.appendChild(logoLink);
}

// Intersection Observer for lazy loading
export function createIntersectionObserver(
  callback: (entries: IntersectionObserverEntry[]) => void,
  options: IntersectionObserverInit = {}
) {
  if (typeof window === 'undefined') return null;

  const defaultOptions = {
    root: null,
    rootMargin: '50px',
    threshold: 0.1,
    ...options,
  };

  return new IntersectionObserver(callback, defaultOptions);
}