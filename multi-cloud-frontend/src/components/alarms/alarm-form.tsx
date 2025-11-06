'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { X, Plus } from 'lucide-react'
import { Alarm, AlarmType, CloudProvider } from '@/types/models'
import { useProviderAccounts } from '@/hooks/useProviderAccounts'

const alarmSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().optional(),
  type: z.enum(['threshold', 'anomaly', 'budget', 'forecast', 'efficiency']),
  threshold: z.number().min(0, 'Threshold must be positive').optional(),
  comparison: z.enum(['greater_than', 'less_than', 'equal_to', 'not_equal_to']),
  period: z.enum(['hourly', 'daily', 'weekly', 'monthly']),
  evaluation_frequency: z.number().min(5, 'Minimum 5 minutes').max(1440, 'Maximum 24 hours'),
  datapoints_to_alarm: z.number().min(1, 'Minimum 1 datapoint').max(10, 'Maximum 10 datapoints'),
  missing_data_treatment: z.enum(['breaching', 'not_breaching', 'ignore']),
  providers: z.array(z.enum(['aws', 'gcp', 'azure'])).optional(),
  services: z.array(z.string()).optional(),
  accounts: z.array(z.string()).optional(),
  regions: z.array(z.string()).optional(),
  email_notifications: z.boolean().default(true),
  webhook_url: z.string().url('Invalid webhook URL').optional().or(z.literal('')),
  notification_channels: z.array(z.string()).optional(),
  anomaly_sensitivity: z.enum(['low', 'medium', 'high']).optional(),
  exclude_weekends: z.boolean().default(false),
  exclude_holidays: z.boolean().default(false),
  budget_amount: z.number().min(0, 'Budget must be positive').optional(),
  budget_period: z.enum(['monthly', 'quarterly', 'yearly']).optional(),
  alert_thresholds: z.array(z.number()).optional(),
})

type AlarmFormData = z.infer<typeof alarmSchema>

interface AlarmFormProps {
  alarm?: Alarm
  onSubmit: (data: Partial<Alarm>) => void
  onCancel: () => void
}

const alarmTypes = [
  { value: 'threshold', label: 'Threshold', description: 'Alert when costs exceed a specific amount' },
  { value: 'anomaly', label: 'Anomaly', description: 'Alert when unusual spending patterns are detected' },
  { value: 'budget', label: 'Budget', description: 'Alert when budget thresholds are reached' },
  { value: 'forecast', label: 'Forecast', description: 'Alert based on projected spending' },
  { value: 'efficiency', label: 'Efficiency', description: 'Alert on resource efficiency opportunities' },
]

const comparisonOptions = [
  { value: 'greater_than', label: 'Greater than' },
  { value: 'less_than', label: 'Less than' },
  { value: 'equal_to', label: 'Equal to' },
  { value: 'not_equal_to', label: 'Not equal to' },
]

const periodOptions = [
  { value: 'hourly', label: 'Hourly' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
]

const missingDataOptions = [
  { value: 'breaching', label: 'Treat as breaching' },
  { value: 'not_breaching', label: 'Treat as not breaching' },
  { value: 'ignore', label: 'Ignore missing data' },
]

const sensitivityOptions = [
  { value: 'low', label: 'Low', description: 'Less sensitive, fewer false positives' },
  { value: 'medium', label: 'Medium', description: 'Balanced sensitivity' },
  { value: 'high', label: 'High', description: 'More sensitive, may have false positives' },
]

const budgetPeriodOptions = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'yearly', label: 'Yearly' },
]

