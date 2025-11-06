"use client"

import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { 
  DollarSign, 
  Cloud, 
  Bell, 
  BarChart3, 
  TrendingUp, 
  TrendingDown,
  Minus
} from "lucide-react"
import { formatCurrency, formatNumber, getCostChangeColor, getCostChangeBadgeVariant } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface MetricCardProps {
  title: string
  value?: number | string
  subValue?: number
  change?: number
  loading?: boolean
  icon?: "dollar" | "cloud" | "bell" | "chart"
  currency?: string
  suffix?: string
  isText?: boolean
  className?: string
}

const iconMap = {
  dollar: DollarSign,
  cloud: Cloud,
  bell: Bell,
  chart: BarChart3,
}

const iconColorMap = {
  dollar: "text-primary-600 bg-primary-100",
  cloud: "text-blue-600 bg-blue-100",
  bell: "text-yellow-600 bg-yellow-100",
  chart: "text-green-600 bg-green-100",
}

export function MetricCard({
  title,
  value,
  subValue,
  change,
  loading = false,
  icon = "dollar",
  currency = "USD",
  suffix,
  isText = false,
  className,
}: MetricCardProps) {
  const Icon = iconMap[icon]
  const iconColorClass = iconColorMap[icon]

  if (loading) {
    return (
      <Card className={cn("p-6", className)}>
        <CardContent className="p-0">
          <div className="flex items-center justify-between">
            <div className="space-y-3 flex-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-4 w-16" />
            </div>
            <Skeleton className="h-12 w-12 rounded-lg" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const formatValue = () => {
    if (value === undefined || value === null) return 'N/A'
    
    if (isText) {
      return value.toString()
    }
    
    if (typeof value === 'number') {
      if (currency && !suffix) {
        return formatCurrency(value, currency)
      }
      return formatNumber(value)
    }
    
    return value.toString()
  }

  const formatSubValue = () => {
    if (!subValue) return null
    
    if (currency) {
      return formatCurrency(subValue, currency)
    }
    
    return formatNumber(subValue)
  }

  const getTrendIcon = () => {
    if (change === undefined || change === null || change === 0) {
      return <Minus className="h-4 w-4" />
    }
    
    return change > 0 ? (
      <TrendingUp className="h-4 w-4" />
    ) : (
      <TrendingDown className="h-4 w-4" />
    )
  }

  const getTrendColor = () => {
    if (change === undefined || change === null) return "text-gray-500"
    return change > 0 ? "text-red-600" : "text-green-600"
  }

  return (
    <Card className={cn("p-6", className)}>
      <CardContent className="p-0">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">
              {title}
            </p>
            <div className="space-y-1">
              <p className="text-2xl font-bold text-foreground">
                {formatValue()}
                {suffix && !isText && (
                  <span className="text-sm font-normal text-muted-foreground ml-1">
                    {suffix}
                  </span>
                )}
              </p>
              {subValue && (
                <p className="text-sm text-muted-foreground">
                  {formatSubValue()}
                </p>
              )}
            </div>
            
            {change !== undefined && change !== null && (
              <div className="flex items-center space-x-1">
                <div className={cn("flex items-center", getTrendColor())}>
                  {getTrendIcon()}
                  <span className="text-sm font-medium ml-1">
                    {Math.abs(change).toFixed(1)}%
                  </span>
                </div>
                <span className="text-sm text-muted-foreground">
                  vs last month
                </span>
              </div>
            )}
          </div>
          
          <div className={cn("p-3 rounded-lg", iconColorClass)}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}