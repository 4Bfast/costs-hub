"use client"

import React from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, getProviderColor } from "@/lib/utils"

interface CostDataPoint {
  date: string
  aws?: number
  gcp?: number
  azure?: number
  total?: number
}

interface CostLineChartProps {
  data: CostDataPoint[]
  loading?: boolean
  title?: string
  height?: number
  showProviders?: boolean
  currency?: string
}

const CustomTooltip = ({ active, payload, label, currency = "USD" }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
        <p className="font-medium text-foreground mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {formatCurrency(entry.value, currency)}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export function CostLineChart({
  data,
  loading = false,
  title = "Cost Trends",
  height = 300,
  showProviders = true,
  currency = "USD",
}: CostLineChartProps) {
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="date" 
              className="text-muted-foreground text-xs"
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              className="text-muted-foreground text-xs"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => formatCurrency(value, currency)}
            />
            <Tooltip content={<CustomTooltip currency={currency} />} />
            <Legend />
            
            {showProviders && (
              <>
                <Line
                  type="monotone"
                  dataKey="aws"
                  stroke={getProviderColor("aws")}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  name="AWS"
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="gcp"
                  stroke={getProviderColor("gcp")}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  name="GCP"
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="azure"
                  stroke={getProviderColor("azure")}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  name="Azure"
                  connectNulls={false}
                />
              </>
            )}
            
            <Line
              type="monotone"
              dataKey="total"
              stroke="hsl(var(--primary))"
              strokeWidth={3}
              dot={{ r: 5 }}
              name="Total"
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}