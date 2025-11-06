"use client"

import React from "react"
import {
  BarChart,
  Bar,
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

interface CostBarData {
  name: string
  aws?: number
  gcp?: number
  azure?: number
  total?: number
  [key: string]: any
}

interface CostBarChartProps {
  data: CostBarData[]
  loading?: boolean
  title?: string
  height?: number
  showProviders?: boolean
  currency?: string
  stacked?: boolean
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

export function CostBarChart({
  data,
  loading = false,
  title = "Cost Comparison",
  height = 300,
  showProviders = true,
  currency = "USD",
  stacked = false,
}: CostBarChartProps) {
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
          <BarChart 
            data={data} 
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="name" 
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
                <Bar
                  dataKey="aws"
                  fill={getProviderColor("aws")}
                  name="AWS"
                  stackId={stacked ? "stack" : undefined}
                />
                <Bar
                  dataKey="gcp"
                  fill={getProviderColor("gcp")}
                  name="GCP"
                  stackId={stacked ? "stack" : undefined}
                />
                <Bar
                  dataKey="azure"
                  fill={getProviderColor("azure")}
                  name="Azure"
                  stackId={stacked ? "stack" : undefined}
                />
              </>
            )}
            
            {!stacked && (
              <Bar
                dataKey="total"
                fill="hsl(var(--primary))"
                name="Total"
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}