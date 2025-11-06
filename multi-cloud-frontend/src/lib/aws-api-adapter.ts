/**
 * AWS API Adapter
 * 
 * Adapts the existing AWS API to work with the frontend expectations
 */

import axios from 'axios';

const AWS_API_BASE = 'https://jrltysmyg5.execute-api.us-east-1.amazonaws.com';

// Create axios instance without credentials for AWS
const awsApiClient = axios.create({
  baseURL: AWS_API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false, // Disable credentials for AWS API
});

export const awsApiAdapter = {
  // Auth endpoints (mock for now since AWS API doesn't have them)
  async login(credentials: { email: string; password: string }) {
    // Mock login for AWS environment
    return {
      success: true,
      data: {
        user: {
          id: 'aws-user-123',
          name: 'AWS User',
          email: credentials.email,
          role: 'ADMIN',
          organization_id: 'aws-org-123'
        },
        organization: {
          id: 'aws-org-123',
          name: '4bfast Organization'
        },
        token: 'aws-token-123'
      }
    };
  },

  async getProfile() {
    return {
      success: true,
      data: {
        user: {
          id: 'aws-user-123',
          name: 'AWS User',
          email: 'user@4bfast.com',
          role: 'ADMIN',
          organization_id: 'aws-org-123'
        },
        organization: {
          id: 'aws-org-123',
          name: '4bfast Organization'
        }
      }
    };
  },

  // Dashboard endpoints - adapt AWS API responses
  async getDashboardMetrics() {
    const response = await awsApiClient.get('/costs');
    const data = response.data;
    
    return {
      success: true,
      data: {
        total_monthly_cost: data.totalCost || 0,
        month_over_month_change: data.costVariation || 0,
        connected_accounts: data.accountBreakdown?.length || 0,
        active_alarms: data.anomaliesCount || 0,
        unread_insights: data.recommendationsCount || 0,
        top_service: data.serviceBreakdown?.[0] ? {
          service_name: data.serviceBreakdown[0].service,
          cost: data.serviceBreakdown[0].cost,
          percentage: 0
        } : null
      }
    };
  },

  async getServiceBreakdown() {
    const response = await awsApiClient.get('/costs');
    const data = response.data;
    
    return {
      success: true,
      data: data.serviceBreakdown?.slice(0, 5).map((service: any) => ({
        service_name: service.service,
        cost: service.cost,
        percentage: (service.cost / data.totalCost * 100).toFixed(1),
        trend: 0,
        provider: 'aws'
      })) || []
    };
  },

  async getRecentAlarms() {
    // Mock alarms since AWS API doesn't have this endpoint
    return {
      success: true,
      data: []
    };
  },

  async getInsightsSummary() {
    const response = await awsApiClient.get('/insights');
    const data = response.data;
    
    return {
      success: true,
      data: {
        total_new_insights: data.count || 0,
        high_priority_count: 0,
        potential_monthly_savings: 0,
        recent_insights: data.insights?.slice(0, 3).map((insight: any, index: number) => ({
          id: `insight-${index}`,
          type: 'recommendation',
          severity: 'medium',
          title: insight.title || 'Insight',
          description: insight.description || '',
          created_at: new Date().toISOString()
        })) || []
      }
    };
  },

  async getCostOverview() {
    const response = await awsApiClient.get('/costs');
    const data = response.data;
    
    return {
      success: true,
      data: {
        current_period: {
          total_cost: data.totalCost || 0,
          start_date: data.startDate || '',
          end_date: data.endDate || ''
        },
        daily_breakdown: [] // AWS API doesn't provide daily breakdown
      }
    };
  }
};
