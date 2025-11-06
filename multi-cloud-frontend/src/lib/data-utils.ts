import { 
  CostRecord, 
  CostSummary, 
  CloudProvider, 
  CostTrendPoint,
  ServiceBreakdown,
  ProviderBreakdown,
  AIInsight,
  AlarmEvent,
  DateRange 
} from '@/types/models';

// Currency formatting utilities
export const formatCurrency = (
  amount: number, 
  currency = 'USD', 
  options?: Intl.NumberFormatOptions
): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    ...options,
  }).format(amount);
};

export const formatCompactCurrency = (amount: number, currency = 'USD'): string => {
  if (amount >= 1000000) {
    return formatCurrency(amount / 1000000, currency, { 
      minimumFractionDigits: 1,
      maximumFractionDigits: 1 
    }) + 'M';
  } else if (amount >= 1000) {
    return formatCurrency(amount / 1000, currency, { 
      minimumFractionDigits: 1,
      maximumFractionDigits: 1 
    }) + 'K';
  }
  return formatCurrency(amount, currency);
};

// Percentage formatting
export const formatPercentage = (
  value: number, 
  options?: Intl.NumberFormatOptions
): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    ...options,
  }).format(value / 100);
};

// Date formatting utilities
export const formatDate = (
  date: string | Date, 
  options?: Intl.DateTimeFormatOptions
): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  }).format(dateObj);
};

export const formatDateTime = (date: string | Date): string => {
  return formatDate(date, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const formatRelativeTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - dateObj.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return formatDate(dateObj);
};

// Cost calculation utilities
export const calculateCostChange = (
  current: number, 
  previous: number
): { amount: number; percentage: number; trend: 'up' | 'down' | 'stable' } => {
  const amount = current - previous;
  const percentage = previous === 0 ? 0 : (amount / previous) * 100;
  
  let trend: 'up' | 'down' | 'stable' = 'stable';
  if (Math.abs(percentage) > 0.1) {
    trend = percentage > 0 ? 'up' : 'down';
  }
  
  return { amount, percentage, trend };
};

export const aggregateCostsByPeriod = (
  records: CostRecord[], 
  period: 'daily' | 'weekly' | 'monthly'
): CostTrendPoint[] => {
  const groupedData = new Map<string, number>();
  
  records.forEach(record => {
    let key: string;
    const date = new Date(record.usage_date);
    
    switch (period) {
      case 'daily':
        key = date.toISOString().split('T')[0];
        break;
      case 'weekly':
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - date.getDay());
        key = weekStart.toISOString().split('T')[0];
        break;
      case 'monthly':
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        break;
      default:
        key = date.toISOString().split('T')[0];
    }
    
    groupedData.set(key, (groupedData.get(key) || 0) + record.cost);
  });
  
  return Array.from(groupedData.entries())
    .map(([date, cost]) => ({ date, cost }))
    .sort((a, b) => a.date.localeCompare(b.date));
};

// Provider utilities
export const getProviderDisplayName = (provider: CloudProvider): string => {
  const names = {
    aws: 'Amazon Web Services',
    gcp: 'Google Cloud Platform',
    azure: 'Microsoft Azure',
  };
  return names[provider] || provider.toUpperCase();
};

export const getProviderColor = (provider: CloudProvider): string => {
  const colors = {
    aws: '#FF9900',
    gcp: '#4285F4',
    azure: '#0078D4',
  };
  return colors[provider] || '#6B7280';
};

export const getProviderIcon = (provider: CloudProvider): string => {
  const icons = {
    aws: '☁️',
    gcp: '🌐',
    azure: '🔷',
  };
  return icons[provider] || '☁️';
};

// Service categorization
export const categorizeService = (service: string, provider: CloudProvider): string => {
  const categories: Record<CloudProvider, Record<string, string>> = {
    aws: {
      'EC2': 'Compute',
      'Lambda': 'Compute',
      'ECS': 'Compute',
      'EKS': 'Compute',
      'S3': 'Storage',
      'EBS': 'Storage',
      'EFS': 'Storage',
      'RDS': 'Database',
      'DynamoDB': 'Database',
      'ElastiCache': 'Database',
      'CloudFront': 'Networking',
      'VPC': 'Networking',
      'Route53': 'Networking',
    },
    gcp: {
      'Compute Engine': 'Compute',
      'Cloud Functions': 'Compute',
      'GKE': 'Compute',
      'Cloud Storage': 'Storage',
      'Persistent Disk': 'Storage',
      'Cloud SQL': 'Database',
      'Firestore': 'Database',
      'BigQuery': 'Analytics',
      'Cloud CDN': 'Networking',
      'VPC': 'Networking',
    },
    azure: {
      'Virtual Machines': 'Compute',
      'Functions': 'Compute',
      'AKS': 'Compute',
      'Blob Storage': 'Storage',
      'Disk Storage': 'Storage',
      'SQL Database': 'Database',
      'Cosmos DB': 'Database',
      'CDN': 'Networking',
      'Virtual Network': 'Networking',
    },
  };
  
  return categories[provider]?.[service] || 'Other';
};

