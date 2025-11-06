'use client'

import { useState } from 'react'
import { Plus, Search, MoreHorizontal, Bell, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { AlarmForm } from '@/components/alarms/alarm-form'
import { useAlarms } from '@/hooks/use-alarms'
import { Alarm, AlarmStatus, AlarmType } from '@/types/models'
import { formatCurrency, formatDate } from '@/lib/data-utils'

const statusIcons = {
  active: CheckCircle,
  inactive: XCircle,
  paused: AlertTriangle,
  error: XCircle,
}

const statusColors = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-800',
  paused: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
}

const typeColors = {
  threshold: 'bg-blue-100 text-blue-800',
  anomaly: 'bg-purple-100 text-purple-800',
  budget: 'bg-green-100 text-green-800',
  forecast: 'bg-orange-100 text-orange-800',
  efficiency: 'bg-indigo-100 text-indigo-800',
}

export default function AlarmsPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<AlarmStatus | 'all'>('all')
  const [typeFilter, setTypeFilter] = useState<AlarmType | 'all'>('all')
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [selectedAlarm, setSelectedAlarm] = useState<Alarm | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)

  const { 
    alarms, 
    isLoading, 
    createAlarm, 
    updateAlarm, 
    deleteAlarm, 
    toggleAlarmStatus 
  } = useAlarms()

  const filteredAlarms = alarms?.filter((alarm) => {
    if (!alarm) return false;
    
    const matchesSearch = (alarm.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (alarm.description || '').toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || alarm.status === statusFilter
    const matchesType = typeFilter === 'all' || alarm.type === typeFilter
    
    return matchesSearch && matchesStatus && matchesType
  }) || []

  const handleCreateAlarm = async (alarmData: Partial<Alarm>) => {
    try {
      await createAlarm(alarmData)
      setIsCreateDialogOpen(false)
    } catch (error) {
      console.error('Failed to create alarm:', error)
    }
  }

  const handleEditAlarm = async (alarmData: Partial<Alarm>) => {
    if (!selectedAlarm) return
    
    try {
      await updateAlarm(selectedAlarm.id, alarmData)
      setIsEditDialogOpen(false)
      setSelectedAlarm(null)
    } catch (error) {
      console.error('Failed to update alarm:', error)
    }
  }

  const handleDeleteAlarm = async (alarmId: string) => {
    try {
      await deleteAlarm(alarmId)
    } catch (error) {
      console.error('Failed to delete alarm:', error)
    }
  }

  const handleToggleStatus = async (alarmId: string, currentStatus: AlarmStatus) => {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active'
    try {
      await toggleAlarmStatus(alarmId, newStatus)
    } catch (error) {
      console.error('Failed to toggle alarm status:', error)
    }
  }

  const openEditDialog = (alarm: Alarm) => {
    setSelectedAlarm(alarm)
    setIsEditDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Cost Alarms</h1>
          <p className="text-gray-600">
            Monitor and manage cost alerts across your cloud providers
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Alarm
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create New Alarm</DialogTitle>
            </DialogHeader>
            <AlarmForm onSubmit={handleCreateAlarm} onCancel={() => setIsCreateDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Search alarms..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as AlarmStatus | 'all')}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
                <SelectItem value="error">Error</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value as AlarmType | 'all')}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="threshold">Threshold</SelectItem>
                <SelectItem value="anomaly">Anomaly</SelectItem>
                <SelectItem value="budget">Budget</SelectItem>
                <SelectItem value="forecast">Forecast</SelectItem>
                <SelectItem value="efficiency">Efficiency</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Alarms Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Alarms ({filteredAlarms.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : filteredAlarms.length === 0 ? (
            <div className="text-center py-8">
              <Bell className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No alarms found</h3>
              <p className="text-gray-600 mb-4">
                {searchTerm || statusFilter !== 'all' || typeFilter !== 'all'
                  ? 'No alarms match your current filters.'
                  : 'Create your first alarm to start monitoring costs.'}
              </p>
              {!searchTerm && statusFilter === 'all' && typeFilter === 'all' && (
                <Button onClick={() => setIsCreateDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Alarm
                </Button>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Last Triggered</TableHead>
                  <TableHead>Trigger Count</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAlarms.map((alarm) => {
                  const StatusIcon = statusIcons[alarm.status]
                  return (
                    <TableRow key={alarm.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{alarm.name}</div>
                          {alarm.description && (
                            <div className="text-sm text-gray-500 truncate max-w-xs">
                              {alarm.description}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={typeColors[alarm.type]}>
                          {alarm.type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <StatusIcon className="h-4 w-4" />
                          <Badge variant="secondary" className={statusColors[alarm.status]}>
                            {alarm.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        {alarm.configuration.threshold ? (
                          <span className="font-medium">
                            {formatCurrency(alarm.configuration.threshold)}
                          </span>
                        ) : (
                          <span className="text-gray-500">N/A</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {alarm.last_triggered ? (
                          <span className="text-sm">
                            {formatDate(alarm.last_triggered)}
                          </span>
                        ) : (
                          <span className="text-gray-500">Never</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="font-medium">{alarm.trigger_count}</span>
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuItem onClick={() => openEditDialog(alarm)}>
                              Edit Alarm
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => handleToggleStatus(alarm.id, alarm.status)}
                            >
                              {alarm.status === 'active' ? 'Disable' : 'Enable'} Alarm
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem 
                              onClick={() => handleDeleteAlarm(alarm.id)}
                              className="text-red-600"
                            >
                              Delete Alarm
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Alarm</DialogTitle>
          </DialogHeader>
          {selectedAlarm && (
            <AlarmForm 
              alarm={selectedAlarm}
              onSubmit={handleEditAlarm} 
              onCancel={() => {
                setIsEditDialogOpen(false)
                setSelectedAlarm(null)
              }} 
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}