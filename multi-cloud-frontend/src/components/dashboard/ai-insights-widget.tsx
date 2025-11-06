"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  ArrowRight, 
  Brain, 
  AlertTriangle, 
  TrendingUp, 
  Lightbulb,
  Target,
  DollarSign
} from "lucide-react"
import { formatCurrency, formatDate } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface InsightData {
  id: string
  type: 'anomaly' | 'recommendation' | 'forecast' | 'optimization'
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
  potential_savings?: number
  created_at: string
}

interface RecommendationData {
  title: string
  potential_savings: number
  effort_level: 'low' | 'medium' | 'high'
  affected_services: string[]
}

interface AIInsightsSummaryData {
  total_new_insights: number
  high_priority_count: number
  potential_monthly_savings: number
  recent_insights: InsightData[]
  top_recommendations: RecommendationData[]
}

interface AIInsightsWidgetProps {
  data?: AIInsightsSummaryData
  loading?: boolean
}

const insightTypeIcons = {
  anomaly: AlertTriangle,
  recommendation: Lightbulb,
  forecast: TrendingUp,
  optimization: Target,
}

const severityColors = {
  low: "bg-blue-100 text-blue-800 border-blue-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  critical: "bg-red-100 text-red-800 border-red-200",
}

const effortColors = {
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-red-100 text-red-800",
}

export function AIInsightsWidget({
  data,
  loading = false,
}: AIInsightsWidgetProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Brain className="h-5 w-5 text-primary" />
              <CardTitle>AI Insights</CardTitle>
            </div>
            <Skeleton className="h-9 w-20" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Summary metrics skeleton */}
            <div className="grid grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="text-center">
                  <Skeleton className="h-6 w-8 mx-auto mb-1" />
                  <Skeleton className="h-3 w-16 mx-auto" />
                </div>
              ))}
            </div>
            
            {/* Recent insights skeleton */}
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="p-3 border rounded-lg">
                  <div className="flex items-start justify-between mb-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-5 w-16" />
                  </div>
                  <Skeleton className="h-3 w-full mb-1" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle>AI Insights</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48 text-muted-foreground">
            <div className="text-center">
              <Brain className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
              <p>No AI insights available</p>
              <p className="text-sm mt-1">Connect accounts to start generating insights</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle>AI Insights</CardTitle>
          </div>
          <Button variant="ghost" size="sm">
            View All
            <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Summary Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-foreground">
                {data.total_new_insights}
              </p>
              <p className="text-sm text-muted-foreground">New Insights</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">
                {data.high_priority_count}
              </p>
              <p className="text-sm text-muted-foreground">High Priority</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">
                {formatCurrency(data.potential_monthly_savings)}
              </p>
              <p className="text-sm text-muted-foreground">Potential Savings</p>
            </div>
          </div>

          {/* Recent Insights */}
          {data.recent_insights && data.recent_insights.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-medium text-foreground">Recent Insights</h4>
              {data.recent_insights.slice(0, 3).map((insight) => {
                const Icon = insightTypeIcons[insight.type]
                return (
                  <div 
                    key={insight.id}
                    className="p-3 border border-border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <p className="font-medium text-sm text-foreground">
                          {insight.title}
                        </p>
                      </div>
                      <Badge 
                        variant="outline" 
                        className={cn("text-xs", severityColors[insight.severity])}
                      >
                        {insight.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                      {insight.description}
                    </p>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">
                        {formatDate(insight.created_at)}
                      </span>
                      {insight.potential_savings && (
                        <div className="flex items-center text-green-600">
                          <DollarSign className="h-3 w-3 mr-1" />
                          {formatCurrency(insight.potential_savings)}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Top Recommendations */}
          {data.top_recommendations && data.top_recommendations.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-medium text-foreground">Top Recommendations</h4>
              {data.top_recommendations.slice(0, 2).map((rec, index) => (
                <div 
                  key={index}
                  className="p-3 bg-primary/5 border border-primary/20 rounded-lg"
                >
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-medium text-sm text-foreground">
                      {rec.title}
                    </p>
                    <Badge 
                      variant="outline" 
                      className={cn("text-xs", effortColors[rec.effort_level])}
                    >
                      {rec.effort_level} effort
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {rec.affected_services.length} service{rec.affected_services.length !== 1 ? 's' : ''} affected
                    </span>
                    <div className="flex items-center text-green-600 font-medium">
                      <DollarSign className="h-3 w-3 mr-1" />
                      {formatCurrency(rec.potential_savings)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty State for Insights */}
          {(!data.recent_insights || data.recent_insights.length === 0) && 
           (!data.top_recommendations || data.top_recommendations.length === 0) && (
            <div className="text-center py-8 text-muted-foreground">
              <Lightbulb className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
              <p className="text-sm">No insights available yet</p>
              <p className="text-xs mt-1">AI analysis will appear here once data is collected</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}