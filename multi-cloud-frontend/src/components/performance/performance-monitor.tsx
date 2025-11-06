'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { usePerformanceOptimization } from '@/hooks/use-performance-optimization';
import { useWebVitals } from '@/lib/web-vitals';
import { Activity, Zap, Clock, Eye } from 'lucide-react';

interface PerformanceMonitorProps {
  showDetails?: boolean;
  className?: string;
}

export function PerformanceMonitor({ 
  showDetails = false, 
  className 
}: PerformanceMonitorProps) {
  const { getMetrics } = usePerformanceOptimization();
  const { getMetrics: getWebVitalsMetrics } = useWebVitals();
  const [metrics, setMetrics] = useState<any>(null);
  const [webVitals, setWebVitals] = useState<any[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (process.env.NODE_ENV === 'development' || showDetails) {
      const updateMetrics = () => {
        setMetrics(getMetrics());
        setWebVitals(getWebVitalsMetrics());
      };

      updateMetrics();
      const interval = setInterval(updateMetrics, 5000);
      return () => clearInterval(interval);
    }
  }, [getMetrics, getWebVitalsMetrics, showDetails]);

  if (!metrics && !showDetails) return null;

  const getRatingColor = (rating: string) => {
    switch (rating) {
      case 'good':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'needs-improvement':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'poor':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const formatValue = (value: number, unit: string) => {
    if (unit === 'ms') {
      return `${Math.round(value)}ms`;
    }
    if (unit === 'MB') {
      return `${(value / 1024 / 1024).toFixed(2)}MB`;
    }
    return value.toString();
  };

  if (!isVisible && !showDetails) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 right-4 z-50"
      >
        <Activity className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <Card className={`fixed bottom-4 right-4 z-50 w-80 ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center">
            <Activity className="h-4 w-4 mr-2" />
            Performance Monitor
          </CardTitle>
          {!showDetails && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsVisible(false)}
            >
              ×
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Web Vitals */}
        {webVitals.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center">
              <Zap className="h-3 w-3 mr-1" />
              Web Vitals
            </h4>
            <div className="space-y-2">
              {webVitals.map((vital) => (
                <div key={vital.name} className="flex items-center justify-between text-xs">
                  <span className="font-medium">{vital.name}</span>
                  <div className="flex items-center space-x-2">
                    <span>{formatValue(vital.value, vital.name === 'CLS' ? '' : 'ms')}</span>
                    <Badge 
                      variant="secondary" 
                      className={getRatingColor(vital.rating)}
                    >
                      {vital.rating}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bundle Performance */}
        {metrics?.bundle && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center">
              <Clock className="h-3 w-3 mr-1" />
              Bundle Performance
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span>Chunks Loaded</span>
                <span className="font-medium">{metrics.bundle.chunksLoaded}</span>
              </div>
              <div className="flex justify-between">
                <span>Total Size</span>
                <span className="font-medium">
                  {formatValue(metrics.bundle.totalBundleSize, 'MB')}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Avg Load Time</span>
                <span className="font-medium">
                  {formatValue(metrics.bundle.averageLoadTime, 'ms')}
                </span>
              </div>
              {metrics.bundle.slowestChunk && (
                <div className="flex justify-between">
                  <span>Slowest Chunk</span>
                  <span className="font-medium">
                    {metrics.bundle.slowestChunk.name} ({formatValue(metrics.bundle.slowestChunk.time, 'ms')})
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Performance Recommendations */}
        {metrics?.bundle?.recommendations?.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center">
              <Eye className="h-3 w-3 mr-1" />
              Recommendations
            </h4>
            <div className="space-y-1">
              {metrics.bundle.recommendations.slice(0, 3).map((rec: string, index: number) => (
                <div key={index} className="text-xs text-yellow-600 dark:text-yellow-400">
                  • {rec}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Performance Score */}
        <div className="pt-2 border-t">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">Performance Score</span>
            <Badge 
              variant="secondary"
              className={getRatingColor(getOverallRating())}
            >
              {getOverallRating().toUpperCase()}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  function getOverallRating(): string {
    if (!webVitals.length) return 'unknown';
    
    const ratings = webVitals.map(v => v.rating);
    if (ratings.every(r => r === 'good')) return 'good';
    if (ratings.some(r => r === 'poor')) return 'poor';
    return 'needs-improvement';
  }
}

// Lightweight performance indicator for production
export function PerformanceIndicator() {
  const [score, setScore] = useState<'good' | 'needs-improvement' | 'poor' | null>(null);
  const { getMetrics: getWebVitalsMetrics } = useWebVitals();

  useEffect(() => {
    const updateScore = () => {
      const vitals = getWebVitalsMetrics();
      if (vitals.length === 0) return;

      const ratings = vitals.map(v => v.rating);
      if (ratings.every(r => r === 'good')) {
        setScore('good');
      } else if (ratings.some(r => r === 'poor')) {
        setScore('poor');
      } else {
        setScore('needs-improvement');
      }
    };

    updateScore();
    const interval = setInterval(updateScore, 10000);
    return () => clearInterval(interval);
  }, [getWebVitalsMetrics]);

  if (!score || process.env.NODE_ENV !== 'production') return null;

  const colors = {
    good: 'bg-green-500',
    'needs-improvement': 'bg-yellow-500',
    poor: 'bg-red-500',
  };

  return (
    <div 
      className={`fixed top-4 right-4 w-3 h-3 rounded-full ${colors[score]} z-50`}
      title={`Performance: ${score.replace('-', ' ')}`}
    />
  );
}