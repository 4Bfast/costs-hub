'use client';

import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

export interface WebVitalsMetric {
  id: string;
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  entries: PerformanceEntry[];
}

// Thresholds for Web Vitals ratings
const THRESHOLDS = {
  CLS: { good: 0.1, poor: 0.25 },
  FID: { good: 100, poor: 300 },
  FCP: { good: 1800, poor: 3000 },
  LCP: { good: 2500, poor: 4000 },
  TTFB: { good: 800, poor: 1800 },
};

function getRating(name: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  const threshold = THRESHOLDS[name as keyof typeof THRESHOLDS];
  if (!threshold) return 'good';
  
  if (value <= threshold.good) return 'good';
  if (value <= threshold.poor) return 'needs-improvement';
  return 'poor';
}

export class WebVitalsTracker {
  private static instance: WebVitalsTracker;
  private metrics: Map<string, WebVitalsMetric> = new Map();
  private callbacks: ((metric: WebVitalsMetric) => void)[] = [];

  static getInstance(): WebVitalsTracker {
    if (!WebVitalsTracker.instance) {
      WebVitalsTracker.instance = new WebVitalsTracker();
    }
    return WebVitalsTracker.instance;
  }

  init() {
    if (typeof window === 'undefined') return;

    // Track Core Web Vitals
    getCLS(this.handleMetric.bind(this));
    getFID(this.handleMetric.bind(this));
    getFCP(this.handleMetric.bind(this));
    getLCP(this.handleMetric.bind(this));
    getTTFB(this.handleMetric.bind(this));

    // Track custom metrics
    this.trackCustomMetrics();
  }

  private handleMetric(metric: any) {
    const webVitalsMetric: WebVitalsMetric = {
      ...metric,
      rating: getRating(metric.name, metric.value),
    };

    this.metrics.set(metric.name, webVitalsMetric);
    
    // Notify callbacks
    this.callbacks.forEach(callback => callback(webVitalsMetric));
    
    // Log metric
    console.log(`${metric.name}:`, {
      value: metric.value,
      rating: webVitalsMetric.rating,
      id: metric.id,
    });

    // Send to analytics
    this.sendToAnalytics(webVitalsMetric);
  }

  private trackCustomMetrics() {
    // Track page load time
    window.addEventListener('load', () => {
      const loadTime = performance.now();
      const customMetric: WebVitalsMetric = {
        id: 'page-load',
        name: 'PAGE_LOAD',
        value: loadTime,
        rating: getRating('TTFB', loadTime),
        delta: loadTime,
        entries: [],
      };
      this.handleMetric(customMetric);
    });

    // Track navigation timing
    if ('navigation' in performance) {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      if (navigation) {
        const domContentLoaded = navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
        const customMetric: WebVitalsMetric = {
          id: 'dom-content-loaded',
          name: 'DCL',
          value: domContentLoaded,
          rating: getRating('FCP', domContentLoaded),
          delta: domContentLoaded,
          entries: [navigation],
        };
        this.handleMetric(customMetric);
      }
    }
  }

  private sendToAnalytics(metric: WebVitalsMetric) {
    // Send to Google Analytics 4
    if (typeof window !== 'undefined' && 'gtag' in window) {
      // @ts-ignore
      window.gtag('event', metric.name, {
        event_category: 'Web Vitals',
        event_label: metric.id,
        value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
        custom_map: {
          metric_rating: metric.rating,
        },
      });
    }

    // Send to custom analytics endpoint
    if (process.env.NODE_ENV === 'production') {
      fetch('/api/analytics/web-vitals', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metric: metric.name,
          value: metric.value,
          rating: metric.rating,
          id: metric.id,
          url: window.location.href,
          userAgent: navigator.userAgent,
          timestamp: Date.now(),
        }),
      }).catch(error => {
        console.warn('Failed to send Web Vitals to analytics:', error);
      });
    }
  }

  onMetric(callback: (metric: WebVitalsMetric) => void) {
    this.callbacks.push(callback);
  }

  getMetrics(): WebVitalsMetric[] {
    return Array.from(this.metrics.values());
  }

  getMetric(name: string): WebVitalsMetric | undefined {
    return this.metrics.get(name);
  }
}

// React hook for Web Vitals
export function useWebVitals() {
  const tracker = WebVitalsTracker.getInstance();
  
  const getMetrics = () => tracker.getMetrics();
  const getMetric = (name: string) => tracker.getMetric(name);
  
  return {
    getMetrics,
    getMetric,
    onMetric: (callback: (metric: WebVitalsMetric) => void) => tracker.onMetric(callback),
  };
}

// Performance budget checker
export class PerformanceBudget {
  private budgets = {
    LCP: 2500, // 2.5s
    FID: 100,  // 100ms
    CLS: 0.1,  // 0.1
    FCP: 1800, // 1.8s
    TTFB: 800, // 800ms
  };

  checkBudget(metric: WebVitalsMetric): boolean {
    const budget = this.budgets[metric.name as keyof typeof this.budgets];
    if (!budget) return true;
    
    const withinBudget = metric.value <= budget;
    
    if (!withinBudget) {
      console.warn(`Performance budget exceeded for ${metric.name}:`, {
        value: metric.value,
        budget,
        overage: metric.value - budget,
      });
    }
    
    return withinBudget;
  }

  setBudget(metric: string, value: number) {
    this.budgets[metric as keyof typeof this.budgets] = value;
  }
}

// Initialize Web Vitals tracking
export function initWebVitals() {
  if (typeof window === 'undefined') return;
  
  const tracker = WebVitalsTracker.getInstance();
  const budget = new PerformanceBudget();
  
  tracker.init();
  
  // Check performance budgets
  tracker.onMetric((metric) => {
    budget.checkBudget(metric);
  });
}