export function AlarmForm({ alarm, onSubmit, onCancel }: AlarmFormProps) {
  const [selectedServices, setSelectedServices] = useState<string[]>([])
  const [selectedRegions, setSelectedRegions] = useState<string[]>([])
  const [newService, setNewService] = useState('')
  const [newRegion, setNewRegion] = useState('')
  const [budgetThresholds, setBudgetThresholds] = useState<number[]>([50, 80, 100])

  const { accounts } = useProviderAccounts()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<AlarmFormData>({
    resolver: zodResolver(alarmSchema),
    defaultValues: {
      name: '',
      description: '',
      type: 'threshold',
      comparison: 'greater_than',
      period: 'daily',
      evaluation_frequency: 60,
      datapoints_to_alarm: 1,
      missing_data_treatment: 'not_breaching',
      email_notifications: true,
      webhook_url: '',
      anomaly_sensitivity: 'medium',
      exclude_weekends: false,
      exclude_holidays: false,
      budget_period: 'monthly',
    },
  })

  const watchedType = watch('type')
  const watchedProviders = watch('providers') || []
  const watchedAccounts = watch('accounts') || []

  useEffect(() => {
    if (alarm) {
      reset({
        name: alarm.name,
        description: alarm.description || '',
        type: alarm.type,
        threshold: alarm.configuration.threshold,
        comparison: alarm.configuration.comparison,
        period: alarm.configuration.period,
        evaluation_frequency: alarm.configuration.evaluation_frequency,
        datapoints_to_alarm: alarm.configuration.datapoints_to_alarm,
        missing_data_treatment: alarm.configuration.missing_data_treatment,
        providers: alarm.configuration.providers,
        accounts: alarm.configuration.accounts,
        email_notifications: alarm.notification_settings.email,
        webhook_url: alarm.notification_settings.webhook || '',
        notification_channels: alarm.notification_settings.channels,
        anomaly_sensitivity: alarm.configuration.anomaly_detection?.sensitivity,
        exclude_weekends: alarm.configuration.anomaly_detection?.exclude_weekends || false,
        exclude_holidays: alarm.configuration.anomaly_detection?.exclude_holidays || false,
        budget_amount: alarm.configuration.budget_settings?.budget_amount,
        budget_period: alarm.configuration.budget_settings?.budget_period,
      })
      
      setSelectedServices(alarm.configuration.services || [])
      setSelectedRegions(alarm.configuration.regions || [])
      setBudgetThresholds(alarm.configuration.budget_settings?.alert_thresholds || [50, 80, 100])
    }
  }, [alarm, reset])

  const handleFormSubmit = (data: AlarmFormData) => {
    const alarmData: Partial<Alarm> = {
      name: data.name,
      description: data.description,
      type: data.type,
      status: 'active',
      configuration: {
        threshold: data.threshold,
        comparison: data.comparison,
        period: data.period,
        evaluation_frequency: data.evaluation_frequency,
        datapoints_to_alarm: data.datapoints_to_alarm,
        missing_data_treatment: data.missing_data_treatment,
        providers: data.providers,
        services: selectedServices,
        accounts: data.accounts,
        regions: selectedRegions,
        ...(data.type === 'anomaly' && {
          anomaly_detection: {
            sensitivity: data.anomaly_sensitivity!,
            exclude_weekends: data.exclude_weekends,
            exclude_holidays: data.exclude_holidays,
          },
        }),
        ...(data.type === 'budget' && {
          budget_settings: {
            budget_amount: data.budget_amount!,
            budget_period: data.budget_period!,
            alert_thresholds: budgetThresholds,
          },
        }),
      },
      notification_settings: {
        email: data.email_notifications,
        webhook: data.webhook_url || undefined,
        channels: data.notification_channels || [],
      },
    }

    onSubmit(alarmData)
  }

  const addService = () => {
    if (newService && !selectedServices.includes(newService)) {
      setSelectedServices([...selectedServices, newService])
      setNewService('')
    }
  }

  const removeService = (service: string) => {
    setSelectedServices(selectedServices.filter(s => s !== service))
  }

  const addRegion = () => {
    if (newRegion && !selectedRegions.includes(newRegion)) {
      setSelectedRegions([...selectedRegions, newRegion])
      setNewRegion('')
    }
  }

  const removeRegion = (region: string) => {
    setSelectedRegions(selectedRegions.filter(r => r !== region))
  }

  const addBudgetThreshold = () => {
    setBudgetThresholds([...budgetThresholds, 0])
  }

  const updateBudgetThreshold = (index: number, value: number) => {
    const newThresholds = [...budgetThresholds]
    newThresholds[index] = value
    setBudgetThresholds(newThresholds)
  }

  const removeBudgetThreshold = (index: number) => {
    setBudgetThresholds(budgetThresholds.filter((_, i) => i !== index))
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Basic Information */}
      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Alarm Name *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder="Enter alarm name"
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Optional description for this alarm"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="type">Alarm Type *</Label>
            <Select value={watchedType} onValueChange={(value) => setValue('type', value as AlarmType)}>
              <SelectTrigger>
                <SelectValue placeholder="Select alarm type" />
              </SelectTrigger>
              <SelectContent>
                {alarmTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-sm text-gray-500">{type.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Threshold Configuration */}
      {(watchedType === 'threshold' || watchedType === 'forecast') && (
        <Card>
          <CardHeader>
            <CardTitle>Threshold Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="threshold">Threshold Amount ($) *</Label>
                <Input
                  id="threshold"
                  type="number"
                  step="0.01"
                  {...register('threshold', { valueAsNumber: true })}
                  placeholder="0.00"
                />
                {errors.threshold && (
                  <p className="text-sm text-red-600">{errors.threshold.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="comparison">Comparison *</Label>
                <Select 
                  value={watch('comparison')} 
                  onValueChange={(value) => setValue('comparison', value as any)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select comparison" />
                  </SelectTrigger>
                  <SelectContent>
                    {comparisonOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Anomaly Detection Configuration */}
      {watchedType === 'anomaly' && (
        <Card>
          <CardHeader>
            <CardTitle>Anomaly Detection Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="sensitivity">Sensitivity Level</Label>
              <Select 
                value={watch('anomaly_sensitivity')} 
                onValueChange={(value) => setValue('anomaly_sensitivity', value as any)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select sensitivity" />
                </SelectTrigger>
                <SelectContent>
                  {sensitivityOptions.map((option) => (
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

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="exclude_weekends"
                  checked={watch('exclude_weekends')}
                  onCheckedChange={(checked) => setValue('exclude_weekends', !!checked)}
                />
                <Label htmlFor="exclude_weekends">Exclude weekends from analysis</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="exclude_holidays"
                  checked={watch('exclude_holidays')}
                  onCheckedChange={(checked) => setValue('exclude_holidays', !!checked)}
                />
                <Label htmlFor="exclude_holidays">Exclude holidays from analysis</Label>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Budget Configuration */}
      {watchedType === 'budget' && (
        <Card>
          <CardHeader>
            <CardTitle>Budget Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="budget_amount">Budget Amount ($) *</Label>
                <Input
                  id="budget_amount"
                  type="number"
                  step="0.01"
                  {...register('budget_amount', { valueAsNumber: true })}
                  placeholder="0.00"
                />
                {errors.budget_amount && (
                  <p className="text-sm text-red-600">{errors.budget_amount.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="budget_period">Budget Period *</Label>
                <Select 
                  value={watch('budget_period')} 
                  onValueChange={(value) => setValue('budget_period', value as any)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select period" />
                  </SelectTrigger>
                  <SelectContent>
                    {budgetPeriodOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Alert Thresholds (%)</Label>
              <div className="space-y-2">
                {budgetThresholds.map((threshold, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <Input
                      type="number"
                      value={threshold}
                      onChange={(e) => updateBudgetThreshold(index, Number(e.target.value))}
                      placeholder="Percentage"
                      className="w-32"
                    />
                    <span className="text-sm text-gray-500">%</span>
                    {budgetThresholds.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeBudgetThreshold(index)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addBudgetThreshold}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Threshold
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Evaluation Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Evaluation Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="period">Evaluation Period *</Label>
              <Select 
                value={watch('period')} 
                onValueChange={(value) => setValue('period', value as any)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select period" />
                </SelectTrigger>
                <SelectContent>
                  {periodOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="evaluation_frequency">Evaluation Frequency (minutes) *</Label>
              <Input
                id="evaluation_frequency"
                type="number"
                {...register('evaluation_frequency', { valueAsNumber: true })}
                placeholder="60"
              />
              {errors.evaluation_frequency && (
                <p className="text-sm text-red-600">{errors.evaluation_frequency.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="datapoints_to_alarm">Datapoints to Alarm *</Label>
              <Input
                id="datapoints_to_alarm"
                type="number"
                {...register('datapoints_to_alarm', { valueAsNumber: true })}
                placeholder="1"
              />
              {errors.datapoints_to_alarm && (
                <p className="text-sm text-red-600">{errors.datapoints_to_alarm.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="missing_data_treatment">Missing Data Treatment *</Label>
              <Select 
                value={watch('missing_data_treatment')} 
                onValueChange={(value) => setValue('missing_data_treatment', value as any)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select treatment" />
                </SelectTrigger>
                <SelectContent>
                  {missingDataOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Scope Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Scope Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Cloud Providers</Label>
            <div className="flex flex-wrap gap-2">
              {(['aws', 'gcp', 'azure'] as CloudProvider[]).map((provider) => (
                <div key={provider} className="flex items-center space-x-2">
                  <Checkbox
                    id={`provider-${provider}`}
                    checked={watchedProviders.includes(provider)}
                    onCheckedChange={(checked) => {
                      const current = watchedProviders
                      if (checked) {
                        setValue('providers', [...current, provider])
                      } else {
                        setValue('providers', current.filter(p => p !== provider))
                      }
                    }}
                  />
                  <Label htmlFor={`provider-${provider}`} className="capitalize">
                    {provider}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Accounts</Label>
            <div className="space-y-2">
              {accounts?.map((account) => (
                <div key={account.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`account-${account.id}`}
                    checked={watchedAccounts.includes(account.account_id)}
                    onCheckedChange={(checked) => {
                      const current = watchedAccounts
                      if (checked) {
                        setValue('accounts', [...current, account.account_id])
                      } else {
                        setValue('accounts', current.filter(a => a !== account.account_id))
                      }
                    }}
                  />
                  <Label htmlFor={`account-${account.id}`}>
                    {account.display_name || account.account_name} ({account.provider})
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Services</Label>
            <div className="flex items-center space-x-2 mb-2">
              <Input
                value={newService}
                onChange={(e) => setNewService(e.target.value)}
                placeholder="Add service name"
                className="flex-1"
              />
              <Button type="button" onClick={addService} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedServices.map((service) => (
                <Badge key={service} variant="secondary" className="flex items-center gap-1">
                  {service}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0"
                    onClick={() => removeService(service)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Regions</Label>
            <div className="flex items-center space-x-2 mb-2">
              <Input
                value={newRegion}
                onChange={(e) => setNewRegion(e.target.value)}
                placeholder="Add region name"
                className="flex-1"
              />
              <Button type="button" onClick={addRegion} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedRegions.map((region) => (
                <Badge key={region} variant="secondary" className="flex items-center gap-1">
                  {region}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0"
                    onClick={() => removeRegion(region)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="email_notifications"
              checked={watch('email_notifications')}
              onCheckedChange={(checked) => setValue('email_notifications', !!checked)}
            />
            <Label htmlFor="email_notifications">Enable email notifications</Label>
          </div>

          <div className="space-y-2">
            <Label htmlFor="webhook_url">Webhook URL (optional)</Label>
            <Input
              id="webhook_url"
              type="url"
              {...register('webhook_url')}
              placeholder="https://your-webhook-url.com"
            />
            {errors.webhook_url && (
              <p className="text-sm text-red-600">{errors.webhook_url.message}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Form Actions */}
      <div className="flex justify-end space-x-3">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving...' : alarm ? 'Update Alarm' : 'Create Alarm'}
        </Button>
      </div>
    </form>
  )
}