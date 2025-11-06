"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Download, Filter, RefreshCw } from "lucide-react"
import { FilterPanel } from "@/components/analysis/filter-panel"
import { CostTrendsChart } from "@/components/analysis/cost-trends-chart"
import { CostBreakdownChart } from "@/components/analysis/cost-breakdown-chart"
import { ProviderComparisonChart } from "@/components/analysis/provider-comparison-chart"
import { CostDataTable } from "@/components/analysis/cost-data-table"
import { ExportDialog } from "@/components/analysis/export-dialog"
import { useCostAnalysis } from "@/hooks/use-cost-analysis"
import { CostFilters } from "@/types/models"
import { LoadingState } from "@/components/ui/loading-state"
import { ErrorState } from "@/components/ui/error-state"
import { EmptyState } from "@/components/ui/empty-state"

export default function AnalysisPage() {
  const [filters, setFilters] = useState<CostFilters>({
    date_range: {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end: new Date().toISOString().split('T')[0]
    }
  })
  const [showFilters, setShowFilters] = useState(false)
  const [showExportDialog, setShowExportDialog] = useState(false)
  const [activeTab, setActiveTab] = useState("trends")

  const {
    costSummary,
    costTrends,
    costBreakdown,
    costRecords,
    isLoading,
    error,
    refetch
  } = useCostAnalysis(filters)

  const handleFiltersChange = (newFilters: CostFilters) => {
    setFilters(newFilters)
  }

  const handleRefresh = () => {
    refetch()
  }

  const handleExport = () => {
    setShowExportDialog(true)
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto py-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Cost Analysis</h1>
            <p className="text-gray-600 mt-1">Loading comprehensive cost analysis...</p>
          </div>
        </div>
        <LoadingState type="cards" count={3} />
        <LoadingState type="chart" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto py-8">
        <ErrorState
          title="Failed to load cost analysis data"
          message="We couldn't load your cost analysis. Please check your connection and try again."
          onRetry={handleRefresh}
          showRetry={true}
        />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Cost Analysis</h1>
          <p className="text-gray-600 mt-1">
            Comprehensive cost analysis and reporting across all cloud providers
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
          
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          <Button
            onClick={handleExport}
            className="flex items-center"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <FilterPanel
              filters={filters}
              onChange={handleFiltersChange}
              onClose={() => setShowFilters(false)}
            />
          </CardContent>
        </Card>
      )}

      {/* Cost Summary Cards with Fallbacks */}
      {costSummary ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${(costSummary.total_cost || 0).toLocaleString()}
                  </p>
                  <div className="flex items-center mt-2">
                    <span className={`text-sm font-medium ${
                      (costSummary.month_over_month_change || 0) >= 0 ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {(costSummary.month_over_month_change || 0) >= 0 ? '+' : ''}
                      {(costSummary.month_over_month_change || 0).toFixed(1)}%
                    </span>
                    <span className="text-gray-500 text-sm ml-1">vs previous period</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Providers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {costSummary.provider_breakdown?.length || 0}
                  </p>
                  <p className="text-sm text-gray-500 mt-2">
                    {costSummary.account_breakdown?.length || 0} accounts
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Top Service</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {costSummary.service_breakdown?.[0]?.service || 'N/A'}
                  </p>
                  <p className="text-sm text-gray-500 mt-2">
                    ${(costSummary.service_breakdown?.[0]?.cost || 0).toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <EmptyState
          title="No cost summary available"
          message="Cost summary will appear here once data is loaded."
          icon="search"
        />
      )}

      {/* Analysis Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="breakdown">Breakdown</TabsTrigger>
          <TabsTrigger value="comparison">Comparison</TabsTrigger>
          <TabsTrigger value="data">Raw Data</TabsTrigger>
        </TabsList>

        <TabsContent value="trends" className="space-y-6">
          {costTrends && costTrends.length > 0 ? (
            <CostTrendsChart
              data={costTrends}
              loading={isLoading}
              filters={filters}
            />
          ) : (
            <EmptyState
              title="No trend data available"
              message="Cost trends will appear here once sufficient data is collected."
              icon="search"
            />
          )}
        </TabsContent>

        <TabsContent value="breakdown" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {costBreakdown?.services && costBreakdown.services.length > 0 ? (
              <CostBreakdownChart
                data={costBreakdown.services}
                loading={isLoading}
                title="Cost by Service"
                type="service"
              />
            ) : (
              <EmptyState
                title="No service breakdown available"
                message="Service cost breakdown will appear here."
                icon="search"
              />
            )}
            
            {costBreakdown?.providers && costBreakdown.providers.length > 0 ? (
              <CostBreakdownChart
                data={costBreakdown.providers}
                loading={isLoading}
                title="Cost by Provider"
                type="provider"
              />
            ) : (
              <EmptyState
                title="No provider breakdown available"
                message="Provider cost breakdown will appear here."
                icon="search"
              />
            )}
          </div>
        </TabsContent>

        <TabsContent value="comparison" className="space-y-6">
          {costSummary?.provider_breakdown && costSummary.provider_breakdown.length > 0 ? (
            <ProviderComparisonChart
              data={costSummary.provider_breakdown}
              loading={isLoading}
              filters={filters}
            />
          ) : (
            <EmptyState
              title="No comparison data available"
              message="Provider comparison will appear here once data is available."
              icon="search"
            />
          )}
        </TabsContent>

        <TabsContent value="data" className="space-y-6">
          {costRecords?.data && costRecords.data.length > 0 ? (
            <CostDataTable
              data={costRecords}
              loading={isLoading}
              filters={filters}
              onFiltersChange={handleFiltersChange}
            />
          ) : (
            <EmptyState
              title="No cost records available"
              message="Cost records will appear here once data is loaded."
              icon="search"
            />
          )}
        </TabsContent>
      </Tabs>

      {/* Export Dialog */}
      <ExportDialog
        open={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        filters={filters}
      />
    </div>
  )
}