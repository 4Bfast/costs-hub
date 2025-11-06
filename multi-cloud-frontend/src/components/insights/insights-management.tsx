"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { 
  CheckSquare,
  Square,
  MoreHorizontal,
  Check,
  X,
  Archive,
  Download,
  History,
  Eye,
  Filter,
  SortAsc,
  SortDesc
} from "lucide-react"
import { formatDate, cn } from "@/lib/utils"
import { AIInsight } from "@/types/models"
import { 
  useBulkUpdateInsights, 
  useExportInsights,
  useInsightHistory 
} from "@/hooks/use-insights"
import { toast } from "sonner"

interface InsightsManagementProps {
  insights: AIInsight[]
  selectedInsights: string[]
  onSelectionChange: (selected: string[]) => void
  onRefresh?: () => void
}

export function InsightsManagement({
  insights,
  selectedInsights,
  onSelectionChange,
  onRefresh
}: InsightsManagementProps) {
  const [showBulkDialog, setShowBulkDialog] = useState(false)
  const [bulkAction, setBulkAction] = useState<'acknowledged' | 'dismissed' | 'implemented' | null>(null)
  const [bulkNotes, setBulkNotes] = useState("")
  const [showHistoryDialog, setShowHistoryDialog] = useState(false)
  const [selectedInsightForHistory, setSelectedInsightForHistory] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<'created_at' | 'severity' | 'type' | 'status'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const bulkUpdate = useBulkUpdateInsights()
  const exportInsights = useExportInsights()
  const { data: historyData } = useInsightHistory(selectedInsightForHistory || '')

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(insights.map(insight => insight.id))
    } else {
      onSelectionChange([])
    }
  }

  const handleSelectInsight = (insightId: string, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedInsights, insightId])
    } else {
      onSelectionChange(selectedInsights.filter(id => id !== insightId))
    }
  }

  const handleBulkAction = async () => {
    if (!bulkAction || selectedInsights.length === 0) return

    try {
      await bulkUpdate.mutateAsync({
        insightIds: selectedInsights,
        status: bulkAction,
        notes: bulkNotes || undefined,
      })
      
      setShowBulkDialog(false)
      setBulkAction(null)
      setBulkNotes("")
      onSelectionChange([])
      
      if (onRefresh) {
        onRefresh()
      }
    } catch (error) {
      toast.error('Failed to update insights')
    }
  }

  const handleExport = async (format: 'csv' | 'excel' | 'json') => {
    try {
      await exportInsights.mutateAsync({
        format,
        filters: selectedInsights.length > 0 ? {
          // Export only selected insights if any are selected
        } : undefined,
        include_recommendations: true,
      })
    } catch (error) {
      toast.error('Failed to export insights')
    }
  }

  const handleViewHistory = (insightId: string) => {
    setSelectedInsightForHistory(insightId)
    setShowHistoryDialog(true)
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200'
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return 'bg-blue-100 text-blue-800'
      case 'acknowledged': return 'bg-yellow-100 text-yellow-800'
      case 'dismissed': return 'bg-gray-100 text-gray-800'
      case 'implemented': return 'bg-green-100 text-green-800'
      case 'expired': return 'bg-gray-100 text-gray-600'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const sortedInsights = [...insights].sort((a, b) => {
    let aValue: any = a[sortBy]
    let bValue: any = b[sortBy]
    
    if (sortBy === 'created_at') {
      aValue = new Date(aValue).getTime()
      bValue = new Date(bValue).getTime()
    }
    
    if (sortOrder === 'asc') {
      return aValue > bValue ? 1 : -1
    } else {
      return aValue < bValue ? 1 : -1
    }
  })

  const allSelected = insights.length > 0 && selectedInsights.length === insights.length
  const someSelected = selectedInsights.length > 0 && selectedInsights.length < insights.length

  return (
    <div className="space-y-4">
      {/* Management Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Insights Management</CardTitle>
            <div className="flex items-center space-x-2">
              {/* Sort Controls */}
              <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at">Date</SelectItem>
                  <SelectItem value="severity">Severity</SelectItem>
                  <SelectItem value="type">Type</SelectItem>
                  <SelectItem value="status">Status</SelectItem>
                </SelectContent>
              </Select>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              >
                {sortOrder === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            {/* Selection Controls */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  checked={allSelected}
                  onCheckedChange={handleSelectAll}
                />
                <span className="text-sm text-muted-foreground">
                  {selectedInsights.length > 0 
                    ? `${selectedInsights.length} of ${insights.length} selected`
                    : `Select all ${insights.length} insights`
                  }
                </span>
              </div>
              
              {selectedInsights.length > 0 && (
                <Badge variant="secondary">
                  {selectedInsights.length} selected
                </Badge>
              )}
            </div>

            {/* Action Controls */}
            <div className="flex items-center space-x-2">
              {/* Bulk Actions */}
              {selectedInsights.length > 0 && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <CheckSquare className="h-4 w-4 mr-2" />
                      Bulk Actions
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem 
                      onClick={() => {
                        setBulkAction('acknowledged')
                        setShowBulkDialog(true)
                      }}
                    >
                      <Check className="h-4 w-4 mr-2" />
                      Acknowledge Selected
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => {
                        setBulkAction('dismissed')
                        setShowBulkDialog(true)
                      }}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Dismiss Selected
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => {
                        setBulkAction('implemented')
                        setShowBulkDialog(true)
                      }}
                    >
                      <Archive className="h-4 w-4 mr-2" />
                      Mark as Implemented
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}

              {/* Export Options */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleExport('csv')}>
                    Export as CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport('excel')}>
                    Export as Excel
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport('json')}>
                    Export as JSON
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Insights List */}
      <Card>
        <CardContent className="p-0">
          <div className="divide-y">
            {sortedInsights.map((insight) => (
              <div key={insight.id} className="p-4 hover:bg-muted/50 transition-colors">
                <div className="flex items-start space-x-3">
                  <Checkbox
                    checked={selectedInsights.includes(insight.id)}
                    onCheckedChange={(checked) => handleSelectInsight(insight.id, checked as boolean)}
                    className="mt-1"
                  />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <h4 className="font-medium text-sm text-foreground truncate">
                          {insight.title}
                        </h4>
                        <Badge 
                          variant="outline" 
                          className={cn("text-xs", getSeverityColor(insight.severity))}
                        >
                          {insight.severity}
                        </Badge>
                        <Badge variant="secondary" className="text-xs capitalize">
                          {insight.type}
                        </Badge>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Badge 
                          variant="outline" 
                          className={cn("text-xs", getStatusColor(insight.status))}
                        >
                          {insight.status}
                        </Badge>
                        
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleViewHistory(insight.id)}>
                              <History className="h-4 w-4 mr-2" />
                              View History
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            {insight.status === 'new' && (
                              <DropdownMenuItem>
                                <Check className="h-4 w-4 mr-2" />
                                Acknowledge
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem>
                              <X className="h-4 w-4 mr-2" />
                              Dismiss
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                    
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                      {insight.summary || insight.description}
                    </p>
                    
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Created: {formatDate(insight.created_at)}</span>
                      <span>Confidence: {Math.round(insight.confidence_score * 100)}%</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Bulk Action Dialog */}
      <Dialog open={showBulkDialog} onOpenChange={setShowBulkDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Bulk Action: {bulkAction && bulkAction.charAt(0).toUpperCase() + bulkAction.slice(1)}
            </DialogTitle>
            <DialogDescription>
              You are about to {bulkAction} {selectedInsights.length} insight{selectedInsights.length !== 1 ? 's' : ''}.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="bulk-notes">Notes (optional)</Label>
              <Textarea
                id="bulk-notes"
                value={bulkNotes}
                onChange={(e) => setBulkNotes(e.target.value)}
                placeholder="Add notes about this bulk action..."
                className="mt-1"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleBulkAction}
              disabled={bulkUpdate.isPending}
            >
              {bulkUpdate.isPending ? 'Processing...' : `${bulkAction && bulkAction.charAt(0).toUpperCase() + bulkAction.slice(1)} ${selectedInsights.length} Insight${selectedInsights.length !== 1 ? 's' : ''}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Dialog */}
      <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Insight History</DialogTitle>
            <DialogDescription>
              View the complete history and audit trail for this insight.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {historyData && historyData.length > 0 ? (
              historyData.map((entry) => (
                <div key={entry.id} className="flex items-start space-x-3 p-3 bg-muted/50 rounded-lg">
                  <div className="p-1 bg-primary/10 rounded">
                    <History className="h-3 w-3 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-sm capitalize">
                        {entry.action.replace('_', ' ')}
                      </p>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(entry.timestamp)}
                      </span>
                    </div>
                    
                    {entry.user_name && (
                      <p className="text-xs text-muted-foreground mb-1">
                        by {entry.user_name}
                      </p>
                    )}
                    
                    {entry.details.notes && (
                      <p className="text-sm text-muted-foreground">
                        {entry.details.notes}
                      </p>
                    )}
                    
                    {entry.details.old_status && entry.details.new_status && (
                      <div className="flex items-center space-x-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {entry.details.old_status}
                        </Badge>
                        <span className="text-xs text-muted-foreground">→</span>
                        <Badge variant="outline" className="text-xs">
                          {entry.details.new_status}
                        </Badge>
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <History className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
                <p className="text-sm">No history available for this insight</p>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowHistoryDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}