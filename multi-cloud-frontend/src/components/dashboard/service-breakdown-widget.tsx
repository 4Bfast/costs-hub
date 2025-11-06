"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowRight, TrendingUp, TrendingDown, Minus } from "lucide-react"
import { formatCurrency, formatPercentage, getProviderColor } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface ServiceData {
  service_name: string
  cost: number
  percentage: number
  trend?: number
  provider: string
  account_count: number
  cost_trend_7d?: Array<{ date: string; cost: number }>
}

interface ServiceBreakdownWidgetProps {
  data?: ServiceData[]
  loading?: boolean
  title?: string
  limit?: number
}

export function ServiceBreakdownWidget({
  data,
  loading = false,
  title = "Top Services by Cost",
  limit = 5,
}: ServiceBreakdownWidgetProps) {
  const displayData = data?.slice(0, limit) || []

  const getTrendIcon = (trend?: number) => {
    if (!trend || trend === 0) return <Minus className="h-3 w-3 text-gray-400" />
    return trend > 0 ? (
      <TrendingUp className="h-3 w-3 text-red-500" />
    ) : (
      <TrendingDown className="h-3 w-3 text-green-500" />
    )
  }

  const getTrendColor = (trend?: number) => {
    if (!trend) return "text-gray-500"
    return trend > 0 ? "text-red-600" : "text-green-600"
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <Skeleton className="h-9 w-20" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <div className="text-right space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-3 w-12" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48 text-muted-foreground">
            <div className="text-center">
              <p>No service data available</p>
              <p className="text-sm mt-1">Connect your cloud accounts to see service breakdown</p>
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
          <CardTitle>{title}</CardTitle>
          <Button variant="ghost" size="sm">
            View All
            <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {displayData.map((service, index) => (
            <div 
              key={`${service.service_name}-${service.provider}`}
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted/70 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <p className="font-medium text-foreground truncate">
                    {service.service_name}
                  </p>
                  <Badge 
                    variant="outline" 
                    className="text-xs"
                    style={{ 
                      borderColor: getProviderColor(service.provider),
                      color: getProviderColor(service.provider)
                    }}
                  >
                    {service.provider.toUpperCase()}
                  </Badge>
                </div>
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <span>{service.account_count} account{service.account_count !== 1 ? 's' : ''}</span>
                  {service.trend !== undefined && (
                    <div className="flex items-center space-x-1">
                      {getTrendIcon(service.trend)}
                      <span className={cn("text-xs", getTrendColor(service.trend))}>
                        {Math.abs(service.trend).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="text-right">
                <p className="font-semibold text-foreground">
                  {formatCurrency(service.cost)}
                </p>
                <p className="text-sm text-muted-foreground">
                  {formatPercentage(service.percentage)}
                </p>
              </div>
            </div>
          ))}
        </div>
        
        {data.length > limit && (
          <div className="mt-4 pt-4 border-t">
            <Button variant="outline" className="w-full">
              View All {data.length} Services
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}