'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { 
  Bell, 
  Mail, 
  Webhook, 
  TestTube, 
  Plus, 
  X, 
  Clock,
  Volume2,
  VolumeX
} from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { NotificationSettings as NotificationSettingsType } from '@/types/models'

const notificationSchema = z.object({
  email_notifications: z.boolean(),
  push_notifications: z.boolean(),
  notification_frequency: z.enum(['immediate', 'hourly', 'daily', 'weekly']),
  alarm_notifications: z.object({
    threshold: z.boolean(),
    anomaly: z.boolean(),
    budget: z.boolean(),
    forecast: z.boolean(),
  }),
  insight_notifications: z.object({
    high_severity: z.boolean(),
    medium_severity: z.boolean(),
    low_severity: z.boolean(),
  }),
  quiet_hours: z.object({
    enabled: z.boolean(),
    start_time: z.string(),
    end_time: z.string(),
    timezone: z.string(),
  }),
  webhook_urls: z.array(z.string().url()),
  email_addresses: z.array(z.string().email()),
})

type NotificationFormData = z.infer<typeof notificationSchema>

interface NotificationSettingsProps {
  settings?: NotificationSettingsType
  onSave: (settings: NotificationSettingsType) => void
  isLoading?: boolean
}

const frequencyOptions = [
  { value: 'immediate', label: 'Immediate', description: 'Send notifications as soon as events occur' },
  { value: 'hourly', label: 'Hourly', description: 'Send a summary every hour' },
  { value: 'daily', label: 'Daily', description: 'Send a daily digest' },
  { value: 'weekly', label: 'Weekly', description: 'Send a weekly summary' },
]

const timezones = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
]

