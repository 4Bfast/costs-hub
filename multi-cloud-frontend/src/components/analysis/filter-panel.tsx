"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { DateRangePicker } from "@/components/ui/date-picker"
import { MultiSelect } from "@/components/ui/multi-select"
import { Slider } from "@/components/ui/slider"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { X, RotateCcw } from "lucide-react"
import { CostFilters, CloudProvider } from "@/types/models"
import { useProviderAccounts } from "@/hooks/use-accounts"
import { useFilterStore } from "@/stores/filter-store"

interface FilterPanelProps {
  filters: CostFilters
  onChange: (filters: CostFilters) => void
  onClose?: () => void
}

const PROVIDER_OPTIONS = [
  { label: "AWS", value: "aws", icon: "🟠" },
  { label: "Google Cloud", value: "gcp", icon: "🔵" },
  { label: "Microsoft Azure", value: "azure", icon: "🔷" },
]

const GROUPING_OPTIONS = [
  { label: "Service", value: "service" },
  { label: "Provider", value: "provider" },
  { label: "Account", value: "account" },
  { label: "Region", value: "region" },
  { label: "Date", value: "date" },
]

const PRESET_RANGES = [
  { label: "Last 7 days", value: "7d" },
  { label: "Last 30 days", value: "30d" },
  { label: "Last 90 days", value: "90d" },
  { label: "This month", value: "month" },
  { label: "Last month", value: "last_month" },
  { label: "This quarter", value: "quarter" },
  { label: "This year", value: "year" },
]

