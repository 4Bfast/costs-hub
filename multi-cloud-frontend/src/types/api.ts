import { CloudProvider } from './models';

// Base API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  metadata: {
    timestamp: string;
    version: string;
    request_id: string;
    client_id?: string;
  };
  errors: string[];
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// Cost data types
export interface CostRecord {
  id: string;
  client_id: string;
  provider: 'aws' | 'gcp' | 'azure';
  service: string;
  cost: number;
  usage_date: string;
  currency: string;
  account_id?: string;
  region?: string;
  tags?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface CostSummary {
  total_cost: number;
  currency: string;
  period_start: string;
  period_end: string;
  provider_breakdown: {
    provider: CloudProvider;
    cost: number;
    percentage: number;
    account_count: number;
    service_count: number;
    trend: number;
  }[];
  service_breakdown: {
    service: string;
    cost: number;
    percentage: number;
    account_count: number;
    trend: number;
    category?: string;
  }[];
  account_breakdown: {
    account_id: string;
    account_name: string;
    cost: number;
    percentage: number;
  }[];
  month_over_month_change: number;
  cost_trend: {
    date: string;
    cost: number;
  }[];
}

// Provider account types
export interface CloudProviderAccount {
  id: string;
  client_id: string;
  provider: 'aws' | 'gcp' | 'azure';
  account_id: string;
  account_name: string;
  status: 'active' | 'inactive' | 'error' | 'pending';
  last_sync: string | null;
  configuration: {
    role_arn?: string; // AWS
    project_id?: string; // GCP
    subscription_id?: string; // Azure
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
}

// AI Insights types
export interface AIInsight {
  id: string;
  client_id: string;
  type: 'anomaly' | 'recommendation' | 'forecast' | 'optimization';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  details: {
    affected_services?: string[];
    cost_impact?: number;
    potential_savings?: number;
    confidence_score?: number;
    time_period?: {
      start: string;
      end: string;
    };
    recommendations?: {
      action: string;
      estimated_savings: number;
      effort_level: 'low' | 'medium' | 'high';
    }[];
  };
  status: 'new' | 'acknowledged' | 'dismissed' | 'implemented';
  created_at: string;
  updated_at: string;
}

// Alarm types
export interface Alarm {
  id: string;
  client_id: string;
  name: string;
  description?: string;
  type: 'threshold' | 'anomaly' | 'budget' | 'forecast';
  status: 'active' | 'inactive';
  configuration: {
    threshold?: number;
    comparison: 'greater_than' | 'less_than' | 'equal_to';
    period: 'daily' | 'weekly' | 'monthly';
    providers?: string[];
    services?: string[];
    accounts?: string[];
  };
  notification_settings: {
    email: boolean;
    webhook?: string;
    channels: string[];
  };
  last_triggered?: string;
  trigger_count: number;
  created_at: string;
  updated_at: string;
}

export interface AlarmEvent {
  id: string;
  alarm_id: string;
  client_id: string;
  triggered_at: string;
  current_value: number;
  threshold_value: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details: {
    affected_accounts?: string[];
    affected_services?: string[];
    cost_breakdown?: {
      service: string;
      cost: number;
    }[];
  };
  status: 'new' | 'acknowledged' | 'resolved';
  acknowledged_at?: string;
  acknowledged_by?: string;
}

// User and organization types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'ADMIN' | 'MEMBER';
  organization_id: string;
  status: 'active' | 'inactive' | 'pending';
  last_login?: string;
  preferences: {
    theme: 'light' | 'dark' | 'system';
    notifications: {
      email: boolean;
      push: boolean;
      frequency: 'immediate' | 'hourly' | 'daily' | 'weekly';
    };
    dashboard: {
      default_period: string;
      default_providers: string[];
    };
  };
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'trial';
  subscription: {
    plan: 'free' | 'pro' | 'enterprise';
    status: 'active' | 'cancelled' | 'past_due';
    current_period_start: string;
    current_period_end: string;
  };
  settings: {
    data_retention_days: number;
    cost_currency: string;
    timezone: string;
    features: {
      ai_insights: boolean;
      multi_cloud: boolean;
      advanced_analytics: boolean;
    };
  };
  created_at: string;
  updated_at: string;
}

// Filter and query types
export interface CostFilters {
  providers?: string[];
  services?: string[];
  accounts?: string[];
  date_range?: {
    start: string;
    end: string;
  };
  cost_range?: {
    min: number;
    max: number;
  };
  tags?: Record<string, string>;
}

export interface QueryParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
  search?: string;
  filters?: CostFilters;
}

// Dashboard data types
export interface DashboardData {
  cost_summary: CostSummary;
  recent_insights: AIInsight[];
  active_alarms: AlarmEvent[];
  provider_accounts: CloudProviderAccount[];
  top_services: {
    service: string;
    cost: number;
    percentage: number;
    trend: number;
  }[];
}

// Export/import types
export interface ExportRequest {
  format: 'csv' | 'excel' | 'json';
  filters?: CostFilters;
  columns?: string[];
  date_range: {
    start: string;
    end: string;
  };
}

export interface ExportJob {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  download_url?: string;
  expires_at?: string;
  created_at: string;
}

// Notification types
export interface Notification {
  id: string;
  client_id: string;
  type: 'alarm' | 'insight' | 'system' | 'billing';
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  read: boolean;
  data?: Record<string, any>;
  created_at: string;
}

// Settings types
export interface NotificationSettings {
  email_notifications: boolean;
  push_notifications: boolean;
  notification_frequency: 'immediate' | 'hourly' | 'daily' | 'weekly';
  alarm_notifications: {
    threshold: boolean;
    anomaly: boolean;
    budget: boolean;
    forecast: boolean;
  };
  insight_notifications: {
    high_severity: boolean;
    medium_severity: boolean;
    low_severity: boolean;
  };
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  currency: string;
  dashboard_settings: {
    default_period: string;
    default_providers: string[];
    refresh_interval: number;
  };
  notification_settings: NotificationSettings;
}