"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Brain, 
  Search, 
  Filter, 
  RefreshCw, 
  Download,
  AlertTriangle,
  Lightbulb,
  TrendingUp,
  Target,
  BarChart3,
  Settings
} from "lucide-react"
import { useInsights, useInsightsSummary, useGenerateInsights } from "@/hooks/use-insights"
import { cn } from "@/lib/utils"
import { InsightCard } from "@/components/insights/insight-card"
import { RecommendationCard } from "@/components/insights/recommendation-card"
import { AnomalyCard } from "@/components/insights/anomaly-card"
import { InsightFilters } from "@/components/insights/insight-filters"
import { InsightsSummaryStats } from "@/components/insights/insights-summary-stats"
import { InsightsManagement } from "@/components/insights/insights-management"
import { PageHeader } from "@/components/layout/page-header"
import { EmptyState } from "@/components/layout/empty-state"

const insightTypeOptions = [
  { value: 'anomaly', label: 'Anomalies', icon: AlertTriangle },
  { value: 'recommendation', label: 'Recommendations', icon: Lightbulb },
  { value: 'forecast', label: 'Forecasts', icon: TrendingUp },
  { value: 'optimization', label: 'Optimizations', icon: Target },
]

export default function InsightsPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [activeTab, setActiveTab] = useState("all")
  const [filters, setFilters] = useState({
    type: undefined as string[] | undefined,
    severity: undefined as string[] | undefined,
    status: undefined as string[] | undefined,
    date_range: undefined as { start: string; end: string } | undefined,
  })
  const [showFilters, setShowFilters] = useState(false)
  const [selectedInsights, setSelectedInsights] = useState<string[]>([])
  const [showManagement, setShowManagement] = useState(false)

  // Query parameters for insights
  const queryParams = {
    search: searchTerm,
    filters: {
      ...filters,
      ...(activeTab !== 'all' && { type: [activeTab] }),
    },
    page: 1,
    limit: 20,
    sort: 'created_at',
    order: 'desc' as const,
  }

  const { data: insights, isLoading: insightsLoading, refetch: refetchInsights } = useInsights(queryParams)
  const { data: summary, isLoading: summaryLoading } = useInsightsSummary()
  const generateInsights = useGenerateInsights()

  const handleGenerateInsights = () => {
    generateInsights.mutate({
      insight_types: ['anomaly', 'recommendation', 'optimization', 'forecast'],
    })
  }

  const handleFilterChange = (newFilters: {
    type?: string[]
    severity?: string[]
    status?: string[]
    date_range?: { start: string; end: string }
  }) => {
    setFilters({
      type: newFilters.type,
      severity: newFilters.severity,
      status: newFilters.status,
      date_range: newFilters.date_range,
    })
  }

  const handleSearch = (value: string) => {
    setSearchTerm(value)
  }

  const renderInsightCard = (insight: any) => {
    switch (insight.type) {
      case 'anomaly':
        return <AnomalyCard key={insight.id} insight={insight} />
      case 'recommendation':
      case 'optimization':
        return <RecommendationCard key={insight.id} insight={insight} />
      default:
        return <InsightCard key={insight.id} insight={insight} />
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Insights"
        description="AI-powered cost analysis, anomaly detection, and optimization recommendations"
        icon={Brain}
        actions={
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowManagement(!showManagement)}
            >
              <Settings className="h-4 w-4 mr-2" />
              Manage
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchInsights()}
              disabled={insightsLoading}
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", insightsLoading && "animate-spin")} />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={handleGenerateInsights}
              disabled={generateInsights.isPending}
            >
              <Brain className="h-4 w-4 mr-2" />
              Generate Insights
            </Button>
          </div>
        }
      />

      {/* Summary Statistics */}
      <InsightsSummaryStats data={summary} loading={summaryLoading} />

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <InsightFilters
              filters={filters}
              onChange={handleFilterChange}
            />
          </CardContent>
        </Card>
      )}

      {/* Management Panel */}
      {showManagement && insights?.data && (
        <InsightsManagement
          insights={insights.data}
          selectedInsights={selectedInsights}
          onSelectionChange={setSelectedInsights}
          onRefresh={() => refetchInsights()}
        />
      )}

      {/* Search and Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between space-x-4">
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search insights..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Insights Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="all" className="flex items-center space-x-2">
            <BarChart3 className="h-4 w-4" />
            <span>All Insights</span>
          </TabsTrigger>
          {insightTypeOptions.map((type) => {
            const Icon = type.icon
            return (
              <TabsTrigger key={type.value} value={type.value} className="flex items-center space-x-2">
                <Icon className="h-4 w-4" />
                <span>{type.label}</span>
              </TabsTrigger>
            )
          })}
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {insightsLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-6">
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <Skeleton className="h-5 w-48" />
                        <Skeleton className="h-6 w-16" />
                      </div>
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-3/4" />
                      <div className="flex items-center justify-between">
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="h-4 w-20" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : !insights?.data || insights.data.length === 0 ? (
            <EmptyState
              icon={Brain}
              title="No insights available"
              description="AI insights will appear here once your cost data is analyzed. Try generating new insights or adjusting your filters."
              action={
                <Button onClick={handleGenerateInsights} disabled={generateInsights.isPending}>
                  <Brain className="h-4 w-4 mr-2" />
                  Generate Insights
                </Button>
              }
            />
          ) : (
            <div className="space-y-4">
              {insights.data.map(renderInsightCard)}
              
              {/* Pagination */}
              {insights.pagination && insights.pagination.totalPages > 1 && (
                <div className="flex items-center justify-center space-x-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!insights.pagination.hasPrev}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {insights.pagination.page} of {insights.pagination.totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!insights.pagination.hasNext}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {insightTypeOptions.map((type) => (
          <TabsContent key={type.value} value={type.value} className="space-y-4">
            {insightsLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Card key={i}>
                    <CardContent className="p-6">
                      <div className="space-y-3">
                        <div className="flex items-start justify-between">
                          <Skeleton className="h-5 w-48" />
                          <Skeleton className="h-6 w-16" />
                        </div>
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-3/4" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : !insights?.data || insights.data.length === 0 ? (
              <EmptyState
                icon={type.icon}
                title={`No ${type.label.toLowerCase()} available`}
                description={`${type.label} will appear here once your cost data is analyzed.`}
                action={
                  <Button onClick={handleGenerateInsights} disabled={generateInsights.isPending}>
                    <Brain className="h-4 w-4 mr-2" />
                    Generate Insights
                  </Button>
                }
              />
            ) : (
              <div className="space-y-4">
                {insights.data.map(renderInsightCard)}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}