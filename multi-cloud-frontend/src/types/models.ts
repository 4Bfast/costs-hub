// Core data models and interfaces for the multi-cloud cost analytics platform

// Base model interface
export interface BaseModel {
  id: string;
  created_at: string;
  updated_at: string;
}

// User model
export interface User extends BaseModel {
  email: string;
  name: string;
  role: UserRole;
  organization_id: string;
  status: UserStatus;
  last_login?: string;
  email_verified: boolean;
  preferences: UserPreferences;
  avatar_url?: string;
}

export type UserRole = 'ADMIN' | 'MEMBER';
export type UserStatus = 'active' | 'inactive' | 'pending' | 'suspended';

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  currency: string;
  dashboard_settings: {
    default_period: string;
    default_providers: string[];
    refresh_interval: number;
    compact_view: boolean;
  };
  notification_settings: NotificationSettings;
}

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

// Organization model
export interface Organization extends BaseModel {
  name: string;
  status: OrganizationStatus;
  subscription: Subscription;
  settings: OrganizationSettings;
  billing_info?: BillingInfo;
  member_count: number;
  account_count: number;
}

export type OrganizationStatus = 'active' | 'inactive' | 'trial' | 'suspended';

export interface Subscription {
  plan: 'free' | 'pro' | 'enterprise';
  status: 'active' | 'cancelled' | 'past_due' | 'trialing';
  current_period_start: string;
  current_period_end: string;
  trial_end?: string;
  cancel_at_period_end: boolean;
}

export interface OrganizationSettings {
  data_retention_days: number;
  cost_currency: string;
  timezone: string;
  features: {
    ai_insights: boolean;
    multi_cloud: boolean;
    advanced_analytics: boolean;
    custom_reports: boolean;
    api_access: boolean;
  };
  limits: {
    max_accounts: number;
    max_users: number;
    max_alarms: number;
    api_rate_limit: number;
  };
}

export interface BillingInfo {
  company_name?: string;
  tax_id?: string;
  address: {
    line1: string;
    line2?: string;
    city: string;
    state?: string;
    postal_code: string;
    country: string;
  };
  payment_method?: {
    type: 'card' | 'bank_account';
    last4: string;
    brand?: string;
    expires?: string;
  };
}

// Cloud Provider Account model
export interface CloudProviderAccount extends BaseModel {
  client_id: string;
  provider: CloudProvider;
  account_id: string;
  account_name: string;
  display_name?: string;
  status: AccountStatus;
  last_sync?: string;
  next_sync?: string;
  configuration: ProviderConfiguration;
  sync_settings: SyncSettings;
  cost_summary?: AccountCostSummary;
  tags?: Record<string, string>;
}

export type CloudProvider = 'aws' | 'gcp' | 'azure';
export type AccountStatus = 'active' | 'inactive' | 'error' | 'pending' | 'syncing';

export interface ProviderConfiguration {
  // AWS specific
  role_arn?: string;
  external_id?: string;
  regions?: string[];
  
  // GCP specific
  project_id?: string;
  service_account_key?: string;
  
  // Azure specific
  subscription_id?: string;
  tenant_id?: string;
  client_id?: string;
  client_secret?: string;
  
  // Common settings
  cost_allocation_tags?: string[];
  exclude_services?: string[];
  include_support_costs?: boolean;
  include_tax?: boolean;
}

export interface SyncSettings {
  enabled: boolean;
  frequency: 'hourly' | 'daily' | 'weekly';
  sync_historical_data: boolean;
  historical_months: number;
  auto_retry: boolean;
  max_retries: number;
}

export interface AccountCostSummary {
  total_cost_30d: number;
  total_cost_7d: number;
  month_over_month_change: number;
  top_services: Array<{
    service: string;
    cost: number;
    percentage: number;
  }>;
  last_updated: string;
}

// Cost Record model
export interface CostRecord extends BaseModel {
  client_id: string;
  provider: CloudProvider;
  account_id: string;
  service: string;
  service_category?: string;
  cost: number;
  usage_quantity?: number;
  usage_unit?: string;
  usage_date: string;
  billing_period: string;
  currency: string;
  region?: string;
  availability_zone?: string;
  resource_id?: string;
  resource_type?: string;
  tags: Record<string, string>;
  metadata: CostRecordMetadata;
}

export interface CostRecordMetadata {
  source: 'billing_api' | 'cost_explorer' | 'focus_export' | 'manual';
  import_job_id?: string;
  raw_data?: Record<string, any>;
  confidence_score?: number;
  anomaly_score?: number;
}

