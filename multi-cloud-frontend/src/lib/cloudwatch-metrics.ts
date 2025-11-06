/**
 * CloudWatch Metrics Client
 * Sends custom metrics to AWS CloudWatch
 */

interface CloudWatchMetric {
  namespace: string
  metricName: string
  value: number
  unit?: string
  dimensions?: Record<string, string>
  timestamp?: string
}

interface MetricBatch {
  metrics: CloudWatchMetric[]
}

class CloudWatchMetricsClient {
  private apiEndpoint: string
  private batchSize: number = 20 // CloudWatch limit
  private flushInterval: number = 30000 // 30 seconds
  private pendingMetrics: CloudWatchMetric[] = []
  private flushTimer?: NodeJS.Timeout

  constructor() {
    this.apiEndpoint = process.env.NEXT_PUBLIC_API_BASE_URL || ''
    
    if (typeof window !== 'undefined') {
      this.startAutoFlush()
      
      // Flush on page unload
      window.addEventListener('beforeunload', () => {
        this.flush()
      })
    }
  }

  private startAutoFlush(): void {
    this.flushTimer = setInterval(() => {
      this.flush()
    }, this.flushInterval)
  }

  public putMetric(
    namespace: string,
    metricName: string,
    value: number,
    dimensions?: Record<string, string>,
    unit: string = 'Count'
  ): void {
    const metric: CloudWatchMetric = {
      namespace,
      metricName,
      value,
      unit,
      dimensions: {
        Environment: process.env.NODE_ENV || 'development',
        ...dimensions,
      },
      timestamp: new Date().toISOString(),
    }

    this.pendingMetrics.push(metric)

    // Auto-flush if batch is full
    if (this.pendingMetrics.length >= this.batchSize) {
      this.flush()
    }
  }

  public async flush(): Promise<void> {
    if (this.pendingMetrics.length === 0) {
      return
    }

    const metricsToSend = this.pendingMetrics.splice(0, this.batchSize)
    
    try {
      await this.sendMetricBatch({ metrics: metricsToSend })
    } catch (error) {
      // Silently fail - don't break the app for metrics
      if (process.env.NODE_ENV === 'development') {
        console.warn('Failed to send CloudWatch metrics:', error)
      }
    }
  }

  private async sendMetricBatch(batch: MetricBatch): Promise<void> {
    if (!this.apiEndpoint) {
      return
    }

    const response = await fetch(`${this.apiEndpoint}/analytics/cloudwatch-metrics`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(batch),
    })

    if (!response.ok) {
      throw new Error(`Failed to send metrics: ${response.status}`)
    }
  }

  public destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
    }
    this.flush()
  }
}

// Create singleton instance
const cloudWatchMetrics = new CloudWatchMetricsClient()

// Convenience functions for common metrics
export const putWebVitalMetric = (name: string, value: number, rating: string) => {
  cloudWatchMetrics.putMetric('CostsHub/WebVitals', name, value, {
    Rating: rating,
  }, 'Milliseconds')
}

export const putAnalyticsMetric = (name: string, value: number = 1, dimensions?: Record<string, string>) => {
  cloudWatchMetrics.putMetric('CostsHub/Analytics', name, value, dimensions)
}

export const putErrorMetric = (errorType: string, value: number = 1, dimensions?: Record<string, string>) => {
  cloudWatchMetrics.putMetric('CostsHub/Errors', errorType, value, dimensions)
}

export const putPerformanceMetric = (name: string, value: number, dimensions?: Record<string, string>) => {
  cloudWatchMetrics.putMetric('CostsHub/Performance', name, value, dimensions, 'Milliseconds')
}

export const putBusinessMetric = (name: string, value: number, dimensions?: Record<string, string>) => {
  cloudWatchMetrics.putMetric('CostsHub/Business', name, value, dimensions)
}

export default cloudWatchMetrics