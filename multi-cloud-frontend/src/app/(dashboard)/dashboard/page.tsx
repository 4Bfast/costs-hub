"use client";

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { AlertCircle, Download, Plus, DollarSign, Cloud, Bell, BarChart } from "lucide-react";
import { useDashboardMetrics } from "@/hooks/use-dashboard";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";

function DashboardPageInner() {
  const { user } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  
  // Use real dashboard metrics hook
  const { data: metricsResponse, isLoading: metricsLoading, error: metricsError, refetch } = useDashboardMetrics();
  
  // Extract metrics data with fallbacks
  const metrics = metricsResponse?.data;

  useEffect(() => {
    const errorParam = searchParams.get('error');
    if (errorParam === 'insufficient_permissions' && !error) {
      setError('You do not have permission to access that page.');
    }
  }, [searchParams, error]);

  // Handle loading state
  if (metricsLoading) {
    return (
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">Loading your cost analytics overview...</p>
          </div>
        </div>
        <LoadingState type="cards" count={4} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <LoadingState type="chart" />
          <LoadingState type="chart" />
        </div>
      </div>
    );
  }

  // Handle error state
  if (metricsError) {
    return (
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">Welcome back! Here's your multi-cloud cost analytics overview.</p>
          </div>
        </div>
        <ErrorState
          title="Failed to load dashboard data"
          message="We couldn't load your dashboard metrics. Please check your connection and try again."
          onRetry={refetch}
          showRetry={true}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md flex items-center">
          <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
          <p className="text-red-600">{error}</p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setError(null)}
            className="ml-auto"
          >
            ×
          </Button>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Welcome back, {user?.name || 'User'}! Here's your multi-cloud cost analytics overview.
          </p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Metrics Cards with Fallbacks */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Monthly Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${(metrics?.total_monthly_cost || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              {metrics?.month_over_month_change !== undefined 
                ? `${metrics.month_over_month_change > 0 ? '+' : ''}${metrics.month_over_month_change.toFixed(1)}% from last month`
                : 'No change data available'
              }
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connected Accounts</CardTitle>
            <Cloud className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.connected_accounts || 0}
            </div>
            <p className="text-xs text-muted-foreground">accounts</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alarms</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.active_alarms || 0}
            </div>
            <p className="text-xs text-muted-foreground">alerts</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Top Service</CardTitle>
            <BarChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.top_service?.service_name || 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              {metrics?.top_service?.cost 
                ? `$${metrics.top_service.cost.toLocaleString()}`
                : 'No data'
              }
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Content Cards with Empty States */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Cost Trend (7 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {metrics?.cost_trend_7d && metrics.cost_trend_7d.length > 0 ? (
              <div className="space-y-2">
                {metrics.cost_trend_7d.slice(0, 3).map((point, index) => (
                  <div key={index} className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">{point.date}</span>
                    <span className="font-medium">${point.cost.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-8">
                No cost trend data available
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Provider Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {metrics?.provider_distribution && metrics.provider_distribution.length > 0 ? (
              <div className="space-y-2">
                {metrics.provider_distribution.slice(0, 3).map((provider, index) => (
                  <div key={index} className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 capitalize">{provider.provider}</span>
                    <div className="text-right">
                      <div className="font-medium">${provider.cost.toFixed(2)}</div>
                      <div className="text-xs text-gray-500">{provider.percentage.toFixed(1)}%</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-8">
                No provider data available
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {metrics?.recent_activity && metrics.recent_activity.length > 0 ? (
              <div className="space-y-3">
                {metrics.recent_activity.slice(0, 3).map((activity, index) => (
                  <div key={index} className="border-l-2 border-blue-200 pl-3">
                    <div className="font-medium text-sm">{activity.title}</div>
                    <div className="text-xs text-gray-600">{activity.description}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {new Date(activity.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-8">
                No recent activity
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Insights Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">
                {metrics?.unread_insights || 0} unread insights available
              </p>
              <Button variant="outline" size="sm">
                View All Insights
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DashboardPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      }>
        <DashboardPageInner />
      </Suspense>
    </ProtectedRoute>
  );
}

export default DashboardPage;
