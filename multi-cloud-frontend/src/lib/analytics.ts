/**
 * Analytics and Performance Monitoring
 * Tracks Web Vitals, user interactions, and errors
 */

import { getCLS, getFCP, getFID, getLCP, getTTFB } from 'web-vitals'

// Types for analytics events
interface AnalyticsEvent {
  name: string
  properties?: Record<string, any>
  timestamp?: number
  userId?: string
  sessionId?: string
}

interface WebVitalMetric {
  name: 'CLS' | 'FCP' | 'FID' | 'LCP' | 'TTFB'
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
  delta: number
  id: string
  navigationType: string
}

interface ErrorEvent {
  message: string
  stack?: string
  filename?: string
  lineno?: number
  colno?: number
  userAgent: string
  url: string
  timestamp: number
  userId?: string
  sessionId?: string
}

class Analytics {
  private isEnabled: boolean
  private sessionId: string
  private userId?: string
  private environment: string
  private apiEndpoint: string

  constructor() {
    this.isEnabled = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS === 'true'
    this.environment = process.env.NODE_ENV || 'development'
    this.apiEndpoint = process.env.NEXT_PUBLIC_API_BASE_URL || ''
    this.sessionId = this.generateSessionId()
    
    if (this.isEnabled && typeof window !== 'undefined') {
      this.initializeAnalytics()
    }
  }

  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  private initializeAnalytics(): void {
    // Initialize Web Vitals tracking
    this.initializeWebVitals()
    
    // Initialize error tracking
    this.initializeErrorTracking()
    
    // Initialize user interaction tracking
    this.initializeUserTracking()
    
    // Track page view
    this.trackPageView()
  }

  private initializeWebVitals(): void {
    // Track Core Web Vitals
    getCLS(this.handleWebVital.bind(this))
    getFCP(this.handleWebVital.bind(this))
    getFID(this.handleWebVital.bind(this))
    getLCP(this.handleWebVital.bind(this))
    getTTFB(this.handleWebVital.bind(this))
  }

  private handleWebVital(metric: any): void {
    const webVitalMetric: WebVitalMetric = {
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
      delta: metric.delta,
      id: metric.id,
      navigationType: metric.navigationType || 'unknown',
    }

    // Send to CloudWatch
    this.sendToCloudWatch('WebVitals', webVitalMetric.name, webVitalMetric.value, {
      Rating: webVitalMetric.rating,
      NavigationType: webVitalMetric.navigationType,
      Environment: this.environment,
    })

    // Send to custom analytics endpoint
    this.trackEvent('web_vital', {
      metric: webVitalMetric.name,
      value: webVitalMetric.value,
      rating: webVitalMetric.rating,
      delta: webVitalMetric.delta,
      id: webVitalMetric.id,
      navigationType: webVitalMetric.navigationType,
    })
  }