// Cost Summary model
export interface CostSummary {
  total_cost: number;
  currency: string;
  period_start: string;
  period_end: string;
  provider_breakdown: ProviderBreakdown[];
  service_breakdown: ServiceBreakdown[];
  account_breakdown: AccountBreakdown[];
  region_breakdown: RegionBreakdown[];
  month_over_month_change: number;
  cost_trend: CostTrendPoint[];
  forecast?: CostForecast;
}

export interface ProviderBreakdown {
  provider: CloudProvider;
  cost: number;
  percentage: number;
  account_count: number;
  service_count: number;
  trend: number;
}

export interface ServiceBreakdown {
  service: string;
  provider: CloudProvider;
  cost: number;
  percentage: number;
  account_count: number;
  trend: number;
  category?: string;
}

export interface AccountBreakdown {
  account_id: string;
  account_name: string;
  provider: CloudProvider;
  cost: number;
  percentage: number;
  service_count: number;
  trend: number;
}

export interface RegionBreakdown {
  region: string;
  provider: CloudProvider;
  cost: number;
  percentage: number;
  service_count: number;
}

export interface CostTrendPoint {
  date: string;
  cost: number;
  provider?: CloudProvider;
  service?: string;
  account_id?: string;
}

export interface CostForecast {
  predicted_cost: number;
  confidence_lower: number;
  confidence_upper: number;
  confidence_level: number;
  forecast_period: string;
  methodology: string;
  factors: string[];
}

// AI Insight model
export interface AIInsight extends BaseModel {
  client_id: string;
  type: InsightType;
  severity: InsightSeverity;
  title: string;
  description: string;
  summary: string;
  details: InsightDetails;
  status: InsightStatus;
  confidence_score: number;
  potential_impact: PotentialImpact;
  affected_resources: AffectedResource[];
  recommendations: Recommendation[];
  metadata: InsightMetadata;
}

export type InsightType = 'anomaly' | 'recommendation' | 'forecast' | 'optimization' | 'trend';
export type InsightSeverity = 'low' | 'medium' | 'high' | 'critical';
export type InsightStatus = 'new' | 'acknowledged' | 'dismissed' | 'implemented' | 'expired';

export interface InsightDetails {
  time_period?: {
    start: string;
    end: string;
  };
  affected_services?: string[];
  affected_accounts?: string[];
  cost_impact?: number;
  usage_impact?: number;
  baseline_data?: Record<string, any>;
  anomaly_data?: Record<string, any>;
  trend_data?: CostTrendPoint[];
}

export interface PotentialImpact {
  cost_savings?: number;
  cost_increase?: number;
  efficiency_gain?: number;
  risk_level?: 'low' | 'medium' | 'high';
  time_to_impact?: string;
}

export interface AffectedResource {
  resource_id: string;
  resource_type: string;
  provider: CloudProvider;
  account_id: string;
  service: string;
  region?: string;
  cost_impact: number;
  tags?: Record<string, string>;
}

export interface Recommendation {
  id: string;
  action: string;
  description: string;
  estimated_savings: number;
  effort_level: 'low' | 'medium' | 'high';
  implementation_steps: string[];
  risks: string[];
  prerequisites: string[];
  priority: number;
  category: string;
}

export interface InsightMetadata {
  detection_method: string;
  model_version?: string;
  data_sources: string[];
  processing_time?: number;
  related_insights?: string[];
  external_references?: string[];
}

// Alarm model
export interface Alarm extends BaseModel {
  client_id: string;
  name: string;
  description?: string;
  type: AlarmType;
  status: AlarmStatus;
  configuration: AlarmConfiguration;
  notification_settings: AlarmNotificationSettings;
  last_triggered?: string;
  trigger_count: number;
  evaluation_history: AlarmEvaluation[];
}

export type AlarmType = 'threshold' | 'anomaly' | 'budget' | 'forecast' | 'efficiency';
export type AlarmStatus = 'active' | 'inactive' | 'paused' | 'error';

export interface AlarmConfiguration {
  threshold?: number;
  comparison: 'greater_than' | 'less_than' | 'equal_to' | 'not_equal_to';
  period: 'hourly' | 'daily' | 'weekly' | 'monthly';
  evaluation_frequency: number; // in minutes
  datapoints_to_alarm: number;
  missing_data_treatment: 'breaching' | 'not_breaching' | 'ignore';
  
