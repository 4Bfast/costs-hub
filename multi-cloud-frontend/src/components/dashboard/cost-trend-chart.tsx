"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { CostLineChart } from "@/components/charts/cost-line-chart"

interface CostDataPoint {
  date: string
  cost: number
  provider_breakdown?: Array<{
    provider: string
    cost: number
  }>
}

interface CostTrendChartProps {
  data?: CostDataPoint[]
  loading?: boolean
  title?: string
  height?: number
}

export function CostTrendChart({
  data,
  loading = false,
  title = "Cost Trends",
  height = 300,
}: CostTrendChartProps) {
  const [selectedPeriod, setSelectedPeriod] = useState("30d")
  const [showProviders, setShowProviders] = useState(true)

  // Transform data for the chart component
  const transformedData = React.useMemo(() => {
    if (!data) return []
    
    return data.map(point => {
      const transformed: any = {
        date: new Date(point.date).toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric' 
        }),
        total: point.cost,
      }
      
      // Add provider breakdown if available
      if (point.provider_breakdown && showProviders) {
        point.provider_breakdown.forEach(provider => {
          transformed[provider.provider.toLowerCase()] = provider.cost
        })
      }
      
      return transformed
    })
  }, [data, showProviders])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <Skeleton className="h-9 w-32" />
          </div>
        </CardHeader>
        <CardContent>
          <Skeleton className="w-full" style={{ height: `${height}px` }} />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <div className="flex items-center space-x-2">
            <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <CostLineChart
          data={transformedData}
          loading={false}
          title=""
          height={height}
          showProviders={showProviders}
        />
      </CardContent>
    </Card>
  )
}