'use client';

// Bundle analysis and optimization utilities
export class BundleAnalyzer {
  private static instance: BundleAnalyzer;
  private loadTimes: Map<string, number> = new Map();
  private bundleSizes: Map<string, number> = new Map();
  private loadedChunks: Set<string> = new Set();

  static getInstance(): BundleAnalyzer {
    if (!BundleAnalyzer.instance) {
      BundleAnalyzer.instance = new BundleAnalyzer();
    }
    return BundleAnalyzer.instance;
  }

  // Track chunk loading performance
  trackChunkLoad(chunkName: string, startTime: number) {
    const endTime = performance.now();
    const loadTime = endTime - startTime;
    
    this.loadTimes.set(chunkName, loadTime);
    this.loadedChunks.add(chunkName);
    
    // Log slow chunk loads
    if (loadTime > 1000) {
      console.warn(`Slow chunk load: ${chunkName} took ${loadTime.toFixed(2)}ms`);
    }
    
    // Send to analytics
    this.sendChunkMetrics(chunkName, loadTime);
    
    return loadTime;
  }

  // Analyze bundle composition
  analyzeBundleComposition() {
    if (typeof window === 'undefined') return null;

    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const jsResources = resources.filter(resource => 
      resource.name.includes('.js') && 
      (resource.name.includes('_next/static') || resource.name.includes('chunks'))
    );

    const analysis = {
      totalChunks: jsResources.length,
      totalSize: jsResources.reduce((sum, resource) => sum + (resource.transferSize || 0), 0),
      largestChunk: jsResources.reduce((largest, resource) => 
        (resource.transferSize || 0) > (largest.transferSize || 0) ? resource : largest
      ),
      slowestChunk: jsResources.reduce((slowest, resource) => 
        resource.duration > slowest.duration ? resource : slowest
      ),
      chunks: jsResources.map(resource => ({
        name: this.extractChunkName(resource.name),
        size: resource.transferSize || 0,
        loadTime: resource.duration,
        cached: resource.transferSize === 0,
      })),
    };

    console.log('Bundle Analysis:', analysis);
    return analysis;
  }

  // Extract chunk name from URL
  private extractChunkName(url: string): string {
    const match = url.match(/\/([^\/]+)\.js$/);
    return match ? match[1] : 'unknown';
  }

  // Send metrics to analytics
  private sendChunkMetrics(chunkName: string, loadTime: number) {
    if (process.env.NODE_ENV === 'production') {
      // Send to analytics service
      fetch('/api/analytics/bundle-performance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chunkName,
          loadTime,
          timestamp: Date.now(),
          userAgent: navigator.userAgent,
          url: window.location.href,
        }),
      }).catch(error => {
        console.warn('Failed to send bundle metrics:', error);
      });
    }
  }

  // Get performance recommendations
  getPerformanceRecommendations() {
    const recommendations: string[] = [];
    
    // Check for slow chunks
    this.loadTimes.forEach((loadTime, chunkName) => {
      if (loadTime > 1000) {
        recommendations.push(`Consider code splitting for ${chunkName} (${loadTime.toFixed(0)}ms load time)`);
      }
    });

    // Check bundle size
    const totalSize = Array.from(this.bundleSizes.values()).reduce((sum, size) => sum + size, 0);
    if (totalSize > 1024 * 1024) { // 1MB
      recommendations.push('Total bundle size exceeds 1MB, consider lazy loading');
    }

    // Check number of chunks
    if (this.loadedChunks.size > 10) {
      recommendations.push('High number of chunks loaded, consider bundle consolidation');
    }

    return recommendations;
  }

  // Monitor resource loading
  monitorResourceLoading() {
    if (typeof window === 'undefined') return;

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'resource') {
          const resource = entry as PerformanceResourceTiming;
          
          if (resource.name.includes('.js')) {
            const chunkName = this.extractChunkName(resource.name);
            this.bundleSizes.set(chunkName, resource.transferSize || 0);
            
            // Track loading performance
            if (resource.duration > 500) {
              console.warn(`Slow resource load: ${chunkName} took ${resource.duration.toFixed(2)}ms`);
            }
          }
        }
      }
    });

    observer.observe({ entryTypes: ['resource'] });
    
    return () => observer.disconnect();
  }

  // Get loading statistics
  getLoadingStats() {
    return {
      chunksLoaded: this.loadedChunks.size,
      averageLoadTime: this.getAverageLoadTime(),
      slowestChunk: this.getSlowestChunk(),
      totalBundleSize: this.getTotalBundleSize(),
      recommendations: this.getPerformanceRecommendations(),
    };
  }

  private getAverageLoadTime(): number {
    const times = Array.from(this.loadTimes.values());
    return times.length > 0 ? times.reduce((sum, time) => sum + time, 0) / times.length : 0;
  }

  private getSlowestChunk(): { name: string; time: number } | null {
    let slowest: { name: string; time: number } | null = null;
    
    this.loadTimes.forEach((time, name) => {
      if (!slowest || time > slowest.time) {
        slowest = { name, time };
      }
    });
    
    return slowest;
  }

  private getTotalBundleSize(): number {
    return Array.from(this.bundleSizes.values()).reduce((sum, size) => sum + size, 0);
  }
}

