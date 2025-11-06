"use client"

import React, { useState } from "react"
import { ColumnDef } from "@tanstack/react-table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DataTable, DataTableColumnHeader, DataTableRowActions } from "@/components/ui/data-table"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  Download, 
  Search, 
  Filter, 
  Eye, 
  Copy, 
  ExternalLink,
  Calendar,
  DollarSign,
  Cloud,
  Server
} from "lucide-react"
import { CostRecord, CostFilters, PaginatedResponse } from "@/types/models"
import { formatCurrency, getProviderColor } from "@/lib/utils"
import { useExportCosts } from "@/hooks/use-costs"
import { toast } from "sonner"

interface CostDataTableProps {
  data?: PaginatedResponse<CostRecord>
  loading?: boolean
  filters?: CostFilters
  onFiltersChange?: (filters: CostFilters) => void
}

export function CostDataTable({ 
  data, 
  loading = false, 
  filters,
  onFiltersChange 
}: CostDataTableProps) {
  const [selectedRecord, setSelectedRecord] = useState<CostRecord | null>(null)
  const [showDetailsDialog, setShowDetailsDialog] = useState(false)
  const [globalFilter, setGlobalFilter] = useState("")
  const [pageSize, setPageSize] = useState(50)
  
  const exportCosts = useExportCosts()

  // Define table columns
  const columns: ColumnDef<CostRecord>[] = [
    {
      accessorKey: "usage_date",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Date" />
      ),
      cell: ({ row }) => {
        const date = new Date(row.getValue("usage_date"))
        return (
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <span className="font-medium">
              {date.toLocaleDateString()}
            </span>
          </div>
        )
      },
    },
    {
      accessorKey: "provider",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Provider" />
      ),
      cell: ({ row }) => {
        const provider = row.getValue("provider") as string
        return (
          <div className="flex items-center space-x-2">
            <div 
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: getProviderColor(provider) }}
            />
            <Badge variant="outline" className="capitalize">
              {provider}
            </Badge>
          </div>
        )
      },
    },
    {
      accessorKey: "service",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Service" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center space-x-2">
          <Server className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">{row.getValue("service")}</span>
        </div>
      ),
    },
    {
      accessorKey: "account_id",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Account" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center space-x-2">
          <Cloud className="w-4 h-4 text-muted-foreground" />
          <span className="font-mono text-sm">
            {row.getValue("account_id")}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "cost",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Cost" />
      ),
      cell: ({ row }) => {
        const cost = parseFloat(row.getValue("cost"))
        const currency = row.original.currency || "USD"
        return (
          <div className="flex items-center space-x-2">
            <DollarSign className="w-4 h-4 text-muted-foreground" />
            <span className="font-semibold">
              {formatCurrency(cost, currency)}
            </span>
          </div>
        )
      },
    },
    {
      accessorKey: "region",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Region" />
      ),
      cell: ({ row }) => {
        const region = row.getValue("region") as string
        return region ? (
          <Badge variant="secondary" className="text-xs">
            {region}
          </Badge>
        ) : (
          <span className="text-muted-foreground">-</span>
        )
      },
    },
    {
      accessorKey: "usage_quantity",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Usage" />
      ),
      cell: ({ row }) => {
        const quantity = row.getValue("usage_quantity") as number
        const unit = row.original.usage_unit
        return quantity ? (
          <div className="text-sm">
            <span className="font-medium">{quantity.toLocaleString()}</span>
            {unit && <span className="text-muted-foreground ml-1">{unit}</span>}
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        )
      },
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row }) => {
        const record = row.original
        return (
          <DataTableRowActions
            row={row}
            actions={[
              {
                label: "View Details",
                onClick: (data) => {
                  setSelectedRecord(data as CostRecord)
                  setShowDetailsDialog(true)
                },
                icon: <Eye className="w-4 h-4" />
              },
              {
                label: "Copy Account ID",
                onClick: (data) => {
                  navigator.clipboard.writeText((data as CostRecord).account_id)
                  toast.success("Account ID copied to clipboard")
                },
                icon: <Copy className="w-4 h-4" />
              },
              {
                label: "View in Console",
                onClick: (data) => {
                  // This would open the cloud provider console
                  toast.info("Opening in cloud console...")
                },
                icon: <ExternalLink className="w-4 h-4" />
              }
            ]}
          />
        )
      },
    },
  ]

  const handleExport = async (format: 'csv' | 'excel' | 'json') => {
    try {
      const result = await exportCosts.mutateAsync({
        format,
        filters,
        date_range: filters?.date_range || {
          start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        }
      })
      
      if (result.download_url) {
        window.open(result.download_url, '_blank')
        toast.success(`Export started. Download will begin shortly.`)
      } else {
        toast.success(`Export job created. You'll receive a notification when ready.`)
      }
    } catch (error) {
      toast.error("Failed to export data")
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Cost Records</CardTitle>
            <div className="flex items-center space-x-2">
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-8 w-24" />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Skeleton className="h-8 flex-1 max-w-sm" />
              <Skeleton className="h-8 w-24" />
            </div>
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Cost Records</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {data?.pagination.total || 0} total records
              </p>
            </div>
            
            <div className="flex items-center space-x-2">
              <Select value={pageSize.toString()} onValueChange={(value) => setPageSize(parseInt(value))}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                  <SelectItem value="200">200</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                onClick={() => handleExport('csv')}
                disabled={exportCosts.isPending}
                className="flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </Button>

              <Button
                variant="outline"
                onClick={() => handleExport('excel')}
                disabled={exportCosts.isPending}
                className="flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Export Excel
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          {/* Search and Filters */}
          <div className="flex items-center space-x-4 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search records..."
                value={globalFilter}
                onChange={(e) => setGlobalFilter(e.target.value)}
                className="pl-10"
              />
            </div>
            
            <Button variant="outline" className="flex items-center">
              <Filter className="w-4 h-4 mr-2" />
              Advanced Filters
            </Button>
          </div>

          {/* Data Table */}
          <DataTable
            columns={columns}
            data={data?.data || []}
            searchKey="service"
            searchPlaceholder="Search by service..."
            onRowClick={(record) => {
              setSelectedRecord(record)
              setShowDetailsDialog(true)
            }}
          />

          {/* Pagination Info */}
          {data?.pagination && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <div className="text-sm text-muted-foreground">
                Showing {((data.pagination.page - 1) * data.pagination.limit) + 1} to{" "}
                {Math.min(data.pagination.page * data.pagination.limit, data.pagination.total)} of{" "}
                {data.pagination.total} records
              </div>
              
              <div className="text-sm text-muted-foreground">
                Page {data.pagination.page} of {data.pagination.totalPages}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Record Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Cost Record Details</DialogTitle>
          </DialogHeader>
          
          {selectedRecord && (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Date</label>
                  <p className="text-sm font-semibold">
                    {new Date(selectedRecord.usage_date).toLocaleDateString()}
                  </p>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Provider</label>
                  <div className="flex items-center space-x-2">
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getProviderColor(selectedRecord.provider) }}
                    />
                    <p className="text-sm font-semibold capitalize">{selectedRecord.provider}</p>
                  </div>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Service</label>
                  <p className="text-sm font-semibold">{selectedRecord.service}</p>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Account ID</label>
                  <p className="text-sm font-mono">{selectedRecord.account_id}</p>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Cost</label>
                  <p className="text-lg font-bold">
                    {formatCurrency(selectedRecord.cost, selectedRecord.currency)}
                  </p>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Region</label>
                  <p className="text-sm font-semibold">{selectedRecord.region || 'N/A'}</p>
                </div>
              </div>

              {/* Usage Information */}
              {selectedRecord.usage_quantity && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Usage</label>
                  <p className="text-sm font-semibold">
                    {selectedRecord.usage_quantity.toLocaleString()} {selectedRecord.usage_unit || 'units'}
                  </p>
                </div>
              )}

              {/* Resource Information */}
              {selectedRecord.resource_id && (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">Resource</label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-muted-foreground">Resource ID</label>
                      <p className="text-sm font-mono">{selectedRecord.resource_id}</p>
                    </div>
                    {selectedRecord.resource_type && (
                      <div>
                        <label className="text-xs text-muted-foreground">Resource Type</label>
                        <p className="text-sm">{selectedRecord.resource_type}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tags */}
              {selectedRecord.tags && Object.keys(selectedRecord.tags).length > 0 && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-2 block">Tags</label>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(selectedRecord.tags).map(([key, value]) => (
                      <Badge key={key} variant="outline" className="text-xs">
                        {key}: {value}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata */}
              <div className="pt-4 border-t">
                <label className="text-sm font-medium text-muted-foreground mb-2 block">Metadata</label>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="text-muted-foreground">Source</label>
                    <p>{selectedRecord.metadata.source}</p>
                  </div>
                  <div>
                    <label className="text-muted-foreground">Billing Period</label>
                    <p>{selectedRecord.billing_period}</p>
                  </div>
                  {selectedRecord.metadata.confidence_score && (
                    <div>
                      <label className="text-muted-foreground">Confidence</label>
                      <p>{(selectedRecord.metadata.confidence_score * 100).toFixed(1)}%</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}