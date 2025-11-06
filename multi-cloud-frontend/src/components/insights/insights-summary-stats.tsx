"use client"

import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { 
  Brain, 
  AlertTriangle, 
  Lightbulb, 
  TrendingUp, 
  Target,
  DollarSign,
  Clock,
  CheckCircle
} from "lucide-react"
import { formatCurrency, cn } from "@/lib/utils"

interface InsightsSummaryData {
  total_insights: number
  by_severity: {
    critical: number
    high: number
    medium: number
    low: number
  }
  by_type: {
    anomaly: number
    recommendation: number
    forecast: number
    optimization: number
  }
  by_status: {
    new: number
    acknowledged: number
    dismissed: number
    implemented: number
  }
  potential_savings: number
  top_recommendations: Array<{
    title: string
    potential_savings: number
    effort_level: 'low' | 'medium' | 'high'
    affected_services: string[]
  }>
}

interface InsightsSummaryStatsProps {
  data?: InsightsSummaryData
  loading?: boolean
}

const severityColors = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-blue-100 text-blue-800 border-blue-200",
}

const typeIcons = {
  anomaly: AlertTriangle,
  recommendation: Lightbulb,
  forecast: TrendingUp,
  optimization: Target,
}

const statusColors = {
  new: "bg-blue-100 text-blue-800",
  acknowledged: "bg-yellow-100 text-yellow-800",
  dismissed: "bg-gray-100 text-gray-800",
  implemented: "bg-green-100 text-green-800",
}

export function InsightsSummaryStats({
  data,
  loading = false,
}: InsightsSummaryStatsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-5 w-5 rounded" />
                  <Skeleton className="h-6 w-8" />
                </div>
                <Skeleton className="h-4 w-24" />
                <div className="space-y-2">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-32 text-muted-foreground">
            <div className="text-center">
              <Brain className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
              <p className="text-sm">No insights data available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Insights */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <Brain className="h-5 w-5 text-primary" />
              <span className="text-2xl font-bold text-foreground">
                {data.total_insights}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">Total Insights</p>
            <div className="mt-3 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">New</span>
                <Badge variant="outline" className={statusColors.new}>
                  {data.by_status.new}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Acknowledged</span>
                <Badge variant="outline" className={statusColors.acknowledged}>
                  {data.by_status.acknowledged}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* High Priority Insights */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
              <span className="text-2xl font-bold text-orange-600">
                {data.by_severity.critical + data.by_severity.high}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">High Priority</p>
            <div className="mt-3 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Critical</span>
                <Badge variant="outline" className={severityColors.critical}>
                  {data.by_severity.critical}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">High</span>
                <Badge variant="outline" className={severityColors.high}>
                  {data.by_severity.high}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Potential Savings */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <DollarSign className="h-5 w-5 text-green-600" />
              <span className="text-2xl font-bold text-green-600">
                {formatCurrency(data.potential_savings)}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">Potential Savings</p>
            <div className="mt-3 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Recommendations</span>
                <Badge variant="outline" className="bg-green-100 text-green-800">
                  {data.by_type.recommendation}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Optimizations</span>
                <Badge variant="outline" className="bg-green-100 text-green-800">
                  {data.by_type.optimization}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Implementation Status */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span className="text-2xl font-bold text-green-600">
                {data.by_status.implemented}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">Implemented</p>
            <div className="mt-3 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Dismissed</span>
                <Badge variant="outline" className={statusColors.dismissed}>
                  {data.by_status.dismissed}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Success Rate</span>
                <span className="text-xs font-medium">
                  {data.total_insights > 0 
                    ? Math.round((data.by_status.implemented / data.total_insights) * 100)
                    : 0}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Insight Types Breakdown */}
      <Card>
        <CardContent className="p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Insights by Type</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(data.by_type).map(([type, count]) => {
              const Icon = typeIcons[type as keyof typeof typeIcons]
              return (
                <div key={type} className="flex items-center space-x-3 p-3 bg-muted/50 rounded-lg">
                  <Icon className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-foreground capitalize">{type}</p>
                    <p className="text-lg font-bold text-foreground">{count}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Top Recommendations Preview */}
      {data.top_recommendations && data.top_recommendations.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Top Recommendations</h3>
            <div className="space-y-3">
              {data.top_recommendations.slice(0, 3).map((rec, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-primary/5 border border-primary/20 rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium text-foreground text-sm">{rec.title}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge 
                        variant="outline" 
                        className={cn(
                          "text-xs",
                          rec.effort_level === 'low' ? "bg-green-100 text-green-800" :
                          rec.effort_level === 'medium' ? "bg-yellow-100 text-yellow-800" :
                          "bg-red-100 text-red-800"
                        )}
                      >
                        {rec.effort_level} effort
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {rec.affected_services.length} service{rec.affected_services.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center text-green-600 font-semibold">
                      <DollarSign className="h-4 w-4 mr-1" />
                      {formatCurrency(rec.potential_savings)}
                    </div>
                    <p className="text-xs text-muted-foreground">potential savings</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}