"use client"

import React, { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Download, FileText, Table, Code } from "lucide-react"
import { CostFilters } from "@/types/models"
import { useExportCosts } from "@/hooks/use-costs"
import { toast } from "sonner"

interface ExportDialogProps {
  open: boolean
  onClose: () => void
  filters?: CostFilters
}

const EXPORT_FORMATS = [
  { 
    value: "csv", 
    label: "CSV", 
    description: "Comma-separated values for spreadsheet applications",
    icon: Table 
  },
  { 
    value: "excel", 
    label: "Excel", 
    description: "Microsoft Excel format with formatting",
    icon: FileText 
  },
  { 
    value: "json", 
    label: "JSON", 
    description: "JavaScript Object Notation for developers",
    icon: Code 
  },
]

const AVAILABLE_COLUMNS = [
  { id: "usage_date", label: "Date", required: true },
  { id: "provider", label: "Provider", required: true },
  { id: "service", label: "Service", required: true },
  { id: "account_id", label: "Account ID", required: true },
  { id: "cost", label: "Cost", required: true },
  { id: "currency", label: "Currency", required: false },
  { id: "region", label: "Region", required: false },
  { id: "availability_zone", label: "Availability Zone", required: false },
  { id: "usage_quantity", label: "Usage Quantity", required: false },
  { id: "usage_unit", label: "Usage Unit", required: false },
  { id: "resource_id", label: "Resource ID", required: false },
  { id: "resource_type", label: "Resource Type", required: false },
  { id: "service_category", label: "Service Category", required: false },
  { id: "billing_period", label: "Billing Period", required: false },
  { id: "tags", label: "Tags", required: false },
]

