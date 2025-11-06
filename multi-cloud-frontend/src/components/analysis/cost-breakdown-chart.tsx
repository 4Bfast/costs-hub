"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CostPieChart } from "@/components/charts/cost-pie-chart"
import { CostBarChart } from "@/components/charts/cost-bar-chart"
import { Skeleton } from "@/components/ui/skeleton"
import { PieChart, BarChart3, List } from "lucide-react"
import { formatCurrency } from "@/lib/utils"

interface BreakdownData {
  name: string
  cost: number
  percentage: number
  trend?: number
  provider?: string
}

interface CostBreakdownChartProps {
  data?: BreakdownData[]
  loading?: boolean
  title?: string
  type?: "service" | "provider" | "account" | "region"
}

const CHART_TYPES = [
  { label: "Pie Chart", value: "pie", icon: PieChart },
  { label: "Bar Chart", value: "bar", icon: BarChart3 },
  { label: "List View", value: "list", icon: List },
]

export function CostBreakdownChart({ 
  data = [], 
  loading = false, 
  title = "Cost Breakdown",
  type = "service"
}: CostBreakdownChartProps) {
  const [chartType, setChartType] = useState("pie")
  const [sortBy, setSortBy] = useState("cost")
  const [showTop, setShowTop] = useState(10)

  // Process and sort data
  const processedData = React.useMemo(() => {
    if (!data || data.length === 0) return []

    let sorted = [...data]
    
    // Sort data
    switch (sortBy) {
      case "cost":
        sorted.sort((a, b) => b.cost - a.cost)
        break
      case "name":
        sorted.sort((a, b) => a.name.localeCompare(b.name))
        break
      case "percentage":
        sorted.sort((a, b) => b.percentage - a.percentage)
        break
      case "trend":
        sorted.sort((a, b) => (b.trend || 0) - (a.trend || 0))
        break
    }

    // Limit to top N items
    const topItems = sorted.slice(0, showTop)
    
    // If there are more items, group the rest as "Others"
    if (sorted.length > showTop) {
      const others = sorted.slice(showTop)
      const othersCost = others.reduce((sum, item) => sum + item.cost, 0)
      const othersPercentage = others.reduce((sum, item) => sum + item.percentage, 0)
      
      topItems.push({
        name: `Others (${others.length})`,
        cost: othersCost,
        percentage: othersPercentage,
        trend: 0
      })
    }

    return topItems
  }, [data, sortBy, showTop])

  // Transform data for different chart types
  const chartData = React.useMemo(() => {
    return processedData.map(item => ({
      name: item.name,
      value: item.cost,
      cost: item.cost,
      percentage: item.percentage,
      trend: item.trend,
      provider: item.provider
    }))
  }, [processedData])

  // Calculate total cost
  const totalCost = React.useMemo(() => {
    return data.reduce((sum, item) => sum + item.cost, 0)
  }, [data])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <Skeleton className="h-8 w-24" />
          </div>
        </CardHeader>
        <CardContent>
          <Skeleton className="w-full h-80" />
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
          <div className="flex items-center justify-center h-80 text-muted-foreground">
            No breakdown data available
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
          <div className="flex items-center space-x-2">
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cost">By Cost</SelectItem>
                <SelectItem value="name">By Name</SelectItem>
                <SelectItem value="percentage">By %</SelectItem>
                {data.some(item => item.trend !== undefined) && (
                  <SelectItem value="trend">By Trend</SelectItem>
                )}
              </SelectContent>
            </Select>

            <Select value={showTop.toString()} onValueChange={(value) => setShowTop(parseInt(value))}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">Top 5</SelectItem>
                <SelectItem value="10">Top 10</SelectItem>
                <SelectItem value="15">Top 15</SelectItem>
                <SelectItem value="20">Top 20</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center border rounded-md">
              {CHART_TYPES.map((chartTypeOption) => {
                const Icon = chartTypeOption.icon
                return (
                  <Button
                    key={chartTypeOption.value}
                    variant={chartType === chartTypeOption.value ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setChartType(chartTypeOption.value)}
                    className="rounded-none first:rounded-l-md last:rounded-r-md"
                  >
                    <Icon className="w-4 h-4" />
                  </Button>
                )
              })}
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Total Cost</p>
            <p className="text-2xl font-bold">{formatCurrency(totalCost)}</p>
          </div>
          
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Top {type}</p>
            <p className="text-lg font-semibold">{processedData[0]?.name || 'N/A'}</p>
            <p className="text-sm text-muted-foreground">
              {formatCurrency(processedData[0]?.cost || 0)} ({processedData[0]?.percentage.toFixed(1) || 0}%)
            </p>
          </div>
          
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Items Shown</p>
            <p className="text-lg font-semibold">{processedData.length}</p>
            <p className="text-sm text-muted-foreground">of {data.length} total</p>
          </div>
        </div>

        {/* Chart Display */}
        {chartType === "pie" && (
          <CostPieChart
            data={chartData}
            loading={false}
            title=""
            height={400}
            showLegend={true}
          />
        )}

        {chartType === "bar" && (
          <CostBarChart
            data={chartData.map(item => ({ name: item.name, total: item.cost }))}
            loading={false}
            title=""
            height={400}
            showProviders={false}
          />
        )}

        {chartType === "list" && (
          <div className="space-y-2">
            {processedData.map((item, index) => (
              <div
                key={item.name}
                className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div className="flex items-center justify-center w-8 h-8 bg-primary/10 rounded-full text-sm font-medium">
                    {index + 1}
                  </div>
                  <div>
                    <p className="font-medium">{item.name}</p>
                    {item.provider && (
                      <p className="text-sm text-muted-foreground capitalize">
                        {item.provider}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="font-semibold">{formatCurrency(item.cost)}</p>
                  <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                    <span>{item.percentage.toFixed(1)}%</span>
                    {item.trend !== undefined && (
                      <span className={`${
                        item.trend > 0 ? 'text-red-600' : 
                        item.trend < 0 ? 'text-green-600' : 'text-gray-600'
                      }`}>
                        {item.trend > 0 ? '+' : ''}{item.trend.toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Chart Controls */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <div className="text-sm text-muted-foreground">
            Showing breakdown by {type}
          </div>
          
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              Export Data
            </Button>
            <Button variant="outline" size="sm">
              Drill Down
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}