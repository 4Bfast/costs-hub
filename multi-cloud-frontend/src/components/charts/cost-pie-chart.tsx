"use client"

import React from "react"
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, getProviderColor } from "@/lib/utils"

interface CostBreakdownData {
  name: string
  value: number
  provider?: string
  color?: string
}

interface CostPieChartProps {
  data: CostBreakdownData[]
  loading?: boolean
  title?: string
  height?: number
  currency?: string
  showLegend?: boolean
}

const CustomTooltip = ({ active, payload, currency = "USD" }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
        <p className="font-medium text-foreground">{data.name}</p>
        <p className="text-sm text-muted-foreground">
          {formatCurrency(data.value, currency)}
        </p>
        <p className="text-xs text-muted-foreground">
          {((data.value / data.total) * 100).toFixed(1)}% of total
        </p>
      </div>
    )
  }
  return null
}

const COLORS = [
  "hsl(var(--primary))",
  "hsl(var(--secondary))",
  "#ff9900", // AWS Orange
  "#4285f4", // GCP Blue
  "#0078d4", // Azure Blue
  "#8b5cf6", // Purple
  "#10b981", // Green
  "#f59e0b", // Yellow
  "#ef4444", // Red
  "#6b7280", // Gray
]

export function CostPieChart({
  data,
  loading = false,
  title = "Cost Breakdown",
  height = 300,
  currency = "USD",
  showLegend = true,
}: CostPieChartProps) {
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

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div 
            className="flex items-center justify-center text-muted-foreground"
            style={{ height: `${height}px` }}
          >
            No cost data available
          </div>
        </CardContent>
      </Card>
    )
  }

  // Calculate total for percentage calculations
  const total = data.reduce((sum, item) => sum + item.value, 0)
  const dataWithTotal = data.map(item => ({ ...item, total }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={dataWithTotal}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {dataWithTotal.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={
                    entry.color || 
                    (entry.provider ? getProviderColor(entry.provider) : COLORS[index % COLORS.length])
                  } 
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip currency={currency} />} />
            {showLegend && <Legend />}
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}