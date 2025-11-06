"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CostBarChart } from "@/components/charts/cost-bar-chart"
import { Skeleton } from "@/components/ui/skeleton"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { ProviderBreakdown, CostFilters } from "@/types/models"
import { formatCurrency, getProviderColor } from "@/lib/utils"

interface ProviderComparisonChartProps {
  data?: ProviderBreakdown[]
  loading?: boolean
  filters?: CostFilters
  onProviderSelect?: (provider: string) => void
}

const COMPARISON_TYPES = [
  { label: "Cost Comparison", value: "cost" },
  { label: "Account Count", value: "accounts" },
  { label: "Service Count", value: "services" },
  { label: "Trend Analysis", value: "trend" },
]

const CHART_STYLES = [
  { label: "Grouped", value: "grouped" },
  { label: "Stacked", value: "stacked" },
]

export function ProviderComparisonChart({ 
  data = [], 
  loading = false, 
  filters,
  onProviderSelect 
}: ProviderComparisonChartProps) {
  const [comparisonType, setComparisonType] = useState("cost")
  const [chartStyle, setChartStyle] = useState("grouped")
  const [showTrends, setShowTrends] = useState(true)

  // Process data for chart display
  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return []

    return data.map(provider => ({
      name: provider.provider.toUpperCase(),
      cost: provider.cost,
      accounts: provider.account_count,
      services: provider.service_count,
      trend: provider.trend,
      percentage: provider.percentage,
      provider: provider.provider
    }))
  }, [data])

  // Get comparison data based on selected type
  const comparisonData = React.useMemo(() => {
    return chartData.map(item => ({
      name: item.name,
      value: comparisonType === "cost" ? item.cost :
             comparisonType === "accounts" ? item.accounts :
             comparisonType === "services" ? item.services :
             item.trend,
      [item.provider]: comparisonType === "cost" ? item.cost :
                      comparisonType === "accounts" ? item.accounts :
                      comparisonType === "services" ? item.services :
                      item.trend,
      total: comparisonType === "cost" ? item.cost :
             comparisonType === "accounts" ? item.accounts :
             comparisonType === "services" ? item.services :
             item.trend
    }))
  }, [chartData, comparisonType])

  // Calculate summary statistics
  const summaryStats = React.useMemo(() => {
    if (data.length === 0) return null

    const totalCost = data.reduce((sum, provider) => sum + provider.cost, 0)
    const totalAccounts = data.reduce((sum, provider) => sum + provider.account_count, 0)
    const totalServices = data.reduce((sum, provider) => sum + provider.service_count, 0)
    const avgTrend = data.reduce((sum, provider) => sum + provider.trend, 0) / data.length

    const topProvider = data.reduce((max, provider) => 
      provider.cost > max.cost ? provider : max
    )

    return {
      totalCost,
      totalAccounts,
      totalServices,
      avgTrend,
      topProvider,
      providerCount: data.length
    }
  }, [data])

  const handleProviderClick = (provider: string) => {
    onProviderSelect?.(provider.toLowerCase())
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Provider Comparison</CardTitle>
            <div className="flex items-center space-x-2">
              <Skeleton className="h-8 w-32" />
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

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Provider Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-80 text-muted-foreground">
            No provider data available
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Provider Comparison</CardTitle>
          <div className="flex items-center space-x-2">
            <Select value={comparisonType} onValueChange={setComparisonType}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COMPARISON_TYPES.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={chartStyle} onValueChange={setChartStyle}>
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHART_STYLES.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant={showTrends ? "default" : "outline"}
              size="sm"
              onClick={() => setShowTrends(!showTrends)}
            >
              Trends
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Summary Statistics */}
        {summaryStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Total Cost</p>
              <p className="text-2xl font-bold">
                {formatCurrency(summaryStats.totalCost)}
              </p>
              <p className="text-xs text-muted-foreground">
                across {summaryStats.providerCount} providers
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Top Provider</p>
              <p className="text-lg font-semibold capitalize">
                {summaryStats.topProvider.provider}
              </p>
              <p className="text-xs text-muted-foreground">
                {summaryStats.topProvider.percentage.toFixed(1)}% of total
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Total Accounts</p>
              <p className="text-lg font-semibold">
                {summaryStats.totalAccounts}
              </p>
              <p className="text-xs text-muted-foreground">connected accounts</p>
            </div>

            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Avg Trend</p>
              <div className="flex items-center space-x-2">
                {summaryStats.avgTrend > 0 && <TrendingUp className="w-4 h-4 text-red-500" />}
                {summaryStats.avgTrend < 0 && <TrendingDown className="w-4 h-4 text-green-500" />}
                {summaryStats.avgTrend === 0 && <Minus className="w-4 h-4 text-gray-500" />}
                <span className={`font-semibold ${
                  summaryStats.avgTrend > 0 ? 'text-red-600' : 
                  summaryStats.avgTrend < 0 ? 'text-green-600' : 'text-gray-600'
                }`}>
                  {summaryStats.avgTrend > 0 ? '+' : ''}{summaryStats.avgTrend.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Provider Breakdown Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {data.map((provider) => (
            <Card 
              key={provider.provider}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleProviderClick(provider.provider)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getProviderColor(provider.provider) }}
                    />
                    <h3 className="font-semibold capitalize">{provider.provider}</h3>
                  </div>
                  <div className="flex items-center space-x-1">
                    {provider.trend > 0 && <TrendingUp className="w-3 h-3 text-red-500" />}
                    {provider.trend < 0 && <TrendingDown className="w-3 h-3 text-green-500" />}
                    {provider.trend === 0 && <Minus className="w-3 h-3 text-gray-500" />}
                    <span className={`text-xs ${
                      provider.trend > 0 ? 'text-red-600' : 
                      provider.trend < 0 ? 'text-green-600' : 'text-gray-600'
                    }`}>
                      {provider.trend > 0 ? '+' : ''}{provider.trend.toFixed(1)}%
                    </span>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div>
                    <p className="text-lg font-bold">{formatCurrency(provider.cost)}</p>
                    <p className="text-sm text-muted-foreground">
                      {provider.percentage.toFixed(1)}% of total cost
                    </p>
                  </div>
                  
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Accounts:</span>
                    <span className="font-medium">{provider.account_count}</span>
                  </div>
                  
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Services:</span>
                    <span className="font-medium">{provider.service_count}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Comparison Chart */}
        <CostBarChart
          data={comparisonData}
          loading={false}
          title=""
          height={300}
          showProviders={false}
          stacked={chartStyle === "stacked"}
        />

        {/* Chart Controls */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <div className="text-sm text-muted-foreground">
            Comparing {comparisonType} across {data.length} providers
          </div>
          
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              Export Comparison
            </Button>
            <Button variant="outline" size="sm">
              Detailed View
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}