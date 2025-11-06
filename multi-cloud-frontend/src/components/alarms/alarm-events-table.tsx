'use client'

import { useState } from 'react'
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Eye, 
  MessageSquare,
  Pause,
  MoreHorizontal
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { AlarmEventDetails } from './alarm-event-details'
import { AlarmEventActionDialog } from './alarm-event-action-dialog'
import { useAlarmEvents } from '@/hooks/use-alarms'
import { AlarmEvent, AlarmEventStatus, InsightSeverity } from '@/types/models'
import { formatCurrency, formatDate } from '@/lib/data-utils'

const statusIcons = {
  new: AlertTriangle,
  acknowledged: CheckCircle,
  resolved: CheckCircle,
  suppressed: Pause,
}

const statusColors = {
  new: 'bg-red-100 text-red-800',
  acknowledged: 'bg-blue-100 text-blue-800',
  resolved: 'bg-green-100 text-green-800',
  suppressed: 'bg-gray-100 text-gray-800',
}

const severityColors = {
  low: 'bg-blue-100 text-blue-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

interface AlarmEventsTableProps {
  alarmId?: string
  showAlarmName?: boolean
}

export function AlarmEventsTable({ alarmId, showAlarmName = false }: AlarmEventsTableProps) {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<AlarmEventStatus | 'all'>('all')
  const [severityFilter, setSeverityFilter] = useState<InsightSeverity | 'all'>('all')
  const [selectedEvent, setSelectedEvent] = useState<AlarmEvent | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [actionType, setActionType] = useState<'acknowledge' | 'dismiss' | 'snooze' | null>(null)
  const [isActionDialogOpen, setIsActionDialogOpen] = useState(false)

  const {
    events,
    pagination,
    isLoading,
    acknowledgeEvent,
    dismissEvent,
    snoozeEvent,
    isAcknowledging,
    isDismissing,
    isSnoozing,
  } = useAlarmEvents(alarmId, page, 20)

  const filteredEvents = events.filter((event) => {
    const matchesStatus = statusFilter === 'all' || event.status === statusFilter
    const matchesSeverity = severityFilter === 'all' || event.severity === severityFilter
    return matchesStatus && matchesSeverity
  })

  const handleViewDetails = (event: AlarmEvent) => {
    setSelectedEvent(event)
    setIsDetailsOpen(true)
  }

  const handleAction = (event: AlarmEvent, action: 'acknowledge' | 'dismiss' | 'snooze') => {
    setSelectedEvent(event)
    setActionType(action)
    setIsActionDialogOpen(true)
  }

  const handleActionSubmit = async (notes?: string, duration?: number) => {
    if (!selectedEvent || !actionType) return

    try {
      switch (actionType) {
        case 'acknowledge':
          await acknowledgeEvent(selectedEvent.id, notes)
          break
        case 'dismiss':
          await dismissEvent(selectedEvent.id, notes)
          break
        case 'snooze':
          if (duration) {
            await snoozeEvent(selectedEvent.id, duration, notes)
          }
          break
      }
      setIsActionDialogOpen(false)
      setSelectedEvent(null)
      setActionType(null)
    } catch (error) {
      console.error('Failed to perform action:', error)
    }
  }

  const getActionButtonText = () => {
    switch (actionType) {
      case 'acknowledge':
        return isAcknowledging ? 'Acknowledging...' : 'Acknowledge'
      case 'dismiss':
        return isDismissing ? 'Dismissing...' : 'Dismiss'
      case 'snooze':
        return isSnoozing ? 'Snoozing...' : 'Snooze'
      default:
        return 'Submit'
    }
  }

  const isActionLoading = isAcknowledging || isDismissing || isSnoozing

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as AlarmEventStatus | 'all')}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="acknowledged">Acknowledged</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="suppressed">Suppressed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={severityFilter} onValueChange={(value) => setSeverityFilter(value as InsightSeverity | 'all')}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Events Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Alarm Events ({filteredEvents.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : filteredEvents.length === 0 ? (
            <div className="text-center py-8">
              <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No events found</h3>
              <p className="text-gray-600">
                {statusFilter !== 'all' || severityFilter !== 'all'
                  ? 'No events match your current filters.'
                  : 'No alarm events have been triggered yet.'}
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    {showAlarmName && <TableHead>Alarm</TableHead>}
                    <TableHead>Triggered</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Current Value</TableHead>
                    <TableHead>Threshold</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEvents.map((event) => {
                    const StatusIcon = statusIcons[event.status]
                    return (
                      <TableRow key={event.id}>
                        {showAlarmName && (
                          <TableCell>
                            <div className="font-medium">Alarm Name</div>
                          </TableCell>
                        )}
                        <TableCell>
                          <div>
                            <div className="font-medium">
                              {formatDate(event.triggered_at)}
                            </div>
                            {event.resolved_at && (
                              <div className="text-sm text-gray-500">
                                Resolved: {formatDate(event.resolved_at)}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <StatusIcon className="h-4 w-4" />
                            <Badge variant="secondary" className={statusColors[event.status]}>
                              {event.status}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={severityColors[event.severity]}>
                            {event.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className="font-medium">
                            {formatCurrency(event.current_value)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="font-medium">
                            {formatCurrency(event.threshold_value)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="max-w-xs truncate" title={event.message}>
                            {event.message}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewDetails(event)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            {event.status === 'new' && (
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="sm">
                                    <MoreHorizontal className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                  <DropdownMenuItem 
                                    onClick={() => handleAction(event, 'acknowledge')}
                                  >
                                    <CheckCircle className="h-4 w-4 mr-2" />
                                    Acknowledge
                                  </DropdownMenuItem>
                                  <DropdownMenuItem 
                                    onClick={() => handleAction(event, 'dismiss')}
                                  >
                                    <XCircle className="h-4 w-4 mr-2" />
                                    Dismiss
                                  </DropdownMenuItem>
                                  <DropdownMenuItem 
                                    onClick={() => handleAction(event, 'snooze')}
                                  >
                                    <Pause className="h-4 w-4 mr-2" />
                                    Snooze
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>

              {/* Pagination */}
              {pagination && pagination.totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-gray-500">
                    Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, pagination.total)} of {pagination.total} events
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={!pagination.hasPrev}
                    >
                      Previous
                    </Button>
                    <span className="text-sm">
                      Page {page} of {pagination.totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={!pagination.hasNext}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Event Details Dialog */}
      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Alarm Event Details</DialogTitle>
          </DialogHeader>
          {selectedEvent && (
            <AlarmEventDetails 
              event={selectedEvent} 
              onClose={() => setIsDetailsOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Action Dialog */}
      <AlarmEventActionDialog
        isOpen={isActionDialogOpen}
        onClose={() => {
          setIsActionDialogOpen(false)
          setSelectedEvent(null)
          setActionType(null)
        }}
        onSubmit={handleActionSubmit}
        actionType={actionType}
        event={selectedEvent}
        isLoading={isActionLoading}
        submitButtonText={getActionButtonText()}
      />
    </div>
  )
}