// React hook for bundle analysis
export function useBundleAnalyzer() {
  const analyzer = BundleAnalyzer.getInstance();
  
  const trackChunkLoad = (chunkName: string) => {
    const startTime = performance.now();
    return () => analyzer.trackChunkLoad(chunkName, startTime);
  };

  return {
    trackChunkLoad,
    analyzeBundleComposition: () => analyzer.analyzeBundleComposition(),
    getLoadingStats: () => analyzer.getLoadingStats(),
    monitorResourceLoading: () => analyzer.monitorResourceLoading(),
  };
}

// Performance budget checker
export class PerformanceBudget {
  private budgets = {
    maxBundleSize: 1024 * 1024, // 1MB
    maxChunkSize: 250 * 1024,   // 250KB
    maxChunkLoadTime: 1000,     // 1s
    maxTotalChunks: 10,
  };

  checkBudgets(stats: ReturnType<BundleAnalyzer['getLoadingStats']>) {
    const violations: string[] = [];
    
    if (stats.totalBundleSize > this.budgets.maxBundleSize) {
      violations.push(`Bundle size (${(stats.totalBundleSize / 1024 / 1024).toFixed(2)}MB) exceeds budget (${(this.budgets.maxBundleSize / 1024 / 1024).toFixed(2)}MB)`);
    }
    
    if (stats.chunksLoaded > this.budgets.maxTotalChunks) {
      violations.push(`Number of chunks (${stats.chunksLoaded}) exceeds budget (${this.budgets.maxTotalChunks})`);
    }
    
    if (stats.slowestChunk && stats.slowestChunk.time > this.budgets.maxChunkLoadTime) {
      violations.push(`Slowest chunk (${stats.slowestChunk.name}: ${stats.slowestChunk.time.toFixed(0)}ms) exceeds budget (${this.budgets.maxChunkLoadTime}ms)`);
    }
    
    return {
      passed: violations.length === 0,
      violations,
    };
  }

  setBudget(metric: keyof typeof this.budgets, value: number) {
    this.budgets[metric] = value;
  }
}

// Initialize bundle monitoring
export function initBundleMonitoring() {
  if (typeof window === 'undefined') return;
  
  const analyzer = BundleAnalyzer.getInstance();
  const budget = new PerformanceBudget();
  
  // Start monitoring
  const cleanup = analyzer.monitorResourceLoading();
  
  // Check budgets on page load
  window.addEventListener('load', () => {
    setTimeout(() => {
      const stats = analyzer.getLoadingStats();
      const budgetCheck = budget.checkBudgets(stats);
      
      if (!budgetCheck.passed) {
        console.warn('Performance budget violations:', budgetCheck.violations);
      }
      
      // Log analysis
      analyzer.analyzeBundleComposition();
    }, 1000);
  });
  
  return cleanup;
}

// Preload optimization
export function optimizePreloading() {
  if (typeof window === 'undefined') return;
  
  // Preload critical chunks based on route
  const currentPath = window.location.pathname;
  
  const criticalChunks = {
    '/dashboard': ['dashboard', 'charts'],
    '/analysis': ['analysis', 'charts', 'tables'],
    '/insights': ['insights', 'ai'],
    '/connections': ['connections', 'forms'],
    '/alarms': ['alarms', 'notifications'],
  };
  
  const chunksToPreload = criticalChunks[currentPath as keyof typeof criticalChunks] || [];
  
  chunksToPreload.forEach(chunk => {
    const link = document.createElement('link');
    link.rel = 'modulepreload';
    link.href = `/_next/static/chunks/${chunk}.js`;
    document.head.appendChild(link);
  });
}