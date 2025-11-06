"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown,
  AlertTriangle,
  Calendar,
  DollarSign
} from "lucide-react"
import { formatCurrency, formatDate, cn } from "@/lib/utils"
import { AIInsight } from "@/types/models"

interface AnomalyTimelineProps {
  insight: AIInsight
  anomalyData?: {
    anomaly_type: 'cost_spike' | 'usage_anomaly' | 'billing_anomaly'
    detection_method: string
    confidence_score: number
    baseline_data: {
      average_cost: number
      standard_deviation: number
      historical_range: { min: number; max: number }
    }
    anomaly_data: {
      detected_cost: number
      deviation_percentage: number
      affected_period: { start: string; end: string }
    }
    contributing_factors: Array<{
      factor: string
      impact_percentage: number
      description: string
    }>
    similar_incidents: Array<{
      date: string
      cost_impact: number
      resolution: string
    }>
  }
  loading?: boolean
}

export function AnomalyTimeline({ 
  insight, 
  anomalyData,
  loading = false 
}: AnomalyTimelineProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5" />
            <span>Anomaly Timeline</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!anomalyData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5" />
            <span>Anomaly Timeline</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32 text-muted-foreground">
            <div className="text-center">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
              <p className="text-sm">Timeline data not available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Generate mock timeline data points for visualization
  const generateTimelineData = () => {
    const points = []
    const startDate = new Date(anomalyData.anomaly_data.affected_period.start)
    const endDate = new Date(anomalyData.anomaly_data.affected_period.end)
    const baselineCost = anomalyData.baseline_data.average_cost
    const detectedCost = anomalyData.anomaly_data.detected_cost
    
    // Add baseline points before anomaly
    for (let i = 7; i > 0; i--) {
      const date = new Date(startDate)
      date.setDate(date.getDate() - i)
      points.push({
        date: date.toISOString().split('T')[0],
        cost: baselineCost + (Math.random() - 0.5) * (baselineCost * 0.1),
        isAnomaly: false,
        isBaseline: true
      })
    }
    
    // Add anomaly points
    const anomalyDays = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    for (let i = 0; i <= anomalyDays; i++) {
      const date = new Date(startDate)
      date.setDate(date.getDate() + i)
      points.push({
        date: date.toISOString().split('T')[0],
        cost: detectedCost + (Math.random() - 0.5) * (detectedCost * 0.05),
        isAnomaly: true,
        isBaseline: false
      })
    }
    
    // Add points after anomaly
    for (let i = 1; i <= 3; i++) {
      const date = new Date(endDate)
      date.setDate(date.getDate() + i)
      points.push({
        date: date.toISOString().split('T')[0],
        cost: baselineCost + (Math.random() - 0.5) * (baselineCost * 0.1),
        isAnomaly: false,
        isBaseline: true
      })
    }
    
    return points
  }

  const timelineData = generateTimelineData()
  const maxCost = Math.max(...timelineData.map(p => p.cost))
  const minCost = Math.min(...timelineData.map(p => p.cost))
  const costRange = maxCost - minCost

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5" />
            <span>Anomaly Timeline</span>
          </div>
          <Badge variant="outline" className="text-xs">
            {anomalyData.detection_method}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Timeline Visualization */}
          <div className="relative">
            <div className="h-32 bg-muted/20 rounded-lg p-4 overflow-hidden">
              <svg width="100%" height="100%" className="overflow-visible">
                {/* Baseline line */}
                <line
                  x1="0"
                  y1={`${((maxCost - anomalyData.baseline_data.average_cost) / costRange) * 100}%`}
                  x2="100%"
                  y2={`${((maxCost - anomalyData.baseline_data.average_cost) / costRange) * 100}%`}
                  stroke="currentColor"
                  strokeDasharray="4 4"
                  className="text-muted-foreground opacity-50"
                  strokeWidth="1"
                />
                
                {/* Cost trend line */}
                <polyline
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className={cn(
                    anomalyData.anomaly_data.deviation_percentage > 0 
                      ? "text-red-500" 
                      : "text-green-500"
                  )}
                  points={timelineData.map((point, index) => {
                    const x = (index / (timelineData.length - 1)) * 100
                    const y = ((maxCost - point.cost) / costRange) * 100
                    return `${x},${y}`
                  }).join(' ')}
                />
                
                {/* Data points */}
                {timelineData.map((point, index) => {
                  const x = (index / (timelineData.length - 1)) * 100
                  const y = ((maxCost - point.cost) / costRange) * 100
                  return (
                    <circle
                      key={index}
                      cx={`${x}%`}
                      cy={`${y}%`}
                      r={point.isAnomaly ? "4" : "2"}
                      fill="currentColor"
                      className={cn(
                        point.isAnomaly 
                          ? "text-red-500" 
                          : "text-blue-500"
                      )}
                    />
                  )
                })}
              </svg>
            </div>
            
            {/* Timeline labels */}
            <div className="flex justify-between mt-2 text-xs text-muted-foreground">
              <span>{formatDate(timelineData[0]?.date)}</span>
              <span className="font-medium">Anomaly Period</span>
              <span>{formatDate(timelineData[timelineData.length - 1]?.date)}</span>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <BarChart3 className="h-4 w-4 text-blue-600 mr-1" />
                <span className="font-bold text-sm text-blue-600">
                  {formatCurrency(anomalyData.baseline_data.average_cost)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Baseline Average</p>
            </div>

            <div className="text-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <AlertTriangle className="h-4 w-4 text-red-600 mr-1" />
                <span className="font-bold text-sm text-red-600">
                  {formatCurrency(anomalyData.anomaly_data.detected_cost)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Peak Anomaly</p>
            </div>

            <div className="text-center p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                {anomalyData.anomaly_data.deviation_percentage > 0 ? (
                  <TrendingUp className="h-4 w-4 text-orange-600 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-green-600 mr-1" />
                )}
                <span className="font-bold text-sm text-orange-600">
                  {Math.abs(anomalyData.anomaly_data.deviation_percentage)}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Deviation</p>
            </div>
          </div>

          {/* Anomaly Period Details */}
          <div className="p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-sm text-foreground">Anomaly Period</h4>
              <Badge variant="outline" className="text-xs">
                {Math.ceil((new Date(anomalyData.anomaly_data.affected_period.end).getTime() - 
                           new Date(anomalyData.anomaly_data.affected_period.start).getTime()) / 
                           (1000 * 60 * 60 * 24))} days
              </Badge>
            </div>
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center text-muted-foreground">
                <Calendar className="h-4 w-4 mr-1" />
                <span>
                  {formatDate(anomalyData.anomaly_data.affected_period.start)} - {formatDate(anomalyData.anomaly_data.affected_period.end)}
                </span>
              </div>
              <div className="flex items-center text-muted-foreground">
                <DollarSign className="h-4 w-4 mr-1" />
                <span>
                  {formatCurrency(anomalyData.anomaly_data.detected_cost - anomalyData.baseline_data.average_cost)} excess cost
                </span>
              </div>
            </div>
          </div>

          {/* Historical Range */}
          <div className="space-y-2">
            <h4 className="font-medium text-sm text-foreground">Historical Cost Range</h4>
            <div className="flex items-center space-x-2">
              <span className="text-xs text-muted-foreground w-16">Min</span>
              <div className="flex-1 bg-muted/50 rounded-full h-2 relative">
                <div 
                  className="absolute left-0 top-0 h-full bg-blue-500 rounded-full"
                  style={{ 
                    width: `${((anomalyData.baseline_data.average_cost - anomalyData.baseline_data.historical_range.min) / 
                              (anomalyData.baseline_data.historical_range.max - anomalyData.baseline_data.historical_range.min)) * 100}%` 
                  }}
                />
                <div 
                  className="absolute top-0 h-full w-1 bg-red-500"
                  style={{ 
                    left: `${((anomalyData.anomaly_data.detected_cost - anomalyData.baseline_data.historical_range.min) / 
                             (anomalyData.baseline_data.historical_range.max - anomalyData.baseline_data.historical_range.min)) * 100}%` 
                  }}
                />
              </div>
              <span className="text-xs text-muted-foreground w-16">Max</span>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{formatCurrency(anomalyData.baseline_data.historical_range.min)}</span>
              <span className="text-red-600 font-medium">
                Anomaly: {formatCurrency(anomalyData.anomaly_data.detected_cost)}
              </span>
              <span>{formatCurrency(anomalyData.baseline_data.historical_range.max)}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}