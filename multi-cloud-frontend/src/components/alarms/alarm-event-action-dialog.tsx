'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { AlarmEvent } from '@/types/models'

interface AlarmEventActionDialogProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (notes?: string, duration?: number) => void
  actionType: 'acknowledge' | 'dismiss' | 'snooze' | null
  event: AlarmEvent | null
  isLoading: boolean
  submitButtonText: string
}

const snoozeOptions = [
  { value: 60, label: '1 hour' },
  { value: 240, label: '4 hours' },
  { value: 480, label: '8 hours' },
  { value: 1440, label: '24 hours' },
  { value: 2880, label: '2 days' },
  { value: 10080, label: '1 week' },
]

const actionDescriptions = {
  acknowledge: 'Mark this event as acknowledged. The event will remain visible but will be marked as seen.',
  dismiss: 'Dismiss this event. The event will be marked as resolved and will not trigger further notifications.',
  snooze: 'Temporarily suppress notifications for this event. The event will remain active but notifications will be paused for the selected duration.',
}

export function AlarmEventActionDialog({
  isOpen,
  onClose,
  onSubmit,
  actionType,
  event,
  isLoading,
  submitButtonText,
}: AlarmEventActionDialogProps) {
  const [notes, setNotes] = useState('')
  const [snoozeDuration, setSnoozeDuration] = useState<number>(240) // Default 4 hours

  const handleSubmit = () => {
    if (actionType === 'snooze') {
      onSubmit(notes || undefined, snoozeDuration)
    } else {
      onSubmit(notes || undefined)
    }
    setNotes('')
    setSnoozeDuration(240)
  }

  const handleClose = () => {
    setNotes('')
    setSnoozeDuration(240)
    onClose()
  }

  if (!actionType || !event) return null

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="capitalize">
            {actionType} Alarm Event
          </DialogTitle>
          <DialogDescription>
            {actionDescriptions[actionType]}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Event Summary */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-sm font-medium text-gray-900 mb-1">
              Event: {event.message}
            </div>
            <div className="text-sm text-gray-500">
              Triggered: {new Date(event.triggered_at).toLocaleString()}
            </div>
          </div>

          {/* Snooze Duration Selection */}
          {actionType === 'snooze' && (
            <div className="space-y-2">
              <Label htmlFor="duration">Snooze Duration</Label>
              <Select 
                value={snoozeDuration.toString()} 
                onValueChange={(value) => setSnoozeDuration(Number(value))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select duration" />
                </SelectTrigger>
                <SelectContent>
                  {snoozeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value.toString()}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">
              Notes {actionType === 'acknowledge' ? '(optional)' : '(optional)'}
            </Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={`Add notes about this ${actionType} action...`}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {submitButtonText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}