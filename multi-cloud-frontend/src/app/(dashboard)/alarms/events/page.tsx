'use client'

import { AlarmEventsTable } from '@/components/alarms/alarm-events-table'

export default function AlarmEventsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Alarm Events</h1>
        <p className="text-gray-600">
          View and manage all alarm events across your organization
        </p>
      </div>

      <AlarmEventsTable showAlarmName={true} />
    </div>
  )
}