export function FilterPanel({ filters, onChange, onClose }: FilterPanelProps) {
  const { data: accounts } = useProviderAccounts()
  const { savedFilters, saveFilter, loadFilter, deleteFilter } = useFilterStore()
  
  const [localFilters, setLocalFilters] = useState<CostFilters>(filters)
  const [costRange, setCostRange] = useState([0, 10000])
  const [groupBy, setGroupBy] = useState("service")
  const [filterName, setFilterName] = useState("")

  // Available services (this would typically come from an API)
  const [availableServices] = useState([
    { label: "EC2", value: "ec2" },
    { label: "S3", value: "s3" },
    { label: "RDS", value: "rds" },
    { label: "Lambda", value: "lambda" },
    { label: "CloudFront", value: "cloudfront" },
    { label: "Compute Engine", value: "compute_engine" },
    { label: "Cloud Storage", value: "cloud_storage" },
    { label: "Virtual Machines", value: "virtual_machines" },
    { label: "Blob Storage", value: "blob_storage" },
  ])

  // Convert accounts to options
  const accountOptions = accounts?.map(account => ({
    label: `${account.account_name} (${account.provider.toUpperCase()})`,
    value: account.account_id,
    icon: PROVIDER_OPTIONS.find(p => p.value === account.provider)?.icon
  })) || []

  useEffect(() => {
    setLocalFilters(filters)
    if (filters.cost_range) {
      setCostRange([filters.cost_range.min, filters.cost_range.max])
    }
  }, [filters])

  const handleDateRangeChange = (range: { start: Date; end: Date } | undefined) => {
    if (range) {
      setLocalFilters(prev => ({
        ...prev,
        date_range: {
          start: range.start.toISOString().split('T')[0],
          end: range.end.toISOString().split('T')[0]
        }
      }))
    }
  }

  const handlePresetRange = (preset: string) => {
    const now = new Date()
    let start: Date
    let end = new Date()

    switch (preset) {
      case "7d":
        start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case "30d":
        start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
        break
      case "90d":
        start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
        break
      case "month":
        start = new Date(now.getFullYear(), now.getMonth(), 1)
        break
      case "last_month":
        start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
        end = new Date(now.getFullYear(), now.getMonth(), 0)
        break
      case "quarter":
        const quarter = Math.floor(now.getMonth() / 3)
        start = new Date(now.getFullYear(), quarter * 3, 1)
        break
      case "year":
        start = new Date(now.getFullYear(), 0, 1)
        break
      default:
        return
    }

    setLocalFilters(prev => ({
      ...prev,
      date_range: {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0]
      }
    }))
  }

  const handleProvidersChange = (providers: string[]) => {
    setLocalFilters(prev => ({
      ...prev,
      providers: providers as CloudProvider[]
    }))
  }

  const handleServicesChange = (services: string[]) => {
    setLocalFilters(prev => ({
      ...prev,
      services
    }))
  }

  const handleAccountsChange = (accounts: string[]) => {
    setLocalFilters(prev => ({
      ...prev,
      accounts
    }))
  }

  const handleCostRangeChange = (values: number[]) => {
    setCostRange(values)
    setLocalFilters(prev => ({
      ...prev,
      cost_range: {
        min: values[0],
        max: values[1]
      }
    }))
  }

  const handleApplyFilters = () => {
    onChange(localFilters)
    onClose?.()
  }

  const handleResetFilters = () => {
    const resetFilters: CostFilters = {
      date_range: {
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        end: new Date().toISOString().split('T')[0]
      }
    }
    setLocalFilters(resetFilters)
    setCostRange([0, 10000])
    setGroupBy("service")
  }

  const handleSaveFilter = () => {
    if (filterName.trim()) {
      saveFilter(filterName, localFilters)
      setFilterName("")
    }
  }

  const currentDateRange = localFilters.date_range ? {
    start: new Date(localFilters.date_range.start),
    end: new Date(localFilters.date_range.end)
  } : undefined

  return (
    <div className="space-y-6">
      {/* Quick Presets */}
      <div>
        <Label className="text-sm font-medium mb-3 block">Quick Date Ranges</Label>
        <div className="flex flex-wrap gap-2">
          {PRESET_RANGES.map((preset) => (
            <Button
              key={preset.value}
              variant="outline"
              size="sm"
              onClick={() => handlePresetRange(preset.value)}
            >
              {preset.label}
            </Button>
          ))}
        </div>
      </div>

      <Separator />

      {/* Date Range */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Date Range</Label>
        <DateRangePicker
          dateRange={currentDateRange}
          onDateRangeChange={handleDateRangeChange}
          placeholder="Select date range"
        />
      </div>

      {/* Providers */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Cloud Providers</Label>
        <MultiSelect
          options={PROVIDER_OPTIONS}
          selected={localFilters.providers || []}
          onSelectionChange={handleProvidersChange}
          placeholder="Select providers"
          searchPlaceholder="Search providers..."
        />
      </div>

      {/* Services */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Services</Label>
        <MultiSelect
          options={availableServices}
          selected={localFilters.services || []}
          onSelectionChange={handleServicesChange}
          placeholder="Select services"
          searchPlaceholder="Search services..."
        />
      </div>

      {/* Accounts */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Accounts</Label>
        <MultiSelect
          options={accountOptions}
          selected={localFilters.accounts || []}
          onSelectionChange={handleAccountsChange}
          placeholder="Select accounts"
          searchPlaceholder="Search accounts..."
        />
      </div>

      {/* Cost Range */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">
          Cost Range: ${costRange[0]} - ${costRange[1]}
        </Label>
        <Slider
          value={costRange}
          onValueChange={handleCostRangeChange}
          max={10000}
          min={0}
          step={100}
          className="w-full"
        />
      </div>

      {/* Group By */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Group By</Label>
        <Select value={groupBy} onValueChange={setGroupBy}>
          <SelectTrigger>
            <SelectValue placeholder="Select grouping" />
          </SelectTrigger>
          <SelectContent>
            {GROUPING_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Saved Filters */}
      {savedFilters.length > 0 && (
        <div className="space-y-3">
          <Label className="text-sm font-medium">Saved Filters</Label>
          <div className="space-y-2">
            {savedFilters.map((saved) => (
              <div key={saved.id} className="flex items-center justify-between p-2 border rounded">
                <span className="text-sm">{saved.name}</span>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setLocalFilters(saved.filters)
                      loadFilter(saved.id)
                    }}
                  >
                    Load
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteFilter(saved.id)}
                  >
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t">
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={handleResetFilters}
            className="flex items-center"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
        </div>
        
        <div className="flex items-center space-x-2">
          {onClose && (
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
          )}
          <Button onClick={handleApplyFilters}>
            Apply Filters
          </Button>
        </div>
      </div>
    </div>
  )
}