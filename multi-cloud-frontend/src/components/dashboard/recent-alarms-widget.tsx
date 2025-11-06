"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  ArrowRight, 
  Bell, 
  AlertTriangle, 
  AlertCircle,
  Info,
  CheckCircle,
  Clock
} from "lucide-react"
import { formatCurrency, formatDate } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface AlarmData {
  id: string
  alarm_name: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  triggered_at: string
  current_value: number
  threshold_value: number
  status: 'new' | 'acknowledged' | 'resolved'
  affected_services: string[]
  cost_impact: number
}

interface RecentAlarmsWidgetProps {
  data?: AlarmData[]
  loading?: boolean
  title?: string
  limit?: number
}

const severityConfig = {
  low: {
    icon: Info,
    color: "text-blue-600",
    bgColor: "bg-blue-100",
    borderColor: "border-blue-200",
    badgeClass: "bg-blue-100 text-blue-800 border-blue-200",
  },
  medium: {
    icon: AlertCircle,
    color: "text-yellow-600",
    bgColor: "bg-yellow-100",
    borderColor: "border-yellow-200",
    badgeClass: "bg-yellow-100 text-yellow-800 border-yellow-200",
  },
  high: {
    icon: AlertTriangle,
    color: "text-orange-600",
    bgColor: "bg-orange-100",
    borderColor: "border-orange-200",
    badgeClass: "bg-orange-100 text-orange-800 border-orange-200",
  },
  critical: {
    icon: AlertTriangle,
    color: "text-red-600",
    bgColor: "bg-red-100",
    borderColor: "border-red-200",
    badgeClass: "bg-red-100 text-red-800 border-red-200",
  },
}

const statusConfig = {
  new: {
    icon: Bell,
    color: "text-red-600",
    label: "New",
    badgeClass: "bg-red-100 text-red-800",
  },
  acknowledged: {
    icon: CheckCircle,
    color: "text-yellow-600",
    label: "Acknowledged",
    badgeClass: "bg-yellow-100 text-yellow-800",
  },
  resolved: {
    icon: CheckCircle,
    color: "text-green-600",
    label: "Resolved",
    badgeClass: "bg-green-100 text-green-800",
  },
}

export function RecentAlarmsWidget({
  data,
  loading = false,
  title = "Recent Cost Alarms",
  limit = 3,
}: RecentAlarmsWidgetProps) {
  const displayData = data?.slice(0, limit) || []

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Bell className="h-5 w-5 text-primary" />
              <CardTitle>{title}</CardTitle>
            </div>
            <Skeleton className="h-9 w-20" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="p-4 border rounded-lg">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                  <Skeleton className="h-5 w-16" />
                </div>
                <Skeleton className="h-3 w-24 mb-2" />
                <div className="flex items-center justify-between">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-4 w-16" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Bell className="h-5 w-5 text-primary" />
            <CardTitle>{title}</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48 text-muted-foreground">
            <div className="text-center">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
              <p>No active alarms</p>
              <p className="text-sm mt-1">All your cost monitoring is within thresholds</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Bell className="h-5 w-5 text-primary" />
            <CardTitle>{title}</CardTitle>
          </div>
          <Button variant="ghost" size="sm">
            View All
            <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {displayData.map((alarm) => {
            const severityInfo = severityConfig[alarm.severity]
            const statusInfo = statusConfig[alarm.status]
            const SeverityIcon = severityInfo.icon
            const StatusIcon = statusInfo.icon
            
            return (
              <div 
                key={alarm.id}
                className={cn(
                  "p-4 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer",
                  severityInfo.borderColor
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <SeverityIcon className={cn("h-4 w-4 flex-shrink-0", severityInfo.color)} />
                    <p className="font-medium text-foreground truncate">
                      {alarm.alarm_name}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <Badge 
                      variant="outline" 
                      className={cn("text-xs", severityInfo.badgeClass)}
                    >
                      {alarm.severity}
                    </Badge>
                    <Badge 
                      variant="outline" 
                      className={cn("text-xs", statusInfo.badgeClass)}
                    >
                      {statusInfo.label}
                    </Badge>
                  </div>
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex items-center text-muted-foreground">
                    <Clock className="h-3 w-3 mr-1" />
                    <span>{formatDate(alarm.triggered_at)}</span>
                  </div>
                  
                  {alarm.affected_services && alarm.affected_services.length > 0 && (
                    <p className="text-muted-foreground">
                      Affected services: {alarm.affected_services.slice(0, 2).join(', ')}
                      {alarm.affected_services.length > 2 && ` +${alarm.affected_services.length - 2} more`}
                    </p>
                  )}
                </div>
                
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                  <div className="text-sm">
                    <span className="text-muted-foreground">Current: </span>
                    <span className="font-medium text-foreground">
                      {formatCurrency(alarm.current_value)}
                    </span>
                    <span className="text-muted-foreground mx-2">|</span>
                    <span className="text-muted-foreground">Threshold: </span>
                    <span className="font-medium text-foreground">
                      {formatCurrency(alarm.threshold_value)}
                    </span>
                  </div>
                  
                  {(alarm.cost_impact && alarm.cost_impact > 0) && (
                    <div className="text-right">
                      <p className="text-sm font-medium text-red-600">
                        +{formatCurrency(alarm.cost_impact)}
                      </p>
                      <p className="text-xs text-muted-foreground">Impact</p>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        
        {data.length > limit && (
          <div className="mt-4 pt-4 border-t">
            <Button variant="outline" className="w-full">
              View All {data.length} Alarms
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}