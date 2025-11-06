/**
 * Performance Monitoring Hook
 * Tracks component render times and API call performance
 */

import { useEffect, useRef, useCallback } from 'react'
import { trackPerformance } from '@/lib/analytics'

interface PerformanceEntry {
  name: string
  startTime: number
  duration?: number
  metadata?: Record<string, any>
}

export function usePerformanceMonitoring(componentName: string) {
  const renderStartTime = useRef<number>(Date.now())
  const performanceEntries = useRef<Map<string, PerformanceEntry>>(new Map())

  // Track component mount time
  useEffect(() => {
    const mountTime = Date.now() - renderStartTime.current
    trackPerformance('component_mount', mountTime, {
      componentName,
    })
  }, [componentName])

  // Start timing an operation
  const startTiming = useCallback((operationName: string, metadata?: Record<string, any>) => {
    const entry: PerformanceEntry = {
      name: operationName,
      startTime: Date.now(),
      metadata,
    }
    performanceEntries.current.set(operationName, entry)
  }, [])

  // End timing an operation
  const endTiming = useCallback((operationName: string, additionalMetadata?: Record<string, any>) => {
    const entry = performanceEntries.current.get(operationName)
    if (entry) {
      const duration = Date.now() - entry.startTime
      entry.duration = duration

      trackPerformance(operationName, duration, {
        componentName,
        ...entry.metadata,
        ...additionalMetadata,
      })

      performanceEntries.current.delete(operationName)
    }
  }, [componentName])

  // Measure a function execution time
  const measureFunction = useCallback(async <T>(
    functionName: string,
    fn: () => Promise<T> | T,
    metadata?: Record<string, any>
  ): Promise<T> => {
    const startTime = Date.now()
    try {
      const result = await fn()
      const duration = Date.now() - startTime
      
      trackPerformance(functionName, duration, {
        componentName,
        success: true,
        ...metadata,
      })
      
      return result
    } catch (error) {
      const duration = Date.now() - startTime
      
      trackPerformance(functionName, duration, {
        componentName,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        ...metadata,
      })
      
      throw error
    }
  }, [componentName])

  // Track API call performance
  const trackApiCall = useCallback(async <T>(
    endpoint: string,
    apiCall: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> => {
    return measureFunction(`api_call_${endpoint}`, apiCall, {
      endpoint,
      ...metadata,
    })
  }, [measureFunction])

  return {
    startTiming,
    endTiming,
    measureFunction,
    trackApiCall,
  }
}

// Hook for tracking page load performance
export function usePageLoadPerformance(pageName: string) {
  useEffect(() => {
    // Track page load performance using Navigation Timing API
    if (typeof window !== 'undefined' && 'performance' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'navigation') {
            const navEntry = entry as PerformanceNavigationTiming
            
            // Track various timing metrics
            trackPerformance('page_load_total', navEntry.loadEventEnd - navEntry.navigationStart, {
              pageName,
              type: 'total_load_time',
            })
            
            trackPerformance('page_load_dom_content', navEntry.domContentLoadedEventEnd - navEntry.navigationStart, {
              pageName,
              type: 'dom_content_loaded',
            })
            
            trackPerformance('page_load_first_paint', navEntry.responseEnd - navEntry.navigationStart, {
              pageName,
              type: 'first_paint',
            })
            
            // Track resource loading time
            if (navEntry.responseEnd && navEntry.requestStart) {
              trackPerformance('page_load_network', navEntry.responseEnd - navEntry.requestStart, {
                pageName,
                type: 'network_time',
              })
            }
          }
        }
      })

      observer.observe({ entryTypes: ['navigation'] })

      return () => observer.disconnect()
    }
  }, [pageName])
}

// Hook for tracking resource loading performance
export function useResourcePerformance() {
  useEffect(() => {
    if (typeof window !== 'undefined' && 'performance' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'resource') {
            const resourceEntry = entry as PerformanceResourceTiming
            
            // Only track significant resources
            if (resourceEntry.duration > 100) { // Only track resources taking more than 100ms
              const resourceType = resourceEntry.initiatorType
              const resourceName = resourceEntry.name.split('/').pop() || 'unknown'
              
              trackPerformance(`resource_load_${resourceType}`, resourceEntry.duration, {
                resourceName,
                resourceType,
                transferSize: resourceEntry.transferSize,
                encodedBodySize: resourceEntry.encodedBodySize,
              })
            }
          }
        }
      })

      observer.observe({ entryTypes: ['resource'] })

      return () => observer.disconnect()
    }
  }, [])
}