// Types for discovered accounts from FOCUS data

export interface DiscoveredAccount {
  id: string;
  provider: 'aws' | 'gcp' | 'azure';
  account_id: string;
  account_name?: string;
  organization_id?: string;
  parent_account_id?: string;
  status: 'discovered' | 'linked' | 'ignored';
  first_seen: string;
  last_seen: string;
  cost_summary: {
    total_cost_30d: number;
    total_cost_7d: number;
    currency: string;
    top_services: Array<{
      service: string;
      cost: number;
      percentage: number;
    }>;
  };
  metadata: {
    source: 'focus_export' | 'billing_api' | 'cost_explorer';
    confidence_score: number;
    data_completeness: number;
    last_updated: string;
  };
  linking_suggestions?: {
    suggested_connection_type: 'cross_account_role' | 'organization_member' | 'manual';
    confidence: number;
    reasons: string[];
    estimated_setup_time: string;
  };
  tags?: Record<string, string>;
}

export interface AccountLinkingSuggestion {
  discovered_account_id: string;
  suggestion_type: 'high_cost' | 'new_account' | 'missing_data' | 'organization_member';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  potential_savings?: number;
  setup_complexity: 'easy' | 'medium' | 'complex';
  estimated_time: string;
  benefits: string[];
  requirements: string[];
}

export interface DiscoveredAccountsFilters {
  providers?: ('aws' | 'gcp' | 'azure')[];
  status?: ('discovered' | 'linked' | 'ignored')[];
  cost_threshold?: number;
  date_range?: {
    start: string;
    end: string;
  };
  sort_by?: 'cost' | 'first_seen' | 'last_seen' | 'account_name';
  sort_order?: 'asc' | 'desc';
}

export interface DiscoveredAccountsStats {
  total_discovered: number;
  total_linked: number;
  total_ignored: number;
  total_cost_30d: number;
  potential_savings: number;
  new_accounts_this_week: number;
  high_cost_unlinked: number;
}