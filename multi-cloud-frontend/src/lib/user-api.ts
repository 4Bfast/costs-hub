import { apiClient } from './api-client';
import { User } from '@/types/models';
import { ApiResponse, PaginatedResponse, QueryParams } from '@/types/api';

// User invitation types
export interface InviteUserRequest {
  email: string;
  name: string;
  role: 'ADMIN' | 'MEMBER';
  message?: string;
}

export interface InviteUserResponse {
  invitation_id: string;
  email: string;
  name: string;
  role: 'ADMIN' | 'MEMBER';
  status: 'pending';
  expires_at: string;
  invited_by: string;
  created_at: string;
}

export interface UpdateUserRoleRequest {
  role: 'ADMIN' | 'MEMBER';
}

export interface UserListFilters {
  status?: 'active' | 'inactive' | 'pending' | 'suspended';
  role?: 'ADMIN' | 'MEMBER';
  search?: string;
}

export interface UserStats {
  total_users: number;
  active_users: number;
  pending_invitations: number;
  admin_count: number;
  member_count: number;
  last_activity: string;
}

class UserApiService {
  private readonly basePath = '/users';

  /**
   * Get list of users in the organization
   */
  async getUsers(params?: QueryParams & { filters?: UserListFilters }): Promise<PaginatedResponse<User>> {
    const queryParams = new URLSearchParams();
    
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.sort) queryParams.append('sort', params.sort);
    if (params?.order) queryParams.append('order', params.order);
    if (params?.search) queryParams.append('search', params.search);
    
    // Add filters
    if (params?.filters?.status) queryParams.append('status', params.filters.status);
    if (params?.filters?.role) queryParams.append('role', params.filters.role);
    if (params?.filters?.search) queryParams.append('search', params.filters.search);

    const url = `${this.basePath}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return apiClient.getPaginated<User>(url);
  }

  /**
   * Get user statistics for the organization
   */
  async getUserStats(): Promise<ApiResponse<UserStats>> {
    return apiClient.get<UserStats>(`${this.basePath}/stats`);
  }

  /**
   * Get a specific user by ID
   */
  async getUser(userId: string): Promise<ApiResponse<User>> {
    return apiClient.get<User>(`${this.basePath}/${userId}`);
  }

  /**
   * Invite a new user to the organization
   */
  async inviteUser(data: InviteUserRequest): Promise<ApiResponse<InviteUserResponse>> {
    return apiClient.post<InviteUserResponse>(`${this.basePath}/invite`, data);
  }

  /**
   * Resend invitation to a pending user
   */
  async resendInvitation(userId: string): Promise<ApiResponse<{ message: string }>> {
    return apiClient.post<{ message: string }>(`${this.basePath}/${userId}/resend-invitation`);
  }

  /**
   * Revoke a pending invitation
   */
  async revokeInvitation(userId: string): Promise<ApiResponse<{ message: string }>> {
    return apiClient.delete<{ message: string }>(`${this.basePath}/${userId}/invitation`);
  }

  /**
   * Update user role
   */
  async updateUserRole(userId: string, data: UpdateUserRoleRequest): Promise<ApiResponse<User>> {
    return apiClient.patch<User>(`${this.basePath}/${userId}/role`, data);
  }

  /**
   * Deactivate a user
   */
  async deactivateUser(userId: string): Promise<ApiResponse<User>> {
    return apiClient.patch<User>(`${this.basePath}/${userId}/deactivate`);
  }

  /**
   * Reactivate a user
   */
  async reactivateUser(userId: string): Promise<ApiResponse<User>> {
    return apiClient.patch<User>(`${this.basePath}/${userId}/reactivate`);
  }

  /**
   * Delete a user (permanent action)
   */
  async deleteUser(userId: string): Promise<ApiResponse<{ message: string }>> {
    return apiClient.delete<{ message: string }>(`${this.basePath}/${userId}`);
  }

  /**
   * Update user profile (for self-updates)
   */
  async updateProfile(data: { name?: string; email?: string }): Promise<ApiResponse<User>> {
    return apiClient.patch<User>(`${this.basePath}/profile`, data);
  }

  /**
   * Change user password (for self-updates)
   */
  async changePassword(data: { 
    current_password: string; 
    new_password: string; 
  }): Promise<ApiResponse<{ message: string }>> {
    return apiClient.post<{ message: string }>(`${this.basePath}/change-password`, data);
  }

  /**
   * Get user activity log
   */
  async getUserActivity(
    userId: string, 
    params?: { 
      page?: number; 
      limit?: number; 
      date_range?: { start: string; end: string } 
    }
  ): Promise<PaginatedResponse<{
    id: string;
    action: string;
    description: string;
    ip_address?: string;
    user_agent?: string;
    created_at: string;
  }>> {
    const queryParams = new URLSearchParams();
    
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.date_range?.start) queryParams.append('start_date', params.date_range.start);
    if (params?.date_range?.end) queryParams.append('end_date', params.date_range.end);

    const url = `${this.basePath}/${userId}/activity${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return apiClient.getPaginated(url);
  }

  /**
   * Bulk operations on users
   */
  async bulkUpdateUsers(data: {
    user_ids: string[];
    action: 'activate' | 'deactivate' | 'delete' | 'change_role';
    role?: 'ADMIN' | 'MEMBER';
  }): Promise<ApiResponse<{ 
    success_count: number; 
    failed_count: number; 
    errors: Array<{ user_id: string; error: string }> 
  }>> {
    return apiClient.post(`${this.basePath}/bulk-update`, data);
  }

  /**
   * Export users data
   */
  async exportUsers(format: 'csv' | 'excel' = 'csv'): Promise<void> {
    const response = await apiClient.downloadFile(
      `${this.basePath}/export?format=${format}`,
      `users-export-${new Date().toISOString().split('T')[0]}.${format}`
    );
    return response;
  }

  /**
   * Check if email is available for invitation
   */
  async checkEmailAvailability(email: string): Promise<ApiResponse<{ available: boolean; reason?: string }>> {
    return apiClient.get<{ available: boolean; reason?: string }>(
      `${this.basePath}/check-email?email=${encodeURIComponent(email)}`
    );
  }

  /**
   * Get organization member limits and usage
   */
  async getMemberLimits(): Promise<ApiResponse<{
    current_count: number;
    max_allowed: number;
    pending_invitations: number;
    can_invite_more: boolean;
  }>> {
    return apiClient.get(`${this.basePath}/limits`);
  }
}

// Create singleton instance
export const userApiService = new UserApiService();