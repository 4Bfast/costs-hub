"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  AlertTriangle, 
  Lightbulb, 
  TrendingUp, 
  Target,
  Clock,
  DollarSign,
  Eye,
  Check,
  X,
  MoreHorizontal,
  Calendar,
  Activity,
  Info
} from "lucide-react"
import { formatCurrency, formatDate, cn } from "@/lib/utils"
import { AIInsight } from "@/types/models"
import { useUpdateInsightStatus } from "@/hooks/use-insights"
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { toast } from "sonner"

interface InsightCardProps {
  insight: AIInsight
  onViewDetails?: (insight: AIInsight) => void
  compact?: boolean
}

const insightTypeIcons = {
  anomaly: AlertTriangle,
  recommendation: Lightbulb,
  forecast: TrendingUp,
  optimization: Target,
  trend: Activity,
}

const severityColors = {
  low: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900 dark:text-blue-300",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-300",
  high: "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900 dark:text-orange-300",
  critical: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900 dark:text-red-300",
}

const statusColors = {
  new: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  acknowledged: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  dismissed: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300",
  implemented: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  expired: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
}

export function InsightCard({ 
  insight, 
  onViewDetails,
  compact = false 
}: InsightCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const updateStatus = useUpdateInsightStatus()

  const Icon = insightTypeIcons[insight.type]

  const handleStatusUpdate = async (status: 'acknowledged' | 'dismissed' | 'implemented') => {
    try {
      await updateStatus.mutateAsync({
        insightId: insight.id,
        status,
      })
    } catch (error) {
      toast.error(`Failed to update insight status`)
    }
  }

  const handleViewDetails = () => {
    if (onViewDetails) {
      onViewDetails(insight)
    } else {
      setIsExpanded(!isExpanded)
    }
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return "text-green-600"
    if (score >= 0.6) return "text-yellow-600"
    return "text-red-600"
  }

  return (
    <Card className={cn(
      "transition-all duration-200 hover:shadow-md",
      insight.severity === 'critical' && "border-red-200 dark:border-red-800",
      insight.severity === 'high' && "border-orange-200 dark:border-orange-800"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <div className={cn(
              "p-2 rounded-lg",
              insight.severity === 'critical' ? "bg-red-100 dark:bg-red-900" :
              insight.severity === 'high' ? "bg-orange-100 dark:bg-orange-900" :
              insight.severity === 'medium' ? "bg-yellow-100 dark:bg-yellow-900" :
              "bg-blue-100 dark:bg-blue-900"
            )}>
              <Icon className={cn(
                "h-5 w-5",
                insight.severity === 'critical' ? "text-red-600 dark:text-red-400" :
                insight.severity === 'high' ? "text-orange-600 dark:text-orange-400" :
                insight.severity === 'medium' ? "text-yellow-600 dark:text-yellow-400" :
                "text-blue-600 dark:text-blue-400"
              )} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="font-semibold text-foreground text-sm truncate">
                  {insight.title}
                </h3>
                <Badge 
                  variant="outline" 
                  className={cn("text-xs", severityColors[insight.severity])}
                >
                  {insight.severity}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {insight.summary || insight.description}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Badge 
              variant="outline" 
              className={cn("text-xs", statusColors[insight.status])}
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
                <DropdownMenuItem onClick={handleViewDetails}>
                  <Eye className="h-4 w-4 mr-2" />
                  View Details
                </DropdownMenuItem>
                {insight.status === 'new' && (
                  <DropdownMenuItem onClick={() => handleStatusUpdate('acknowledged')}>
                    <Check className="h-4 w-4 mr-2" />
                    Acknowledge
                  </DropdownMenuItem>
                )}
                {insight.status !== 'dismissed' && (
                  <DropdownMenuItem onClick={() => handleStatusUpdate('dismissed')}>
                    <X className="h-4 w-4 mr-2" />
                    Dismiss
                  </DropdownMenuItem>
                )}
                {(insight.type === 'recommendation' || insight.type === 'optimization') && 
                 insight.status !== 'implemented' && (
                  <DropdownMenuItem onClick={() => handleStatusUpdate('implemented')}>
                    <Check className="h-4 w-4 mr-2" />
                    Mark Implemented
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="space-y-3">
          {/* Key Metrics */}
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-muted-foreground">
                <Calendar className="h-4 w-4 mr-1" />
                {formatDate(insight.created_at)}
              </div>
              <div className="flex items-center text-muted-foreground">
                <Activity className={cn("h-4 w-4 mr-1", getConfidenceColor(insight.confidence_score))} />
                {Math.round(insight.confidence_score * 100)}% confidence
              </div>
            </div>
            
            {insight.potential_impact?.cost_savings && (
              <div className="flex items-center text-green-600 font-medium">
                <DollarSign className="h-4 w-4 mr-1" />
                {formatCurrency(insight.potential_impact.cost_savings)} potential savings
              </div>
            )}
          </div>

          {/* Affected Resources Summary */}
          {insight.affected_resources && insight.affected_resources.length > 0 && (
            <div className="text-sm">
              <span className="text-muted-foreground">Affects: </span>
              <span className="font-medium">
                {insight.affected_resources.length} resource{insight.affected_resources.length !== 1 ? 's' : ''}
              </span>
              {insight.details?.affected_services && (
                <span className="text-muted-foreground ml-2">
                  across {insight.details.affected_services.length} service{insight.details.affected_services.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          )}

          {/* Expandable Details */}
          {!compact && (
            <>
              <Separator />
              <div className="flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs"
                >
                  <Info className="h-3 w-3 mr-1" />
                  {isExpanded ? 'Less Details' : 'More Details'}
                </Button>
                
                <div className="flex items-center space-x-2">
                  {insight.status === 'new' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusUpdate('acknowledged')}
                      disabled={updateStatus.isPending}
                    >
                      <Check className="h-3 w-3 mr-1" />
                      Acknowledge
                    </Button>
                  )}
                  
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleViewDetails}
                  >
                    <Eye className="h-3 w-3 mr-1" />
                    View
                  </Button>
                </div>
              </div>

              {isExpanded && (
                <div className="space-y-3 pt-3 border-t">
                  {/* Full Description */}
                  <div>
                    <h4 className="font-medium text-sm text-foreground mb-2">Description</h4>
                    <p className="text-sm text-muted-foreground">
                      {insight.description}
                    </p>
                  </div>

                  {/* Affected Services */}
                  {insight.details?.affected_services && insight.details.affected_services.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm text-foreground mb-2">Affected Services</h4>
                      <div className="flex flex-wrap gap-1">
                        {insight.details.affected_services.slice(0, 5).map((service, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {service}
                          </Badge>
                        ))}
                        {insight.details.affected_services.length > 5 && (
                          <Badge variant="secondary" className="text-xs">
                            +{insight.details.affected_services.length - 5} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Time Period */}
                  {insight.details?.time_period && (
                    <div>
                      <h4 className="font-medium text-sm text-foreground mb-2">Time Period</h4>
                      <p className="text-sm text-muted-foreground">
                        {formatDate(insight.details.time_period.start)} - {formatDate(insight.details.time_period.end)}
                      </p>
                    </div>
                  )}

                  {/* Cost Impact */}
                  {insight.details?.cost_impact && (
                    <div>
                      <h4 className="font-medium text-sm text-foreground mb-2">Cost Impact</h4>
                      <p className="text-sm font-medium text-foreground">
                        {formatCurrency(insight.details.cost_impact)}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}