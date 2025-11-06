'use client';

import React, { Suspense, lazy } from 'react';
import { ChartSkeleton } from '@/components/ui/skeleton';

// Dynamically import chart components for better code splitting
const CostLineChart = lazy(() => import('./cost-line-chart').then(module => ({ default: module.CostLineChart })));
const CostBarChart = lazy(() => import('./cost-bar-chart').then(module => ({ default: module.CostBarChart })));
const CostPieChart = lazy(() => import('./cost-pie-chart').then(module => ({ default: module.CostPieChart })));

// For advanced charts, we'll import the scatter plot as default
const AdvancedChartsWrapper = lazy(() => 
  import('./advanced-charts').then(module => ({
    default: module.CostUsageScatterPlot
  }))
);

interface DynamicChartProps {
  type: 'line' | 'bar' | 'pie' | 'advanced';
  data: any;
  height?: string;
  loading?: boolean;
  [key: string]: any;
}

export function DynamicChart({ type, data, height = "300px", loading = false, ...props }: DynamicChartProps) {
  if (loading || !data) {
    return <ChartSkeleton height={height} />;
  }

  const renderChart = () => {
    switch (type) {
      case 'line':
        return <CostLineChart data={data} {...props} />;
      case 'bar':
        return <CostBarChart data={data} {...props} />;
      case 'pie':
        return <CostPieChart data={data} {...props} />;
      case 'advanced':
        return <AdvancedChartsWrapper data={data} {...props} />;
      default:
        return <div>Unsupported chart type</div>;
    }
  };

  return (
    <Suspense fallback={<ChartSkeleton height={height} />}>
      <div style={{ height }}>
        {renderChart()}
      </div>
    </Suspense>
  );
}

// Individual dynamic chart components for more granular loading
export const DynamicLineChart = ({ data, loading, ...props }: any) => (
  <Suspense fallback={<ChartSkeleton />}>
    {loading ? <ChartSkeleton /> : <CostLineChart data={data} {...props} />}
  </Suspense>
);

export const DynamicBarChart = ({ data, loading, ...props }: any) => (
  <Suspense fallback={<ChartSkeleton />}>
    {loading ? <ChartSkeleton /> : <CostBarChart data={data} {...props} />}
  </Suspense>
);

export const DynamicPieChart = ({ data, loading, ...props }: any) => (
  <Suspense fallback={<ChartSkeleton />}>
    {loading ? <ChartSkeleton /> : <CostPieChart data={data} {...props} />}
  </Suspense>
);