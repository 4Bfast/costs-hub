"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { MultiSelect } from "@/components/ui/multi-select"
import { DateRangePicker } from "@/components/ui/date-picker"
import { Badge } from "@/components/ui/badge"
import { X, Calendar, Filter } from "lucide-react"
import { cn } from "@/lib/utils"

interface InsightFiltersProps {
  filters: {
    type?: string[]
    severity?: string[]
    status?: string[]
    date_range?: { start: string; end: string }
  }
  onChange: (filters: InsightFiltersProps['filters']) => void
}

const typeOptions = [
  { value: 'anomaly', label: 'Anomalies' },
  { value: 'recommendation', label: 'Recommendations' },
  { value: 'forecast', label: 'Forecasts' },
  { value: 'optimization', label: 'Optimizations' },
  { value: 'trend', label: 'Trends' },
]

const severityOptions = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

const statusOptions = [
  { value: 'new', label: 'New' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: 'implemented', label: 'Implemented' },
  { value: 'expired', label: 'Expired' },
]

const quickDateRanges = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last 6 months', days: 180 },
]

export function InsightFilters({ filters, onChange }: InsightFiltersProps) {
  const handleFilterChange = (key: string, value: any) => {
    onChange({
      ...filters,
      [key]: value,
    })
  }

  const handleQuickDateRange = (days: number) => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - days)
    
    handleFilterChange('date_range', {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
    })
  }

  const clearFilter = (key: string) => {
    const newFilters = { ...filters }
    delete newFilters[key as keyof typeof newFilters]
    onChange(newFilters)
  }

  const clearAllFilters = () => {
    onChange({})
  }

  const hasActiveFilters = Object.keys(filters).some(key => {
    const value = filters[key as keyof typeof filters]
    return Array.isArray(value) ? value.length > 0 : !!value
  })

  const getActiveFilterCount = () => {
    let count = 0
    if (filters.type && filters.type.length > 0) count++
    if (filters.severity && filters.severity.length > 0) count++
    if (filters.status && filters.status.length > 0) count++
    if (filters.date_range) count++
    return count
  }

  return (
    <div className="space-y-6">
      {/* Filter Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Insight Type Filter */}
        <div className="space-y-2">
          <Label htmlFor="type-filter">Insight Type</Label>
          <MultiSelect
            options={typeOptions}
            selected={filters.type || []}
            onSelectionChange={(value) => handleFilterChange('type', value)}
            placeholder="Select types..."
            className="w-full"
          />
        </div>

        {/* Severity Filter */}
        <div className="space-y-2">
          <Label htmlFor="severity-filter">Severity</Label>
          <MultiSelect
            options={severityOptions}
            selected={filters.severity || []}
            onSelectionChange={(value) => handleFilterChange('severity', value)}
            placeholder="Select severity..."
            className="w-full"
          />
        </div>

        {/* Status Filter */}
        <div className="space-y-2">
          <Label htmlFor="status-filter">Status</Label>
          <MultiSelect
            options={statusOptions}
            selected={filters.status || []}
            onSelectionChange={(value) => handleFilterChange('status', value)}
            placeholder="Select status..."
            className="w-full"
          />
        </div>

        {/* Date Range Filter */}
        <div className="space-y-2">
          <Label htmlFor="date-filter">Date Range</Label>
          <div className="space-y-2">
            <DateRangePicker
              dateRange={filters.date_range ? {
                start: new Date(filters.date_range.start),
                end: new Date(filters.date_range.end)
              } : undefined}
              onDateRangeChange={(value) => handleFilterChange('date_range', value ? {
                start: value.start.toISOString().split('T')[0],
                end: value.end.toISOString().split('T')[0]
              } : undefined)}
              placeholder="Select date range..."
            />
          </div>
        </div>
      </div>

      {/* Quick Date Range Buttons */}
      <div className="space-y-2">
        <Label>Quick Date Ranges</Label>
        <div className="flex flex-wrap gap-2">
          {quickDateRanges.map((range) => (
            <Button
              key={range.days}
              variant="outline"
              size="sm"
              onClick={() => handleQuickDateRange(range.days)}
              className={cn(
                "text-xs",
                filters.date_range && "bg-primary/10 border-primary/30"
              )}
            >
              <Calendar className="h-3 w-3 mr-1" />
              {range.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="flex items-center space-x-2">
              <Filter className="h-4 w-4" />
              <span>Active Filters ({getActiveFilterCount()})</span>
            </Label>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs"
            >
              Clear All
            </Button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {/* Type Filters */}
            {filters.type?.map((type) => (
              <Badge key={`type-${type}`} variant="secondary" className="flex items-center space-x-1">
                <span className="text-xs">Type: {typeOptions.find(t => t.value === type)?.label}</span>
                <button
                  onClick={() => handleFilterChange('type', filters.type?.filter(t => t !== type))}
                  className="ml-1 hover:bg-secondary-foreground/20 rounded-full p-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}

            {/* Severity Filters */}
            {filters.severity?.map((severity) => (
              <Badge key={`severity-${severity}`} variant="secondary" className="flex items-center space-x-1">
                <span className="text-xs">Severity: {severityOptions.find(s => s.value === severity)?.label}</span>
                <button
                  onClick={() => handleFilterChange('severity', filters.severity?.filter(s => s !== severity))}
                  className="ml-1 hover:bg-secondary-foreground/20 rounded-full p-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}

            {/* Status Filters */}
            {filters.status?.map((status) => (
              <Badge key={`status-${status}`} variant="secondary" className="flex items-center space-x-1">
                <span className="text-xs">Status: {statusOptions.find(s => s.value === status)?.label}</span>
                <button
                  onClick={() => handleFilterChange('status', filters.status?.filter(s => s !== status))}
                  className="ml-1 hover:bg-secondary-foreground/20 rounded-full p-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}

            {/* Date Range Filter */}
            {filters.date_range && (
              <Badge variant="secondary" className="flex items-center space-x-1">
                <span className="text-xs">
                  Date: {filters.date_range.start} to {filters.date_range.end}
                </span>
                <button
                  onClick={() => clearFilter('date_range')}
                  className="ml-1 hover:bg-secondary-foreground/20 rounded-full p-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  )
}