export function ExportDialog({ open, onClose, filters }: ExportDialogProps) {
  const [format, setFormat] = useState<'csv' | 'excel' | 'json'>('csv')
  const [selectedColumns, setSelectedColumns] = useState<string[]>(
    AVAILABLE_COLUMNS.filter(col => col.required).map(col => col.id)
  )
  const [includeMetadata, setIncludeMetadata] = useState(false)
  const [includeTags, setIncludeTags] = useState(true)
  const [groupBy, setGroupBy] = useState<string[]>([])

  const exportCosts = useExportCosts()

  const handleColumnToggle = (columnId: string, checked: boolean) => {
    if (checked) {
      setSelectedColumns(prev => [...prev, columnId])
    } else {
      // Don't allow unchecking required columns
      const column = AVAILABLE_COLUMNS.find(col => col.id === columnId)
      if (!column?.required) {
        setSelectedColumns(prev => prev.filter(id => id !== columnId))
      }
    }
  }

  const handleSelectAll = () => {
    setSelectedColumns(AVAILABLE_COLUMNS.map(col => col.id))
  }

  const handleSelectRequired = () => {
    setSelectedColumns(AVAILABLE_COLUMNS.filter(col => col.required).map(col => col.id))
  }

  const handleExport = async () => {
    try {
      const exportRequest = {
        format,
        filters,
        columns: selectedColumns,
        date_range: filters?.date_range || {
          start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        },
        options: {
          include_metadata: includeMetadata,
          include_tags: includeTags,
          group_by: groupBy.length > 0 ? groupBy : undefined
        }
      }

      const result = await exportCosts.mutateAsync(exportRequest)
      
      if (result.download_url) {
        // Direct download
        window.open(result.download_url, '_blank')
        toast.success(`Export completed. Download started.`)
      } else {
        // Async export job
        toast.success(`Export job created (ID: ${result.job_id}). You'll receive a notification when ready.`)
      }
      
      onClose()
    } catch (error) {
      toast.error("Failed to export data. Please try again.")
    }
  }

  const selectedFormat = EXPORT_FORMATS.find(f => f.value === format)
  const Icon = selectedFormat?.icon || Download

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Download className="w-5 h-5" />
            <span>Export Cost Data</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Export Format Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Export Format</Label>
            <div className="grid grid-cols-1 gap-3">
              {EXPORT_FORMATS.map((formatOption) => {
                const FormatIcon = formatOption.icon
                return (
                  <Card 
                    key={formatOption.value}
                    className={`cursor-pointer transition-colors ${
                      format === formatOption.value 
                        ? 'border-primary bg-primary/5' 
                        : 'hover:bg-muted/50'
                    }`}
                    onClick={() => setFormat(formatOption.value as any)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-md ${
                          format === formatOption.value 
                            ? 'bg-primary text-primary-foreground' 
                            : 'bg-muted'
                        }`}>
                          <FormatIcon className="w-4 h-4" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-medium">{formatOption.label}</h4>
                          <p className="text-sm text-muted-foreground">
                            {formatOption.description}
                          </p>
                        </div>
                        <div className={`w-4 h-4 rounded-full border-2 ${
                          format === formatOption.value 
                            ? 'border-primary bg-primary' 
                            : 'border-muted-foreground'
                        }`}>
                          {format === formatOption.value && (
                            <div className="w-full h-full rounded-full bg-white scale-50" />
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>

          <Separator />

          {/* Column Selection */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Columns to Export</Label>
              <div className="flex items-center space-x-2">
                <Button variant="outline" size="sm" onClick={handleSelectRequired}>
                  Required Only
                </Button>
                <Button variant="outline" size="sm" onClick={handleSelectAll}>
                  Select All
                </Button>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3 max-h-48 overflow-y-auto">
              {AVAILABLE_COLUMNS.map((column) => (
                <div key={column.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={column.id}
                    checked={selectedColumns.includes(column.id)}
                    onCheckedChange={(checked) => 
                      handleColumnToggle(column.id, !!checked)
                    }
                    disabled={column.required}
                  />
                  <Label 
                    htmlFor={column.id} 
                    className={`text-sm ${column.required ? 'font-medium' : ''}`}
                  >
                    {column.label}
                    {column.required && <span className="text-red-500 ml-1">*</span>}
                  </Label>
                </div>
              ))}
            </div>
            
            <p className="text-xs text-muted-foreground">
              * Required columns cannot be deselected
            </p>
          </div>

          <Separator />

          {/* Export Options */}
          <div className="space-y-4">
            <Label className="text-sm font-medium">Export Options</Label>
            
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="include-metadata"
                  checked={includeMetadata}
                  onCheckedChange={(checked) => setIncludeMetadata(!!checked)}
                />
                <Label htmlFor="include-metadata" className="text-sm">
                  Include metadata (source, confidence scores, etc.)
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="include-tags"
                  checked={includeTags}
                  onCheckedChange={(checked) => setIncludeTags(!!checked)}
                />
                <Label htmlFor="include-tags" className="text-sm">
                  Include resource tags
                </Label>
              </div>
            </div>

            {/* Grouping Options */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Group By (Optional)</Label>
              <Select 
                value={groupBy.join(',')} 
                onValueChange={(value) => setGroupBy(value ? value.split(',') : [])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="No grouping" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No grouping</SelectItem>
                  <SelectItem value="provider">Provider</SelectItem>
                  <SelectItem value="service">Service</SelectItem>
                  <SelectItem value="account_id">Account</SelectItem>
                  <SelectItem value="region">Region</SelectItem>
                  <SelectItem value="provider,service">Provider + Service</SelectItem>
                  <SelectItem value="service,region">Service + Region</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Export Summary */}
          <Card className="bg-muted/50">
            <CardContent className="p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Icon className="w-4 h-4" />
                <span className="font-medium">Export Summary</span>
              </div>
              <div className="space-y-1 text-sm text-muted-foreground">
                <p>Format: {selectedFormat?.label}</p>
                <p>Columns: {selectedColumns.length} selected</p>
                {filters?.date_range && (
                  <p>
                    Date Range: {filters.date_range.start} to {filters.date_range.end}
                  </p>
                )}
                {filters?.providers?.length && (
                  <p>Providers: {filters.providers.join(', ')}</p>
                )}
                {groupBy.length > 0 && (
                  <p>Grouped by: {groupBy.join(', ')}</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleExport}
            disabled={exportCosts.isPending || selectedColumns.length === 0}
            className="flex items-center space-x-2"
          >
            {exportCosts.isPending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Exporting...</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>Export Data</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}