// Data transformation utilities
export const transformCostRecordsToSummary = (
  records: CostRecord[], 
  dateRange: DateRange
): CostSummary => {
  const totalCost = records.reduce((sum, record) => sum + record.cost, 0);
  
  // Provider breakdown
  const providerMap = new Map<CloudProvider, number>();
  records.forEach(record => {
    providerMap.set(record.provider, (providerMap.get(record.provider) || 0) + record.cost);
  });
  
  const providerBreakdown: ProviderBreakdown[] = Array.from(providerMap.entries()).map(([provider, cost]) => ({
    provider,
    cost,
    percentage: (cost / totalCost) * 100,
    account_count: new Set(records.filter(r => r.provider === provider).map(r => r.account_id)).size,
    service_count: new Set(records.filter(r => r.provider === provider).map(r => r.service)).size,
    trend: 0, // Would need historical data to calculate
  }));
  
  // Service breakdown
  const serviceMap = new Map<string, { cost: number; provider: CloudProvider; accounts: Set<string> }>();
  records.forEach(record => {
    const key = `${record.service}-${record.provider}`;
    const existing = serviceMap.get(key) || { cost: 0, provider: record.provider, accounts: new Set() };
    existing.cost += record.cost;
    existing.accounts.add(record.account_id);
    serviceMap.set(key, existing);
  });
  
  const serviceBreakdown: ServiceBreakdown[] = Array.from(serviceMap.entries()).map(([key, data]) => {
    const [service] = key.split('-');
    return {
      service,
      provider: data.provider,
      cost: data.cost,
      percentage: (data.cost / totalCost) * 100,
      account_count: data.accounts.size,
      trend: 0, // Would need historical data to calculate
      category: categorizeService(service, data.provider),
    };
  });
  
  // Account breakdown
  const accountMap = new Map<string, { cost: number; provider: CloudProvider; services: Set<string> }>();
  records.forEach(record => {
    const existing = accountMap.get(record.account_id) || { 
      cost: 0, 
      provider: record.provider, 
      services: new Set() 
    };
    existing.cost += record.cost;
    existing.services.add(record.service);
    accountMap.set(record.account_id, existing);
  });
  
  const accountBreakdown = Array.from(accountMap.entries()).map(([accountId, data]) => ({
    account_id: accountId,
    account_name: accountId, // Would need to lookup actual name
    provider: data.provider,
    cost: data.cost,
    percentage: (data.cost / totalCost) * 100,
    service_count: data.services.size,
    trend: 0,
  }));
  
  // Region breakdown
  const regionMap = new Map<string, { cost: number; provider: CloudProvider; services: Set<string> }>();
  records.forEach(record => {
    if (record.region) {
      const existing = regionMap.get(record.region) || { 
        cost: 0, 
        provider: record.provider, 
        services: new Set() 
      };
      existing.cost += record.cost;
      existing.services.add(record.service);
      regionMap.set(record.region, existing);
    }
  });
  
  const regionBreakdown = Array.from(regionMap.entries()).map(([region, data]) => ({
    region,
    provider: data.provider,
    cost: data.cost,
    percentage: (data.cost / totalCost) * 100,
    service_count: data.services.size,
  }));
  
  // Cost trend (daily aggregation)
  const costTrend = aggregateCostsByPeriod(records, 'daily');
  
  return {
    total_cost: totalCost,
    currency: records[0]?.currency || 'USD',
    period_start: dateRange.start,
    period_end: dateRange.end,
    provider_breakdown: providerBreakdown.sort((a, b) => b.cost - a.cost),
    service_breakdown: serviceBreakdown.sort((a, b) => b.cost - a.cost),
    account_breakdown: accountBreakdown.sort((a, b) => b.cost - a.cost),
    region_breakdown: regionBreakdown.sort((a, b) => b.cost - a.cost),
    month_over_month_change: 0, // Would need previous period data
    cost_trend: costTrend,
  };
};

// Insight utilities
export const getInsightSeverityColor = (severity: AIInsight['severity']): string => {
  const colors = {
    low: '#10B981',
    medium: '#F59E0B',
    high: '#EF4444',
    critical: '#DC2626',
  };
  return colors[severity];
};

