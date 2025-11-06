import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { Alarm, AlarmStatus, AlarmEvent, PaginatedResponse } from '@/types/models'
import { toast } from '@/hooks/use-toast'

// API functions
const alarmsApi = {
  getAlarms: async (): Promise<Alarm[]> => {
    const response = await apiClient.get<Alarm[]>('/alarms')
    return response.data
  },

  getAlarm: async (id: string): Promise<Alarm> => {
    const response = await apiClient.get<Alarm>(`/alarms/${id}`)
    return response.data
  },

  createAlarm: async (alarmData: Partial<Alarm>): Promise<Alarm> => {
    const response = await apiClient.post<Alarm>('/alarms', alarmData)
    return response.data
  },

  updateAlarm: async (id: string, alarmData: Partial<Alarm>): Promise<Alarm> => {
    const response = await apiClient.put<Alarm>(`/alarms/${id}`, alarmData)
    return response.data
  },

  deleteAlarm: async (id: string): Promise<void> => {
    await apiClient.delete(`/alarms/${id}`)
  },

  toggleAlarmStatus: async (id: string, status: AlarmStatus): Promise<Alarm> => {
    const response = await apiClient.patch<Alarm>(`/alarms/${id}/status`, { status })
    return response.data
  },

  testAlarm: async (id: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>(`/alarms/${id}/test`)
    return response.data
  },

  getAlarmEvents: async (alarmId?: string, page = 1, limit = 20): Promise<PaginatedResponse<AlarmEvent>> => {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    })
    
    if (alarmId) {
      params.append('alarm_id', alarmId)
    }

    const response = await apiClient.get<AlarmEvent[]>(`/alarm-events?${params}`)
    return response as PaginatedResponse<AlarmEvent>
  },

  acknowledgeAlarmEvent: async (eventId: string, notes?: string): Promise<AlarmEvent> => {
    const response = await apiClient.patch<AlarmEvent>(`/alarm-events/${eventId}/acknowledge`, { notes })
    return response.data
  },

  dismissAlarmEvent: async (eventId: string, notes?: string): Promise<AlarmEvent> => {
    const response = await apiClient.patch<AlarmEvent>(`/alarm-events/${eventId}/dismiss`, { notes })
    return response.data
  },

  snoozeAlarmEvent: async (eventId: string, duration: number, notes?: string): Promise<AlarmEvent> => {
    const response = await apiClient.patch<AlarmEvent>(`/alarm-events/${eventId}/snooze`, { 
      duration, 
      notes 
    })
    return response.data
  },
}

