"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import { 
  Lightbulb, 
  Target,
  DollarSign,
  Clock,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  Users,
  Calendar,
  Activity,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  BookOpen
} from "lucide-react"
import { formatCurrency, formatDate, cn } from "@/lib/utils"
import { AIInsight, Recommendation } from "@/types/models"
import { useUpdateInsightStatus, useInsightRecommendations } from "@/hooks/use-insights"
import { toast } from "sonner"

interface RecommendationCardProps {
  insight: AIInsight
  onViewDetails?: (insight: AIInsight) => void
  compact?: boolean
}

const effortLevelColors = {
  low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  high: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
}

const effortLevelIcons = {
  low: CheckCircle,
  medium: Clock,
  high: AlertTriangle,
}

const priorityColors = {
  1: "bg-red-100 text-red-800 border-red-200",
  2: "bg-orange-100 text-orange-800 border-orange-200", 
  3: "bg-yellow-100 text-yellow-800 border-yellow-200",
  4: "bg-blue-100 text-blue-800 border-blue-200",
  5: "bg-gray-100 text-gray-800 border-gray-200",
}

export function RecommendationCard({ 
  insight, 
  onViewDetails,
  compact = false 
}: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [selectedRecommendation, setSelectedRecommendation] = useState<string | null>(null)
  
  const updateStatus = useUpdateInsightStatus()
  const { data: recommendationsData } = useInsightRecommendations(insight.id)

  const handleStatusUpdate = async (status: 'acknowledged' | 'dismissed' | 'implemented') => {
    try {
      await updateStatus.mutateAsync({
        insightId: insight.id,
        status,
        notes: status === 'implemented' ? 'Recommendation implemented via dashboard' : undefined,
      })
    } catch (error) {
      toast.error(`Failed to update recommendation status`)
    }
  }

  const handleViewDetails = () => {
    if (onViewDetails) {
      onViewDetails(insight)
    } else {
      setIsExpanded(!isExpanded)
    }
  }

  const getROIColor = (savings: number) => {
    if (savings >= 1000) return "text-green-600"
    if (savings >= 500) return "text-yellow-600"
    return "text-blue-600"
  }

  const calculateROI = (savings: number, effort: string) => {
    const effortMultiplier = { low: 1, medium: 0.7, high: 0.4 }
    return savings * (effortMultiplier[effort as keyof typeof effortMultiplier] || 0.5)
  }

  const topRecommendation = insight.recommendations?.[0] || recommendationsData?.recommendations?.[0]

  return (
    <Card className="transition-all duration-200 hover:shadow-md border-l-4 border-l-green-500">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900">
              {insight.type === 'optimization' ? (
                <Target className="h-5 w-5 text-green-600 dark:text-green-400" />
              ) : (
                <Lightbulb className="h-5 w-5 text-green-600 dark:text-green-400" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="font-semibold text-foreground text-sm">
                  {insight.title}
                </h3>
                <Badge variant="outline" className="bg-green-100 text-green-800 border-green-200 text-xs">
                  {insight.type === 'optimization' ? 'Optimization' : 'Recommendation'}
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
              className={cn(
                "text-xs",
                insight.status === 'new' ? "bg-blue-100 text-blue-800" :
                insight.status === 'acknowledged' ? "bg-yellow-100 text-yellow-800" :
                insight.status === 'implemented' ? "bg-green-100 text-green-800" :
                "bg-gray-100 text-gray-800"
              )}
            >
              {insight.status}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="space-y-4">
          {/* Key Metrics Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Potential Savings */}
            <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <DollarSign className="h-4 w-4 text-green-600 mr-1" />
                <span className={cn("font-bold text-sm", getROIColor(insight.potential_impact?.cost_savings || 0))}>
                  {formatCurrency(insight.potential_impact?.cost_savings || 0)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Potential Savings</p>
            </div>

            {/* Effort Level */}
            {topRecommendation && (
              <div className="text-center p-3 bg-muted/50 rounded-lg">
                <div className="flex items-center justify-center mb-1">
                  {React.createElement(effortLevelIcons[topRecommendation.effort_level], {
                    className: "h-4 w-4 mr-1"
                  })}
                  <Badge 
                    variant="outline" 
                    className={cn("text-xs", effortLevelColors[topRecommendation.effort_level])}
                  >
                    {topRecommendation.effort_level}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">Effort Level</p>
              </div>
            )}

            {/* ROI Score */}
            {topRecommendation && (
              <div className="text-center p-3 bg-primary/5 rounded-lg">
                <div className="flex items-center justify-center mb-1">
                  <TrendingUp className="h-4 w-4 text-primary mr-1" />
                  <span className="font-bold text-sm text-primary">
                    {Math.round(calculateROI(insight.potential_impact?.cost_savings || 0, topRecommendation.effort_level))}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">ROI Score</p>
              </div>
            )}

            {/* Confidence */}
            <div className="text-center p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center justify-center mb-1">
                <Activity className="h-4 w-4 text-muted-foreground mr-1" />
                <span className="font-bold text-sm">
                  {Math.round(insight.confidence_score * 100)}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Confidence</p>
            </div>
          </div>

          {/* Affected Resources */}
          {insight.affected_resources && insight.affected_resources.length > 0 && (
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center text-muted-foreground">
                <Users className="h-4 w-4 mr-1" />
                <span>
                  Affects {insight.affected_resources.length} resource{insight.affected_resources.length !== 1 ? 's' : ''}
                </span>
                {insight.details?.affected_services && (
                  <span className="ml-2">
                    across {insight.details.affected_services.length} service{insight.details.affected_services.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center text-muted-foreground">
                <Calendar className="h-4 w-4 mr-1" />
                {formatDate(insight.created_at)}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between">
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
            
            <div className="flex items-center space-x-2">
              {insight.status === 'new' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleStatusUpdate('acknowledged')}
                  disabled={updateStatus.isPending}
                >
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Acknowledge
                </Button>
              )}
              
              {insight.status !== 'implemented' && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => handleStatusUpdate('implemented')}
                  disabled={updateStatus.isPending}
                >
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Mark Implemented
                </Button>
              )}
            </div>
          </div>

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

              {/* Recommendations List */}
              {recommendationsData?.recommendations && recommendationsData.recommendations.length > 0 && (
                <div>
                  <h4 className="font-medium text-sm text-foreground mb-3">Implementation Steps</h4>
                  <div className="space-y-3">
                    {recommendationsData.recommendations.map((rec, index) => (
                      <div 
                        key={rec.id}
                        className={cn(
                          "p-3 border rounded-lg cursor-pointer transition-colors",
                          selectedRecommendation === rec.id ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50"
                        )}
                        onClick={() => setSelectedRecommendation(selectedRecommendation === rec.id ? null : rec.id)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <Badge 
                              variant="outline" 
                              className={cn("text-xs", priorityColors[rec.priority as keyof typeof priorityColors] || priorityColors[5])}
                            >
                              Priority {rec.priority}
                            </Badge>
                            <Badge 
                              variant="outline" 
                              className={cn("text-xs", effortLevelColors[rec.effort_level])}
                            >
                              {rec.effort_level} effort
                            </Badge>
                          </div>
                          <div className="flex items-center text-green-600 font-medium text-sm">
                            <DollarSign className="h-3 w-3 mr-1" />
                            {formatCurrency(rec.estimated_savings)}
                          </div>
                        </div>
                        
                        <h5 className="font-medium text-sm text-foreground mb-1">{rec.action}</h5>
                        <p className="text-sm text-muted-foreground mb-2">{rec.description}</p>
                        
                        {selectedRecommendation === rec.id && (
                          <div className="space-y-3 pt-3 border-t">
                            {/* Implementation Steps */}
                            {rec.implementation_steps && rec.implementation_steps.length > 0 && (
                              <div>
                                <h6 className="font-medium text-xs text-foreground mb-2">Implementation Steps:</h6>
                                <ol className="list-decimal list-inside space-y-1">
                                  {rec.implementation_steps.map((step, stepIndex) => (
                                    <li key={stepIndex} className="text-xs text-muted-foreground">
                                      {step}
                                    </li>
                                  ))}
                                </ol>
                              </div>
                            )}
                            
                            {/* Risks */}
                            {rec.risks && rec.risks.length > 0 && (
                              <div>
                                <h6 className="font-medium text-xs text-foreground mb-2">Risks:</h6>
                                <ul className="list-disc list-inside space-y-1">
                                  {rec.risks.map((risk, riskIndex) => (
                                    <li key={riskIndex} className="text-xs text-orange-600">
                                      {risk}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            
                            {/* Prerequisites */}
                            {rec.prerequisites && rec.prerequisites.length > 0 && (
                              <div>
                                <h6 className="font-medium text-xs text-foreground mb-2">Prerequisites:</h6>
                                <ul className="list-disc list-inside space-y-1">
                                  {rec.prerequisites.map((prereq, prereqIndex) => (
                                    <li key={prereqIndex} className="text-xs text-muted-foreground">
                                      {prereq}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
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

              {/* Total Potential Savings */}
              {recommendationsData?.total_potential_savings && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-foreground">Total Potential Savings:</span>
                    <div className="flex items-center text-green-600 font-bold">
                      <DollarSign className="h-4 w-4 mr-1" />
                      {formatCurrency(recommendationsData.total_potential_savings)}
                    </div>
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