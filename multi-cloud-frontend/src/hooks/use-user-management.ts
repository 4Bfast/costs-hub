import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { 
  userApiService, 
  InviteUserRequest, 
  UpdateUserRoleRequest, 
  UserListFilters 
} from '@/lib/user-api';
import { QueryParams } from '@/types/api';
import { User } from '@/types/models';

// Query keys for React Query
export const userQueryKeys = {
  all: ['users'] as const,
  lists: () => [...userQueryKeys.all, 'list'] as const,
  list: (params?: QueryParams & { filters?: UserListFilters }) => 
    [...userQueryKeys.lists(), params] as const,
  stats: () => [...userQueryKeys.all, 'stats'] as const,
  detail: (id: string) => [...userQueryKeys.all, 'detail', id] as const,
  activity: (id: string, params?: any) => 
    [...userQueryKeys.all, 'activity', id, params] as const,
  limits: () => [...userQueryKeys.all, 'limits'] as const,
};

// Hook for fetching users list
export function useUsers(params?: QueryParams & { filters?: UserListFilters }) {
  return useQuery({
    queryKey: userQueryKeys.list(params),
    queryFn: () => userApiService.getUsers(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Hook for user statistics
export function useUserStats() {
  return useQuery({
    queryKey: userQueryKeys.stats(),
    queryFn: () => userApiService.getUserStats(),
    staleTime: 5 * 60 * 1000,
  });
}

// Hook for member limits
export function useMemberLimits() {
  return useQuery({
    queryKey: userQueryKeys.limits(),
    queryFn: () => userApiService.getMemberLimits(),
    staleTime: 5 * 60 * 1000,
  });
}

// Hook for user management operations
export function useUserManagement() {
  const queryClient = useQueryClient();

  const inviteUser = useMutation({
    mutationFn: (data: InviteUserRequest) => userApiService.inviteUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all });
      toast.success('User invitation sent successfully');
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to send invitation');
    },
  });

  const updateUserRole = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UpdateUserRoleRequest }) =>
      userApiService.updateUserRole(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all });
      toast.success('User role updated successfully');
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to update user role');
    },
  });

  const resendInvitation = useMutation({
    mutationFn: (userId: string) => userApiService.resendInvitation(userId),
    onSuccess: () => {
      toast.success('Invitation resent successfully');
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to resend invitation');
    },
  });

  const revokeInvitation = useMutation({
    mutationFn: (userId: string) => userApiService.revokeInvitation(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all });
      toast.success('Invitation revoked successfully');
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to revoke invitation');
    },
  });

  const deactivateUser = useMutation({
    mutationFn: (userId: string) => userApiService.deactivateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all });
      toast.success('User deactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to deactivate user');
    },
  });

  const reactivateUser = useMutation({
    mutationFn: (userId: string) => userApiService.reactivateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all });
      toast.success('User reactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to reactivate user');
    },
  });

  const deleteUser = useMutation({
    mutationFn: (userId: string) => userApiService.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all });
      toast.success('User deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to delete user');
    },
  });

  return {
    inviteUser: inviteUser.mutate,
    updateUserRole: updateUserRole.mutate,
    resendInvitation: resendInvitation.mutate,
    revokeInvitation: revokeInvitation.mutate,
    deactivateUser: deactivateUser.mutate,
    reactivateUser: reactivateUser.mutate,
    deleteUser: deleteUser.mutate,
    isInviting: inviteUser.isPending,
    isUpdatingRole: updateUserRole.isPending,
    isResending: resendInvitation.isPending,
    isRevoking: revokeInvitation.isPending,
    isDeactivating: deactivateUser.isPending,
    isReactivating: reactivateUser.isPending,
    isDeleting: deleteUser.isPending,
  };
}