// Hooks
export function useAlarms() {
  const queryClient = useQueryClient()

  const {
    data: alarms,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['alarms'],
    queryFn: alarmsApi.getAlarms,
  })

  const createAlarmMutation = useMutation({
    mutationFn: alarmsApi.createAlarm,
    onSuccess: (newAlarm) => {
      queryClient.invalidateQueries({ queryKey: ['alarms'] })
      toast({
        title: 'Alarm Created',
        description: `Alarm "${newAlarm.name}" has been created successfully.`,
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create alarm',
        variant: 'destructive',
      })
    },
  })

  const updateAlarmMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Alarm> }) =>
      alarmsApi.updateAlarm(id, data),
    onSuccess: (updatedAlarm) => {
      queryClient.invalidateQueries({ queryKey: ['alarms'] })
      queryClient.invalidateQueries({ queryKey: ['alarm', updatedAlarm.id] })
      toast({
        title: 'Alarm Updated',
        description: `Alarm "${updatedAlarm.name}" has been updated successfully.`,
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to update alarm',
        variant: 'destructive',
      })
    },
  })

  const deleteAlarmMutation = useMutation({
    mutationFn: alarmsApi.deleteAlarm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alarms'] })
      toast({
        title: 'Alarm Deleted',
        description: 'Alarm has been deleted successfully.',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete alarm',
        variant: 'destructive',
      })
    },
  })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AlarmStatus }) =>
      alarmsApi.toggleAlarmStatus(id, status),
    onSuccess: (updatedAlarm) => {
      queryClient.invalidateQueries({ queryKey: ['alarms'] })
      queryClient.invalidateQueries({ queryKey: ['alarm', updatedAlarm.id] })
      toast({
        title: 'Alarm Status Updated',
        description: `Alarm "${updatedAlarm.name}" is now ${updatedAlarm.status}.`,
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to update alarm status',
        variant: 'destructive',
      })
    },
  })

  const testAlarmMutation = useMutation({
    mutationFn: alarmsApi.testAlarm,
    onSuccess: (result) => {
      toast({
        title: result.success ? 'Test Successful' : 'Test Failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to test alarm',
        variant: 'destructive',
      })
    },
  })

  return {
    alarms,
    isLoading,
    error,
    createAlarm: createAlarmMutation.mutate,
    updateAlarm: (id: string, data: Partial<Alarm>) =>
      updateAlarmMutation.mutate({ id, data }),
    deleteAlarm: deleteAlarmMutation.mutate,
    toggleAlarmStatus: (id: string, status: AlarmStatus) =>
      toggleStatusMutation.mutate({ id, status }),
    testAlarm: testAlarmMutation.mutate,
    isCreating: createAlarmMutation.isPending,
    isUpdating: updateAlarmMutation.isPending,
    isDeleting: deleteAlarmMutation.isPending,
    isToggling: toggleStatusMutation.isPending,
    isTesting: testAlarmMutation.isPending,
  }
}

export function useAlarm(id: string) {
  return useQuery({
    queryKey: ['alarm', id],
    queryFn: () => alarmsApi.getAlarm(id),
    enabled: !!id,
  })
}

export function useAlarmEvents(alarmId?: string, page = 1, limit = 20) {
  const queryClient = useQueryClient()

  const {
    data: eventsResponse,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['alarm-events', alarmId, page, limit],
    queryFn: () => alarmsApi.getAlarmEvents(alarmId, page, limit),
  })

  const acknowledgeEventMutation = useMutation({
    mutationFn: ({ eventId, notes }: { eventId: string; notes?: string }) =>
      alarmsApi.acknowledgeAlarmEvent(eventId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alarm-events'] })
      toast({
        title: 'Event Acknowledged',
        description: 'Alarm event has been acknowledged.',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to acknowledge event',
        variant: 'destructive',
      })
    },
  })

  const dismissEventMutation = useMutation({
    mutationFn: ({ eventId, notes }: { eventId: string; notes?: string }) =>
      alarmsApi.dismissAlarmEvent(eventId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alarm-events'] })
      toast({
        title: 'Event Dismissed',
        description: 'Alarm event has been dismissed.',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to dismiss event',
        variant: 'destructive',
      })
    },
  })

  const snoozeEventMutation = useMutation({
    mutationFn: ({ eventId, duration, notes }: { eventId: string; duration: number; notes?: string }) =>
      alarmsApi.snoozeAlarmEvent(eventId, duration, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alarm-events'] })
      toast({
        title: 'Event Snoozed',
        description: 'Alarm event has been snoozed.',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to snooze event',
        variant: 'destructive',
      })
    },
  })

  return {
    events: eventsResponse?.data || [],
    pagination: eventsResponse?.pagination,
    isLoading,
    error,
    acknowledgeEvent: (eventId: string, notes?: string) =>
      acknowledgeEventMutation.mutate({ eventId, notes }),
    dismissEvent: (eventId: string, notes?: string) =>
      dismissEventMutation.mutate({ eventId, notes }),
    snoozeEvent: (eventId: string, duration: number, notes?: string) =>
      snoozeEventMutation.mutate({ eventId, duration, notes }),
    isAcknowledging: acknowledgeEventMutation.isPending,
    isDismissing: dismissEventMutation.isPending,
    isSnoozing: snoozeEventMutation.isPending,
  }
}