export const getInsightTypeIcon = (type: AIInsight['type']): string => {
  const icons = {
    anomaly: '⚠️',
    recommendation: '💡',
    forecast: '📈',
    optimization: '⚡',
    trend: '📊',
  };
  return icons[type] || '📊';
};

export const getAlarmSeverityColor = (severity: AlarmEvent['severity']): string => {
  return getInsightSeverityColor(severity);
};

// Date range utilities
export const getDateRangePresets = (): Array<{ label: string; value: string; range: DateRange }> => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  
  return [
    {
      label: 'Last 7 days',
      value: '7d',
      range: {
        start: new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        end: today.toISOString().split('T')[0],
      },
    },
    {
      label: 'Last 30 days',
      value: '30d',
      range: {
        start: new Date(today.getTime() - 29 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        end: today.toISOString().split('T')[0],
      },
    },
    {
      label: 'Last 90 days',
      value: '90d',
      range: {
        start: new Date(today.getTime() - 89 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        end: today.toISOString().split('T')[0],
      },
    },
    {
      label: 'This month',
      value: 'month',
      range: {
        start: new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0],
        end: today.toISOString().split('T')[0],
      },
    },
    {
      label: 'Last month',
      value: 'last_month',
      range: {
        start: new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0],
        end: new Date(now.getFullYear(), now.getMonth(), 0).toISOString().split('T')[0],
      },
    },
  ];
};

// Validation utilities
export const validateDateRange = (range: DateRange): boolean => {
  const start = new Date(range.start);
  const end = new Date(range.end);
  const now = new Date();
  
  return start <= end && end <= now;
};

export const validateCostValue = (value: number): boolean => {
  return typeof value === 'number' && value >= 0 && isFinite(value);
};

// Search and filter utilities
export const filterCostRecords = (
  records: CostRecord[], 
  searchTerm: string
): CostRecord[] => {
  if (!searchTerm.trim()) return records;
  
  const term = searchTerm.toLowerCase();
  return records.filter(record => 
    record.service.toLowerCase().includes(term) ||
    record.account_id.toLowerCase().includes(term) ||
    record.provider.toLowerCase().includes(term) ||
    record.region?.toLowerCase().includes(term) ||
    Object.values(record.tags).some(tag => 
      tag.toLowerCase().includes(term)
    )
  );
};

export const sortCostRecords = (
  records: CostRecord[], 
  sortBy: keyof CostRecord, 
  order: 'asc' | 'desc' = 'desc'
): CostRecord[] => {
  return [...records].sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return order === 'asc' ? aVal - bVal : bVal - aVal;
    }
    
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return order === 'asc' 
        ? aVal.localeCompare(bVal) 
        : bVal.localeCompare(aVal);
    }
    
    return 0;
  });
};

// Chart data transformation
export const transformForLineChart = (
  data: CostTrendPoint[], 
  options?: { fillGaps?: boolean; maxPoints?: number }
): Array<{ date: string; cost: number; formattedDate: string }> => {
  let processedData = data.map(point => ({
    ...point,
    formattedDate: formatDate(point.date, { month: 'short', day: 'numeric' }),
  }));
  
  // Limit number of points for performance
  if (options?.maxPoints && processedData.length > options.maxPoints) {
    const step = Math.ceil(processedData.length / options.maxPoints);
    processedData = processedData.filter((_, index) => index % step === 0);
  }
  
  return processedData;
};

export const transformForPieChart = (
  breakdown: ServiceBreakdown[] | ProviderBreakdown[], 
  maxSlices = 5
): Array<{ name: string; value: number; percentage: number; color: string }> => {
  const sorted = [...breakdown].sort((a, b) => b.cost - a.cost);
  const topItems = sorted.slice(0, maxSlices - 1);
  const others = sorted.slice(maxSlices - 1);
  
  const result = topItems.map((item, index) => ({
    name: 'provider' in item ? getProviderDisplayName(item.provider) : (item as ServiceBreakdown).service,
    value: item.cost,
    percentage: item.percentage,
    color: 'provider' in item ? getProviderColor(item.provider) : `hsl(${index * 45}, 70%, 50%)`,
  }));
  
  if (others.length > 0) {
    const othersCost = others.reduce((sum, item) => sum + item.cost, 0);
    const othersPercentage = others.reduce((sum, item) => sum + item.percentage, 0);
    
    result.push({
      name: 'Others',
      value: othersCost,
      percentage: othersPercentage,
      color: '#9CA3AF',
    });
  }
  
  return result;
};