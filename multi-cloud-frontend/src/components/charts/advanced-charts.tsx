"use client"

import React from "react"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  Cell,
  Area,
  AreaChart,
  ReferenceLine,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency } from "@/lib/utils"

// Scatter Plot for Cost vs Usage Correlation
interface ScatterPlotData {
  name: string
  cost: number
  usage: number
  provider: string
  service: string
}

interface CostUsageScatterPlotProps {
  data: ScatterPlotData[]
  loading?: boolean
  title?: string
  height?: number
}

export function CostUsageScatterPlot({
  data,
  loading = false,
  title = "Cost vs Usage Correlation",
  height = 400,
}: CostUsageScatterPlotProps) {
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
          <p className="font-medium text-foreground">{data.name}</p>
          <p className="text-sm text-muted-foreground">Service: {data.service}</p>
          <p className="text-sm text-muted-foreground">Provider: {data.provider}</p>
          <p className="text-sm">Cost: {formatCurrency(data.cost)}</p>
          <p className="text-sm">Usage: {data.usage.toLocaleString()}</p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
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
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              type="number" 
              dataKey="usage" 
              name="Usage"
              className="text-muted-foreground text-xs"
            />
            <YAxis 
              type="number" 
              dataKey="cost" 
              name="Cost"
              className="text-muted-foreground text-xs"
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Scatter 
              name="Services" 
              data={data} 
              fill="hsl(var(--primary))"
              fillOpacity={0.6}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

// Waterfall Chart for Cost Change Analysis
interface WaterfallData {
  name: string
  value: number
  cumulative: number
  type: 'positive' | 'negative' | 'total'
}

interface CostWaterfallChartProps {
  data: WaterfallData[]
  loading?: boolean
  title?: string
  height?: number
}

export function CostWaterfallChart({
  data,
  loading = false,
  title = "Cost Change Analysis",
  height = 400,
}: CostWaterfallChartProps) {
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
          <p className="font-medium text-foreground">{label}</p>
          <p className="text-sm">
            Change: {formatCurrency(data.value)}
          </p>
          <p className="text-sm">
            Cumulative: {formatCurrency(data.cumulative)}
          </p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
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
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="name" 
              className="text-muted-foreground text-xs"
            />
            <YAxis 
              className="text-muted-foreground text-xs"
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" fill="hsl(var(--primary))">
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={
                    entry.type === 'positive' ? '#10b981' :
                    entry.type === 'negative' ? '#ef4444' :
                    'hsl(var(--primary))'
                  } 
                />
              ))}
            </Bar>
            <Line 
              type="monotone" 
              dataKey="cumulative" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

// Box Plot for Cost Distribution Analysis
interface BoxPlotData {
  name: string
  min: number
  q1: number
  median: number
  q3: number
  max: number
  outliers?: number[]
}

interface CostBoxPlotProps {
  data: BoxPlotData[]
  loading?: boolean
  title?: string
  height?: number
}

export function CostBoxPlot({
  data,
  loading = false,
  title = "Cost Distribution Analysis",
  height = 400,
}: CostBoxPlotProps) {
  // Custom box plot implementation using ComposedChart
  const boxPlotData = data.map((item, index) => ({
    name: item.name,
    x: index,
    min: item.min,
    q1: item.q1,
    median: item.median,
    q3: item.q3,
    max: item.max,
    iqr: item.q3 - item.q1,
    outliers: item.outliers || []
  }))

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
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
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart data={boxPlotData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="name" 
              className="text-muted-foreground text-xs"
            />
            <YAxis 
              className="text-muted-foreground text-xs"
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip 
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
                      <p className="font-medium text-foreground">{label}</p>
                      <p className="text-sm">Min: {formatCurrency(data.min)}</p>
                      <p className="text-sm">Q1: {formatCurrency(data.q1)}</p>
                      <p className="text-sm">Median: {formatCurrency(data.median)}</p>
                      <p className="text-sm">Q3: {formatCurrency(data.q3)}</p>
                      <p className="text-sm">Max: {formatCurrency(data.max)}</p>
                      <p className="text-sm">IQR: {formatCurrency(data.iqr)}</p>
                    </div>
                  )
                }
                return null
              }}
            />
            {/* Box representation using bars */}
            <Bar dataKey="iqr" fill="hsl(var(--primary))" fillOpacity={0.3} />
            {/* Median line */}
            <ReferenceLine y={0} stroke="hsl(var(--primary))" strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

// Forecast Visualization with Confidence Intervals
interface ForecastData {
  date: string
  actual?: number
  predicted: number
  confidence_lower: number
  confidence_upper: number
}

interface CostForecastChartProps {
  data: ForecastData[]
  loading?: boolean
  title?: string
  height?: number
}

export function CostForecastChart({
  data,
  loading = false,
  title = "Cost Forecast with Confidence Intervals",
  height = 400,
}: CostForecastChartProps) {
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
          <p className="font-medium text-foreground">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
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
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="date" 
              className="text-muted-foreground text-xs"
            />
            <YAxis 
              className="text-muted-foreground text-xs"
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            
            {/* Confidence interval area */}
            <Area
              type="monotone"
              dataKey="confidence_upper"
              stackId="1"
              stroke="none"
              fill="hsl(var(--primary))"
              fillOpacity={0.1}
              name="Confidence Upper"
            />
            <Area
              type="monotone"
              dataKey="confidence_lower"
              stackId="1"
              stroke="none"
              fill="white"
              fillOpacity={1}
              name="Confidence Lower"
            />
            
            {/* Actual costs line */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ r: 4 }}
              name="Actual Cost"
              connectNulls={false}
            />
            
            {/* Predicted costs line */}
            <Line
              type="monotone"
              dataKey="predicted"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 4 }}
              name="Predicted Cost"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

// Cost Efficiency Metrics Dashboard
interface EfficiencyMetric {
  name: string
  current: number
  target: number
  trend: number
  unit: string
}

interface CostEfficiencyDashboardProps {
  metrics: EfficiencyMetric[]
  loading?: boolean
  title?: string
}

export function CostEfficiencyDashboard({
  metrics,
  loading = false,
  title = "Cost Efficiency Metrics",
}: CostEfficiencyDashboardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {metrics.map((metric) => {
            const efficiency = (metric.current / metric.target) * 100
            const isEfficient = efficiency <= 100
            
            return (
              <Card key={metric.name} className="p-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">{metric.name}</h4>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      isEfficient 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {efficiency.toFixed(0)}%
                    </span>
                  </div>
                  
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Current:</span>
                      <span className="font-medium">
                        {metric.current.toLocaleString()} {metric.unit}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Target:</span>
                      <span className="font-medium">
                        {metric.target.toLocaleString()} {metric.unit}
                      </span>
                    </div>
                  </div>
                  
                  {/* Progress bar */}
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        isEfficient ? 'bg-green-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(efficiency, 100)}%` }}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">
                      Trend: {metric.trend > 0 ? '+' : ''}{metric.trend.toFixed(1)}%
                    </span>
                    <span className={`${
                      isEfficient ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {isEfficient ? 'Efficient' : 'Over Target'}
                    </span>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}