  private initializeErrorTracking(): void {
    // Global error handler
    window.addEventListener('error', (event) => {
      this.trackError({
        message: event.message,
        stack: event.error?.stack,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: Date.now(),
        userId: this.userId,
        sessionId: this.sessionId,
      })
    })

    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      this.trackError({
        message: `Unhandled Promise Rejection: ${event.reason}`,
        stack: event.reason?.stack,
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: Date.now(),
        userId: this.userId,
        sessionId: this.sessionId,
      })
    })
  }

  private initializeUserTracking(): void {
    // Track page visibility changes
    document.addEventListener('visibilitychange', () => {
      this.trackEvent('page_visibility_change', {
        visibility: document.visibilityState,
      })
    })

    // Track user engagement time
    let startTime = Date.now()
    window.addEventListener('beforeunload', () => {
      const engagementTime = Date.now() - startTime
      this.trackEvent('page_engagement', {
        duration: engagementTime,
        url: window.location.href,
      })
    })
  }

  public setUserId(userId: string): void {
    this.userId = userId
  }

  public trackPageView(path?: string): void {
    if (!this.isEnabled) return

    const currentPath = path || window.location.pathname
    
    this.trackEvent('page_view', {
      path: currentPath,
      referrer: document.referrer,
      userAgent: navigator.userAgent,
    })

    // Send to CloudWatch
    this.sendToCloudWatch('Analytics', 'PageViews', 1, {
      Path: currentPath,
      Environment: this.environment,
    })
  }

  public trackEvent(eventName: string, properties?: Record<string, any>): void {
    if (!this.isEnabled) return

    const event: AnalyticsEvent = {
      name: eventName,
      properties: {
        ...properties,
        environment: this.environment,
        userAgent: typeof window !== 'undefined' ? navigator.userAgent : undefined,
        url: typeof window !== 'undefined' ? window.location.href : undefined,
      },
      timestamp: Date.now(),
      userId: this.userId,
      sessionId: this.sessionId,
    }

    // Send to analytics endpoint
    this.sendAnalyticsEvent(event)

    // Send specific metrics to CloudWatch
    if (eventName === 'user_login') {
      this.sendToCloudWatch('Analytics', 'UserLogins', 1, {
        Environment: this.environment,
      })
    } else if (eventName === 'dashboard_view') {
      this.sendToCloudWatch('Analytics', 'DashboardViews', 1, {
        Environment: this.environment,
      })
    }
  }

  public trackError(error: ErrorEvent): void {
    if (!this.isEnabled) return

    // Send to CloudWatch
    this.sendToCloudWatch('Errors', 'JavaScriptErrors', 1, {
      Message: error.message.substring(0, 100), // Truncate for CloudWatch
      Environment: this.environment,
      URL: error.url,
    })

    // Send detailed error to analytics endpoint
    this.sendAnalyticsEvent({
      name: 'javascript_error',
      properties: error,
      timestamp: error.timestamp,
      userId: error.userId,
      sessionId: error.sessionId,
    })
  }

  public trackUserInteraction(action: string, element?: string, properties?: Record<string, any>): void {
    if (!this.isEnabled) return

    this.trackEvent('user_interaction', {
      action,
      element,
      ...properties,
    })
  }

  public trackPerformance(name: string, duration: number, properties?: Record<string, any>): void {
    if (!this.isEnabled) return

    this.trackEvent('performance_metric', {
      name,
      duration,
      ...properties,
    })

    // Send to CloudWatch
    this.sendToCloudWatch('Performance', name, duration, {
      Environment: this.environment,
      ...properties,
    })
  }

  public trackConversion(event: string, value?: number, properties?: Record<string, any>): void {
    if (!this.isEnabled) return

    this.trackEvent('conversion', {
      event,
      value,
      ...properties,
    })

    // Send to CloudWatch
    this.sendToCloudWatch('Conversions', event, value || 1, {
      Environment: this.environment,
    })
  }

  private async sendAnalyticsEvent(event: AnalyticsEvent): Promise<void> {
    try {
      // Send to custom analytics endpoint
      if (this.apiEndpoint) {
        await fetch(`${this.apiEndpoint}/analytics/events`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(event),
        })
      }

      // Also log to console in development
      if (this.environment === 'development') {
        console.log('Analytics Event:', event)
      }
    } catch (error) {
      // Silently fail - don't break the app for analytics
      if (this.environment === 'development') {
        console.warn('Failed to send analytics event:', error)
      }
    }
  }

  private async sendToCloudWatch(
    namespace: string,
    metricName: string,
    value: number,
    dimensions?: Record<string, string>
  ): Promise<void> {
    try {
      // Send to CloudWatch via API Gateway endpoint
      if (this.apiEndpoint) {
        await fetch(`${this.apiEndpoint}/analytics/metrics`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            namespace: `CostsHub/${namespace}`,
            metricName,
            value,
            dimensions: {
              Environment: this.environment,
              ...dimensions,
            },
            timestamp: new Date().toISOString(),
          }),
        })
      }
    } catch (error) {
      // Silently fail - don't break the app for metrics
      if (this.environment === 'development') {
        console.warn('Failed to send CloudWatch metric:', error)
      }
    }
  }

  public async flush(): Promise<void> {
    // Flush any pending analytics events
    // This can be called before page unload
    return Promise.resolve()
  }
}

// Create singleton instance
const analytics = new Analytics()

// Export convenience functions
export const trackPageView = (path?: string) => analytics.trackPageView(path)
export const trackEvent = (eventName: string, properties?: Record<string, any>) => 
  analytics.trackEvent(eventName, properties)
export const trackError = (error: ErrorEvent) => analytics.trackError(error)
export const trackUserInteraction = (action: string, element?: string, properties?: Record<string, any>) =>
  analytics.trackUserInteraction(action, element, properties)
export const trackPerformance = (name: string, duration: number, properties?: Record<string, any>) =>
  analytics.trackPerformance(name, duration, properties)
export const trackConversion = (event: string, value?: number, properties?: Record<string, any>) =>
  analytics.trackConversion(event, value, properties)
export const setUserId = (userId: string) => analytics.setUserId(userId)
export const flushAnalytics = () => analytics.flush()

export default analytics