  // Scope
  providers?: CloudProvider[];
  services?: string[];
  accounts?: string[];
  regions?: string[];
  tags?: Record<string, string>;
  
  // Advanced settings
  anomaly_detection?: {
    sensitivity: 'low' | 'medium' | 'high';
    exclude_weekends: boolean;
    exclude_holidays: boolean;
  };
  
  budget_settings?: {
    budget_amount: number;
    budget_period: 'monthly' | 'quarterly' | 'yearly';
    alert_thresholds: number[]; // percentages
  };
}

export interface AlarmNotificationSettings {
  email: boolean;
  webhook?: string;
  channels: string[];
  escalation_policy?: {
    enabled: boolean;
    levels: Array<{
      delay_minutes: number;
      recipients: string[];
    }>;
  };
  quiet_hours?: {
    enabled: boolean;
    start_time: string;
    end_time: string;
    timezone: string;
  };
}

export interface AlarmEvaluation {
  timestamp: string;
  value: number;
  threshold: number;
  state: 'OK' | 'ALARM' | 'INSUFFICIENT_DATA';
  reason: string;
}

// Alarm Event model
export interface AlarmEvent extends BaseModel {
  alarm_id: string;
  client_id: string;
  triggered_at: string;
  resolved_at?: string;
  current_value: number;
  threshold_value: number;
  severity: InsightSeverity;
  message: string;
  details: AlarmEventDetails;
  status: AlarmEventStatus;
  acknowledged_at?: string;
  acknowledged_by?: string;
  notes?: string;
}

export type AlarmEventStatus = 'new' | 'acknowledged' | 'resolved' | 'suppressed';

export interface AlarmEventDetails {
  affected_accounts?: string[];
  affected_services?: string[];
  cost_breakdown?: Array<{
    service: string;
    account_id: string;
    cost: number;
    percentage: number;
  }>;
  trend_data?: CostTrendPoint[];
  contributing_factors?: string[];
  recommended_actions?: string[];
}

// Notification model
export interface Notification extends BaseModel {
  client_id: string;
  user_id?: string; // null for organization-wide notifications
  type: NotificationType;
  title: string;
  message: string;
  severity: NotificationSeverity;
  read: boolean;
  read_at?: string;
  data?: Record<string, any>;
  action_url?: string;
  expires_at?: string;
}

export type NotificationType = 'alarm' | 'insight' | 'system' | 'billing' | 'account' | 'user';
export type NotificationSeverity = 'info' | 'warning' | 'error' | 'success';

// Filter and query types
export interface CostFilters {
  providers?: CloudProvider[];
  services?: string[];
  accounts?: string[];
  regions?: string[];
  date_range?: DateRange;
  cost_range?: NumberRange;
  tags?: Record<string, string>;
  resource_types?: string[];
}

export interface DateRange {
  start: string;
  end: string;
}

export interface NumberRange {
  min: number;
  max: number;
}

export interface QueryParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
  search?: string;
}

// Dashboard data types
export interface DashboardData {
  cost_summary: CostSummary;
  recent_insights: AIInsight[];
  active_alarms: AlarmEvent[];
  provider_accounts: CloudProviderAccount[];
  top_services: ServiceBreakdown[];
  account_health: AccountHealthSummary;
  budget_status?: BudgetStatus;
}

export interface AccountHealthSummary {
  total_accounts: number;
  healthy_accounts: number;
  accounts_with_issues: number;
  sync_status: {
    syncing_now: number;
    last_sync_24h: number;
    sync_errors: number;
  };
}

export interface BudgetStatus {
  monthly_budget?: number;
  current_spend: number;
  projected_spend: number;
  budget_utilization: number;
  days_remaining: number;
  status: 'on_track' | 'at_risk' | 'over_budget' | 'no_budget';
}

// Export/import types
export interface ExportRequest {
  format: 'csv' | 'excel' | 'json' | 'pdf';
  type: 'costs' | 'insights' | 'alarms' | 'accounts';
  filters?: CostFilters | Record<string, any>;
  columns?: string[];
  date_range?: DateRange;
  options?: {
    include_metadata?: boolean;
    include_tags?: boolean;
    group_by?: string[];
  };
}

export interface ExportJob extends BaseModel {
  client_id: string;
  user_id: string;
  type: ExportRequest['type'];
  format: ExportRequest['format'];
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'expired';
  download_url?: string;
  file_size?: number;
  expires_at?: string;
  error_message?: string;
  progress?: number;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

// API response wrapper types
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