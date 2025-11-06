"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import { 
  AlertTriangle, 
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  Calendar,
  BarChart3,
  Eye,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Zap,
  Target,
  Clock,
  AlertCircle
} from "lucide-react"
import { formatCurrency, formatDate, cn } from "@/lib/utils"
import { AIInsight } from "@/types/models"
import { useUpdateInsightStatus, useAnomalyDetails } from "@/hooks/use-insights"
import { AnomalyTimeline } from "./anomaly-timeline"
import { toast } from "sonner"

interface AnomalyCardProps {
  insight: AIInsight
  onViewDetails?: (insight: AIInsight) => void
  compact?: boolean
}

const anomalyTypeIcons = {
  cost_spike: TrendingUp,
  usage_anomaly: Activity,
  billing_anomaly: AlertCircle,
}

const anomalyTypeColors = {
  cost_spike: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900 dark:text-red-300",
  usage_anomaly: "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900 dark:text-orange-300",
  billing_anomaly: "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-300",
}

const severityColors = {
  low: "bg-blue-100 text-blue-800 border-blue-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  critical: "bg-red-100 text-red-800 border-red-200",
}

export function AnomalyCard({ 
  insight, 
  onViewDetails,
  compact = false 
}: AnomalyCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showTimeline, setShowTimeline] = useState(false)
  
  const updateStatus = useUpdateInsightStatus()
  const { data: anomalyData } = useAnomalyDetails(insight.id)

  const handleStatusUpdate = async (status: 'acknowledged' | 'dismissed') => {
    try {
      await updateStatus.mutateAsync({
        insightId: insight.id,
        status,
        notes: status === 'acknowledged' ? 'Anomaly acknowledged via dashboard' : 'Anomaly dismissed as false positive',
      })
    } catch (error) {
      toast.error(`Failed to update anomaly status`)
    }
  }

  const handleViewDetails = () => {
    if (onViewDetails) {
      onViewDetails(insight)
    } else {
      setIsExpanded(!isExpanded)
    }
  }

  const getDeviationColor = (percentage: number) => {
    const abs = Math.abs(percentage)
    if (abs >= 100) return "text-red-600"
    if (abs >= 50) return "text-orange-600"
    if (abs >= 25) return "text-yellow-600"
    return "text-blue-600"
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return "text-green-600"
    if (score >= 0.6) return "text-yellow-600"
    return "text-red-600"
  }

  // Extract anomaly-specific data
  const anomalyType = anomalyData?.anomaly_type || 'cost_spike'
  const detectedCost = anomalyData?.anomaly_data?.detected_cost || insight.details?.cost_impact || 0
  const baselineCost = anomalyData?.baseline_data?.average_cost || 0
  const deviationPercentage = anomalyData?.anomaly_data?.deviation_percentage || 0
  const confidenceScore = anomalyData?.confidence_score || insight.confidence_score

  const Icon = anomalyTypeIcons[anomalyType] || AlertTriangle

  return (
    <Card className="transition-all duration-200 hover:shadow-md border-l-4 border-l-red-500">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900">
              <Icon className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="font-semibold text-foreground text-sm">
                  {insight.title}
                </h3>
                <Badge 
                  variant="outline" 
                  className={cn("text-xs", anomalyTypeColors[anomalyType])}
                >
                  {anomalyType.replace('_', ' ')}
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
              className={cn("text-xs", severityColors[insight.severity])}
            >
              {insight.severity}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="space-y-4">
          {/* Anomaly Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Detected Cost */}
            <div className="text-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <DollarSign className="h-4 w-4 text-red-600 mr-1" />
                <span className="font-bold text-sm text-red-600">
                  {formatCurrency(detectedCost)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Detected Cost</p>
            </div>

            {/* Baseline Cost */}
            <div className="text-center p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <BarChart3 className="h-4 w-4 text-muted-foreground mr-1" />
                <span className="font-bold text-sm">
                  {formatCurrency(baselineCost)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Baseline</p>
            </div>

            {/* Deviation */}
            <div className="text-center p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                {deviationPercentage > 0 ? (
                  <TrendingUp className="h-4 w-4 text-orange-600 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-green-600 mr-1" />
                )}
                <span className={cn("font-bold text-sm", getDeviationColor(deviationPercentage))}>
                  {deviationPercentage > 0 ? '+' : ''}{Math.round(deviationPercentage)}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Deviation</p>
            </div>

            {/* Confidence */}
            <div className="text-center p-3 bg-primary/5 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <Target className="h-4 w-4 text-primary mr-1" />
                <span className={cn("font-bold text-sm", getConfidenceColor(confidenceScore))}>
                  {Math.round(confidenceScore * 100)}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Confidence</p>
            </div>
          </div>

          {/* Deviation Progress Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Deviation from baseline</span>
              <span className={cn("font-medium", getDeviationColor(deviationPercentage))}>
                {Math.abs(deviationPercentage)}% {deviationPercentage > 0 ? 'increase' : 'decrease'}
              </span>
            </div>
            <Progress 
              value={Math.min(Math.abs(deviationPercentage), 100)} 
              className={cn(
                "h-2",
                Math.abs(deviationPercentage) >= 100 ? "bg-red-100" :
                Math.abs(deviationPercentage) >= 50 ? "bg-orange-100" :
                "bg-yellow-100"
              )}
            />
          </div>

          {/* Time Period and Detection Info */}
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-muted-foreground">
                <Calendar className="h-4 w-4 mr-1" />
                {insight.details?.time_period ? (
                  <span>
                    {formatDate(insight.details.time_period.start)} - {formatDate(insight.details.time_period.end)}
                  </span>
                ) : (
                  formatDate(insight.created_at)
                )}
              </div>
              {anomalyData?.detection_method && (
                <div className="flex items-center text-muted-foreground">
                  <Zap className="h-4 w-4 mr-1" />
                  <span className="capitalize">{anomalyData.detection_method}</span>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs"
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="h-3 w-3 mr-1" />
                    Less Details
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3 mr-1" />
                    More Details
                  </>
                )}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowTimeline(!showTimeline)}
                className="text-xs"
              >
                <BarChart3 className="h-3 w-3 mr-1" />
                Timeline
              </Button>
            </div>
            
            <div className="flex items-center space-x-2">
              {insight.status === 'new' && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleStatusUpdate('dismissed')}
                    disabled={updateStatus.isPending}
                  >
                    <X className="h-3 w-3 mr-1" />
                    False Positive
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleStatusUpdate('acknowledged')}
                    disabled={updateStatus.isPending}
                  >
                    <Check className="h-3 w-3 mr-1" />
                    Acknowledge
                  </Button>
                </>
              )}
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleViewDetails}
              >
                <Eye className="h-3 w-3 mr-1" />
                Details
              </Button>
            </div>
          </div>

          {/* Timeline Visualization */}
          {showTimeline && (
            <div className="pt-4 border-t">
              <AnomalyTimeline 
                insight={insight}
                anomalyData={anomalyData}
              />
            </div>
          )}

          {/* Expandable Details */}
          {isExpanded && (
            <div className="space-y-4 pt-4 border-t">
              {/* Full Description */}
              <div>
                <h4 className="font-medium text-sm text-foreground mb-2">Description</h4>
                <p className="text-sm text-muted-foreground">
                  {insight.description}
                </p>
              </div>

              {/* Baseline Data */}
              {anomalyData?.baseline_data && (
                <div>
                  <h4 className="font-medium text-sm text-foreground mb-2">Baseline Analysis</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <div className="p-2 bg-muted/50 rounded">
                      <p className="text-xs text-muted-foreground">Average Cost</p>
                      <p className="font-medium text-sm">{formatCurrency(anomalyData.baseline_data.average_cost)}</p>
                    </div>
                    <div className="p-2 bg-muted/50 rounded">
                      <p className="text-xs text-muted-foreground">Std Deviation</p>
                      <p className="font-medium text-sm">{formatCurrency(anomalyData.baseline_data.standard_deviation)}</p>
                    </div>
                    <div className="p-2 bg-muted/50 rounded">
                      <p className="text-xs text-muted-foreground">Historical Range</p>
                      <p className="font-medium text-sm">
                        {formatCurrency(anomalyData.baseline_data.historical_range.min)} - {formatCurrency(anomalyData.baseline_data.historical_range.max)}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Contributing Factors */}
              {anomalyData?.contributing_factors && anomalyData.contributing_factors.length > 0 && (
                <div>
                  <h4 className="font-medium text-sm text-foreground mb-2">Contributing Factors</h4>
                  <div className="space-y-2">
                    {anomalyData.contributing_factors.map((factor, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                        <div>
                          <p className="font-medium text-sm">{factor.factor}</p>
                          <p className="text-xs text-muted-foreground">{factor.description}</p>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {factor.impact_percentage}% impact
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Similar Incidents */}
              {anomalyData?.similar_incidents && anomalyData.similar_incidents.length > 0 && (
                <div>
                  <h4 className="font-medium text-sm text-foreground mb-2">Similar Past Incidents</h4>
                  <div className="space-y-2">
                    {anomalyData.similar_incidents.slice(0, 3).map((incident, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
                        <div>
                          <p className="font-medium text-sm">{formatDate(incident.date)}</p>
                          <p className="text-xs text-muted-foreground">{incident.resolution}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-sm">{formatCurrency(incident.cost_impact)}</p>
                          <p className="text-xs text-muted-foreground">cost impact</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Affected Services */}
              {insight.details?.affected_services && insight.details.affected_services.length > 0 && (
                <div>
                  <h4 className="font-medium text-sm text-foreground mb-2">Affected Services</h4>
                  <div className="flex flex-wrap gap-1">
                    {insight.details.affected_services.map((service, index) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        {service}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}