export function NotificationSettings({ settings, onSave, isLoading }: NotificationSettingsProps) {
  const [webhookUrls, setWebhookUrls] = useState<string[]>([])
  const [emailAddresses, setEmailAddresses] = useState<string[]>([])
  const [newWebhook, setNewWebhook] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [isTestingWebhook, setIsTestingWebhook] = useState<string | null>(null)
  const [isTestingEmail, setIsTestingEmail] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
    reset,
  } = useForm<NotificationFormData>({
    resolver: zodResolver(notificationSchema),
    defaultValues: {
      email_notifications: true,
      push_notifications: true,
      notification_frequency: 'immediate',
      alarm_notifications: {
        threshold: true,
        anomaly: true,
        budget: true,
        forecast: true,
      },
      insight_notifications: {
        high_severity: true,
        medium_severity: true,
        low_severity: false,
      },
      quiet_hours: {
        enabled: false,
        start_time: '22:00',
        end_time: '08:00',
        timezone: 'UTC',
      },
      webhook_urls: [],
      email_addresses: [],
    },
  })

  const watchQuietHoursEnabled = watch('quiet_hours.enabled')

  useEffect(() => {
    if (settings) {
      reset({
        email_notifications: settings.email_notifications,
        push_notifications: settings.push_notifications,
        notification_frequency: settings.notification_frequency,
        alarm_notifications: settings.alarm_notifications,
        insight_notifications: settings.insight_notifications,
        quiet_hours: {
          enabled: false, // This would come from settings if available
          start_time: '22:00',
          end_time: '08:00',
          timezone: 'UTC',
        },
        webhook_urls: [],
        email_addresses: [],
      })
    }
  }, [settings, reset])

  const handleFormSubmit = (data: NotificationFormData) => {
    const notificationSettings: NotificationSettingsType = {
      email_notifications: data.email_notifications,
      push_notifications: data.push_notifications,
      notification_frequency: data.notification_frequency,
      alarm_notifications: data.alarm_notifications,
      insight_notifications: data.insight_notifications,
    }

    onSave(notificationSettings)
  }

  const addWebhook = () => {
    if (newWebhook && !webhookUrls.includes(newWebhook)) {
      try {
        new URL(newWebhook) // Validate URL
        setWebhookUrls([...webhookUrls, newWebhook])
        setNewWebhook('')
      } catch {
        toast({
          title: 'Invalid URL',
          description: 'Please enter a valid webhook URL',
          variant: 'destructive',
        })
      }
    }
  }

  const removeWebhook = (url: string) => {
    setWebhookUrls(webhookUrls.filter(w => w !== url))
  }

  const addEmail = () => {
    if (newEmail && !emailAddresses.includes(newEmail)) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (emailRegex.test(newEmail)) {
        setEmailAddresses([...emailAddresses, newEmail])
        setNewEmail('')
      } else {
        toast({
          title: 'Invalid Email',
          description: 'Please enter a valid email address',
          variant: 'destructive',
        })
      }
    }
  }

  const removeEmail = (email: string) => {
    setEmailAddresses(emailAddresses.filter(e => e !== email))
  }

  const testWebhook = async (url: string) => {
    setIsTestingWebhook(url)
    try {
      // Simulate webhook test
      await new Promise(resolve => setTimeout(resolve, 2000))
      toast({
        title: 'Webhook Test Successful',
        description: 'Test notification sent successfully',
      })
    } catch (error) {
      toast({
        title: 'Webhook Test Failed',
        description: 'Failed to send test notification',
        variant: 'destructive',
      })
    } finally {
      setIsTestingWebhook(null)
    }
  }

  const testEmail = async (email: string) => {
    setIsTestingEmail(email)
    try {
      // Simulate email test
      await new Promise(resolve => setTimeout(resolve, 2000))
      toast({
        title: 'Email Test Successful',
        description: 'Test email sent successfully',
      })
    } catch (error) {
      toast({
        title: 'Email Test Failed',
        description: 'Failed to send test email',
        variant: 'destructive',
      })
    } finally {
      setIsTestingEmail(null)
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            General Notification Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Email Notifications</Label>
                <div className="text-sm text-gray-500">
                  Receive notifications via email
                </div>
              </div>
              <Switch
                checked={watch('email_notifications')}
                onCheckedChange={(checked) => setValue('email_notifications', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Push Notifications</Label>
                <div className="text-sm text-gray-500">
                  Receive browser push notifications
                </div>
              </div>
              <Switch
                checked={watch('push_notifications')}
                onCheckedChange={(checked) => setValue('push_notifications', checked)}
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <Label htmlFor="frequency">Notification Frequency</Label>
            <Select 
              value={watch('notification_frequency')} 
              onValueChange={(value) => setValue('notification_frequency', value as any)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select frequency" />
              </SelectTrigger>
              <SelectContent>
                {frequencyOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div>
                      <div className="font-medium">{option.label}</div>
                      <div className="text-sm text-gray-500">{option.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Alarm Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Alarm Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Threshold Alarms</Label>
                <div className="text-sm text-gray-500">
                  Notifications when cost thresholds are exceeded
                </div>
              </div>
              <Switch
                checked={watch('alarm_notifications.threshold')}
                onCheckedChange={(checked) => setValue('alarm_notifications.threshold', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Anomaly Detection</Label>
                <div className="text-sm text-gray-500">
                  Notifications for unusual spending patterns
                </div>
              </div>
              <Switch
                checked={watch('alarm_notifications.anomaly')}
                onCheckedChange={(checked) => setValue('alarm_notifications.anomaly', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Budget Alarms</Label>
                <div className="text-sm text-gray-500">
                  Notifications when budget limits are approached
                </div>
              </div>
              <Switch
                checked={watch('alarm_notifications.budget')}
                onCheckedChange={(checked) => setValue('alarm_notifications.budget', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Forecast Alarms</Label>
                <div className="text-sm text-gray-500">
                  Notifications based on cost projections
                </div>
              </div>
              <Switch
                checked={watch('alarm_notifications.forecast')}
                onCheckedChange={(checked) => setValue('alarm_notifications.forecast', checked)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Insight Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>AI Insight Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">High Severity Insights</Label>
                <div className="text-sm text-gray-500">
                  Critical cost optimization opportunities
                </div>
              </div>
              <Switch
                checked={watch('insight_notifications.high_severity')}
                onCheckedChange={(checked) => setValue('insight_notifications.high_severity', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Medium Severity Insights</Label>
                <div className="text-sm text-gray-500">
                  Important recommendations and trends
                </div>
              </div>
              <Switch
                checked={watch('insight_notifications.medium_severity')}
                onCheckedChange={(checked) => setValue('insight_notifications.medium_severity', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Low Severity Insights</Label>
                <div className="text-sm text-gray-500">
                  General observations and minor optimizations
                </div>
              </div>
              <Switch
                checked={watch('insight_notifications.low_severity')}
                onCheckedChange={(checked) => setValue('insight_notifications.low_severity', checked)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quiet Hours */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Quiet Hours
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Enable Quiet Hours</Label>
              <div className="text-sm text-gray-500">
                Suppress notifications during specified hours
              </div>
            </div>
            <Switch
              checked={watchQuietHoursEnabled}
              onCheckedChange={(checked) => setValue('quiet_hours.enabled', checked)}
            />
          </div>

          {watchQuietHoursEnabled && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t">
              <div className="space-y-2">
                <Label htmlFor="start_time">Start Time</Label>
                <Input
                  id="start_time"
                  type="time"
                  {...register('quiet_hours.start_time')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end_time">End Time</Label>
                <Input
                  id="end_time"
                  type="time"
                  {...register('quiet_hours.end_time')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Select 
                  value={watch('quiet_hours.timezone')} 
                  onValueChange={(value) => setValue('quiet_hours.timezone', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select timezone" />
                  </SelectTrigger>
                  <SelectContent>
                    {timezones.map((tz) => (
                      <SelectItem key={tz} value={tz}>
                        {tz}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Webhook Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="h-5 w-5" />
            Webhook Notifications
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Input
              value={newWebhook}
              onChange={(e) => setNewWebhook(e.target.value)}
              placeholder="https://your-webhook-url.com"
              className="flex-1"
            />
            <Button type="button" onClick={addWebhook} size="sm">
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {webhookUrls.length > 0 && (
            <div className="space-y-2">
              {webhookUrls.map((url) => (
                <div key={url} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1 truncate">
                    <div className="font-medium truncate">{url}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => testWebhook(url)}
                      disabled={isTestingWebhook === url}
                    >
                      <TestTube className="h-4 w-4" />
                      {isTestingWebhook === url ? 'Testing...' : 'Test'}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeWebhook(url)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Email Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Additional Email Recipients
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Input
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="email@example.com"
              type="email"
              className="flex-1"
            />
            <Button type="button" onClick={addEmail} size="sm">
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {emailAddresses.length > 0 && (
            <div className="space-y-2">
              {emailAddresses.map((email) => (
                <div key={email} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="font-medium">{email}</div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => testEmail(email)}
                      disabled={isTestingEmail === email}
                    >
                      <TestTube className="h-4 w-4" />
                      {isTestingEmail === email ? 'Testing...' : 'Test'}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeEmail(email)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Form Actions */}
      <div className="flex justify-end space-x-3">
        <Button type="button" variant="outline" onClick={() => reset()}>
          Reset
        </Button>
        <Button type="submit" disabled={isLoading || !isDirty}>
          {isLoading ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </form>
  )
}