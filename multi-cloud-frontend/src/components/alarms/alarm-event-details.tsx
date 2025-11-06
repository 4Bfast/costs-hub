'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { 
  Clock, 
  DollarSign, 
  TrendingUp, 
  AlertTriangle,
  CheckCircle,
  User,
  MessageSquare
} from 'lucide-react'
import { AlarmEvent } from '@/types/models'
import { formatCurrency, formatDate } from '@/lib/data-utils'
import { CostLineChart } from '@/components/charts/cost-line-chart'

interface AlarmEventDetailsProps {
  event: AlarmEvent
  onClose: () => void
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

export function AlarmEventDetails({ event }: AlarmEventDetailsProps) {
  const exceedsThreshold = event.current_value > event.threshold_value
  const percentageChange = ((event.current_value - event.threshold_value) / event.threshold_value) * 100

  return (
    <div className="space-y-6">
      {/* Event Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Event Overview
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm font-medium text-gray-500">Status</div>
              <Badge variant="secondary" className={statusColors[event.status]}>
                {event.status}
              </Badge>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Severity</div>
              <Badge variant="secondary" className={severityColors[event.severity]}>
                {event.severity}
              </Badge>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Triggered At</div>
              <div className="font-medium">{formatDate(event.triggered_at)}</div>
            </div>
            {event.resolved_at && (
              <div>
                <div className="text-sm font-medium text-gray-500">Resolved At</div>
                <div className="font-medium">{formatDate(event.resolved_at)}</div>
              </div>
            )}
          </div>

          <Separator />

          <div>
            <div className="text-sm font-medium text-gray-500 mb-2">Message</div>
            <p className="text-gray-900">{event.message}</p>
          </div>
        </CardContent>
      </Card>

      {/* Cost Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Cost Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {formatCurrency(event.current_value)}
              </div>
              <div className="text-sm text-gray-500">Current Value</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {formatCurrency(event.threshold_value)}
              </div>
              <div className="text-sm text-gray-500">Threshold</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${exceedsThreshold ? 'text-red-600' : 'text-green-600'}`}>
                {exceedsThreshold ? '+' : ''}{percentageChange.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">
                {exceedsThreshold ? 'Over Threshold' : 'Under Threshold'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cost Breakdown */}
      {event.details.cost_breakdown && event.details.cost_breakdown.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Cost Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {event.details.cost_breakdown.map((item, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <div className="font-medium">{item.service}</div>
                    <div className="text-sm text-gray-500">{item.account_id}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">{formatCurrency(item.cost)}</div>
                    <div className="text-sm text-gray-500">{item.percentage.toFixed(1)}%</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trend Visualization */}
      {event.details.trend_data && event.details.trend_data.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Cost Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <CostLineChart 
                data={event.details.trend_data}
                height={240}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Affected Resources */}
      {event.details.affected_accounts && event.details.affected_accounts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Affected Resources</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {event.details.affected_accounts && (
                <div>
                  <div className="text-sm font-medium text-gray-500 mb-2">Accounts</div>
                  <div className="flex flex-wrap gap-2">
                    {event.details.affected_accounts.map((account) => (
                      <Badge key={account} variant="outline">
                        {account}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              
              {event.details.affected_services && (
                <div>
                  <div className="text-sm font-medium text-gray-500 mb-2">Services</div>
                  <div className="flex flex-wrap gap-2">
                    {event.details.affected_services.map((service) => (
                      <Badge key={service} variant="outline">
                        {service}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Contributing Factors */}
      {event.details.contributing_factors && event.details.contributing_factors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Contributing Factors</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {event.details.contributing_factors.map((factor, index) => (
                <li key={index} className="flex items-start gap-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0" />
                  <span className="text-gray-700">{factor}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Recommended Actions */}
      {event.details.recommended_actions && event.details.recommended_actions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recommended Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {event.details.recommended_actions.map((action, index) => (
                <li key={index} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700">{action}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Acknowledgment Information */}
      {event.acknowledged_at && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Acknowledgment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-medium text-gray-500">Acknowledged At</div>
                <div className="font-medium">{formatDate(event.acknowledged_at)}</div>
              </div>
              {event.acknowledged_by && (
                <div>
                  <div className="text-sm font-medium text-gray-500">Acknowledged By</div>
                  <div className="font-medium">{event.acknowledged_by}</div>
                </div>
              )}
            </div>
            
            {event.notes && (
              <div>
                <div className="text-sm font-medium text-gray-500 mb-2 flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Notes
                </div>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-gray-700">{event.notes}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Event Timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-red-500 rounded-full mt-2" />
              <div>
                <div className="font-medium">Event Triggered</div>
                <div className="text-sm text-gray-500">{formatDate(event.triggered_at)}</div>
              </div>
            </div>
            
            {event.acknowledged_at && (
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2" />
                <div>
                  <div className="font-medium">Event Acknowledged</div>
                  <div className="text-sm text-gray-500">{formatDate(event.acknowledged_at)}</div>
                  {event.acknowledged_by && (
                    <div className="text-sm text-gray-500">by {event.acknowledged_by}</div>
                  )}
                </div>
              </div>
            )}
            
            {event.resolved_at && (
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 bg-green-500 rounded-full mt-2" />
                <div>
                  <div className="font-medium">Event Resolved</div>
                  <div className="text-sm text-gray-500">{formatDate(event.resolved_at)}</div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}