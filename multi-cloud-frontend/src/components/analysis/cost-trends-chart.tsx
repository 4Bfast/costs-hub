"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CostLineChart } from "@/components/charts/cost-line-chart"
import { Skeleton } from "@/components/ui/skeleton"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { CostFilters, CostTrendPoint } from "@/types/models"
import { formatCurrency } from "@/lib/utils"

interface CostTrendsChartProps {
  data?: CostTrendPoint[]
  loading?: boolean
  filters?: CostFilters
  onFiltersChange?: (filters: CostFilters) => void
}

const PERIOD_OPTIONS = [
  { label: "Daily", value: "daily" },
  { label: "Weekly", value: "weekly" },
  { label: "Monthly", value: "monthly" },
]

const CHART_TYPES = [
  { label: "Line Chart", value: "line" },
  { label: "Area Chart", value: "area" },
  { label: "Bar Chart", value: "bar" },
]

export function CostTrendsChart({ 
  data = [], 
  loading = false, 
  filters,
  onFiltersChange 
}: CostTrendsChartProps) {
  const [period, setPeriod] = useState("daily")
  const [chartType, setChartType] = useState("line")
  const [showProviders, setShowProviders] = useState(true)

  // Transform data for chart display
  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return []

    // Group data by date and aggregate by provider
    const groupedData = data.reduce((acc, point) => {
      const date = point.date
      if (!acc[date]) {
        acc[date] = { date, total: 0, aws: 0, gcp: 0, azure: 0 }
      }
      
      acc[date].total += point.cost
      if (point.provider) {
        acc[date][point.provider] = (acc[date][point.provider] || 0) + point.cost
      }
      
      return acc
    }, {} as Record<string, any>)

    return Object.values(groupedData).sort((a: any, b: any) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    )
  }, [data])

  // Calculate trend statistics
  const trendStats = React.useMemo(() => {
    if (chartData.length < 2) return null

    const firstValue = chartData[0]?.total || 0
    const lastValue = chartData[chartData.length - 1]?.total || 0
    const change = lastValue - firstValue
    const changePercent = firstValue > 0 ? (change / firstValue) * 100 : 0

    return {
      change,
      changePercent,
      trend: change > 0 ? 'up' : change < 0 ? 'down' : 'flat',
      average: chartData.reduce((sum, point) => sum + (point.total || 0), 0) / chartData.length,
      peak: Math.max(...chartData.map(point => point.total || 0)),
      low: Math.min(...chartData.map(point => point.total || 0))
    }
  }, [chartData])

  const handlePeriodChange = (newPeriod: string) => {
    setPeriod(newPeriod)
    // You could trigger a data refetch here with the new period
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Cost Trends</CardTitle>
            <div className="flex items-center space-x-2">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-8 w-24" />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-6 w-20" />
                  <Skeleton className="h-3 w-12" />
                </div>
              ))}
            </div>
            <Skeleton className="w-full h-80" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Cost Trends</CardTitle>
          <div className="flex items-center space-x-2">
            <Select value={period} onValueChange={handlePeriodChange}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PERIOD_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select value={chartType} onValueChange={setChartType}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHART_TYPES.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant={showProviders ? "default" : "outline"}
              size="sm"
              onClick={() => setShowProviders(!showProviders)}
            >
              Providers
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Trend Statistics */}
        {trendStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Period Change</p>
              <div className="flex items-center space-x-2">
                {trendStats.trend === 'up' && <TrendingUp className="w-4 h-4 text-red-500" />}
                {trendStats.trend === 'down' && <TrendingDown className="w-4 h-4 text-green-500" />}
                {trendStats.trend === 'flat' && <Minus className="w-4 h-4 text-gray-500" />}
                <span className={`font-semibold ${
                  trendStats.trend === 'up' ? 'text-red-600' : 
                  trendStats.trend === 'down' ? 'text-green-600' : 'text-gray-600'
                }`}>
                  {trendStats.changePercent > 0 ? '+' : ''}{trendStats.changePercent.toFixed(1)}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {formatCurrency(Math.abs(trendStats.change))} change
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Average</p>
              <p className="text-lg font-semibold">
                {formatCurrency(trendStats.average)}
              </p>
              <p className="text-xs text-muted-foreground">per period</p>
            </div>

            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Peak</p>
              <p className="text-lg font-semibold">
                {formatCurrency(trendStats.peak)}
              </p>
              <p className="text-xs text-muted-foreground">highest cost</p>
            </div>

            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Low</p>
              <p className="text-lg font-semibold">
                {formatCurrency(trendStats.low)}
              </p>
              <p className="text-xs text-muted-foreground">lowest cost</p>
            </div>
          </div>
        )}

        {/* Chart */}
        <CostLineChart
          data={chartData}
          loading={false}
          title=""
          height={400}
          showProviders={showProviders}
        />

        {/* Chart Controls */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
            <span>Showing {chartData.length} data points</span>
            {filters?.date_range && (
              <span>
                {filters.date_range.start} to {filters.date_range.end}
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              Download Chart
            </Button>
            <Button variant="outline" size="sm">
              Share
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}