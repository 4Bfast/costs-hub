"use client"

import React, { useState, useMemo } from "react"
import { useAuth } from "@/contexts/auth-context"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Plus,
  Search,
  MoreHorizontal,
  Users,
  UserCheck,
  AlertCircle,
} from "lucide-react"
import { useUsers, useUserStats, useUserManagement } from "@/hooks/use-user-management"

interface UserListFilters {
  status?: 'active' | 'inactive' | 'pending' | 'suspended';
  role?: 'ADMIN' | 'MEMBER';
  search?: string;
}

export default function UsersPage() {
  const { user } = useAuth()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<UserListFilters['status']>()
  const [roleFilter, setRoleFilter] = useState<UserListFilters['role']>()
  const [currentPage, setCurrentPage] = useState(1)

  const filters = useMemo<UserListFilters>(() => ({
    search: searchQuery || undefined,
    status: statusFilter,
    role: roleFilter,
  }), [searchQuery, statusFilter, roleFilter])

  const {
    data: usersResponse,
    isLoading: usersLoading,
    error: usersError
  } = useUsers({
    page: currentPage,
    limit: 10,
    filters
  })

  const {
    data: statsResponse,
    isLoading: statsLoading
  } = useUserStats()

  const {
    updateUserRole,
    deactivateUser,
    reactivateUser,
    deleteUser,
    isUpdatingRole,
    isDeactivating,
    isReactivating,
    isDeleting
  } = useUserManagement()

  const users = Array.isArray(usersResponse?.data?.users) ? usersResponse.data.users : 
                Array.isArray(usersResponse?.data) ? usersResponse.data : []
  const pagination = usersResponse?.pagination
  const stats = statsResponse?.data

  // Debug detalhado
  console.log('🔍 Debug Users:', {
    usersResponse,
    users,
    usersLength: users.length,
    stats,
    usersLoading,
    usersError
  })

  // Debug autenticação
  React.useEffect(() => {
    const checkAuth = async () => {
      const environment = process.env.NEXT_PUBLIC_ENVIRONMENT;
      console.log('🔐 Environment:', environment);
      
      if (environment === 'production') {
        const { cognitoTokenManager } = await import('@/lib/cognito-token-manager');
        const token = await cognitoTokenManager.getAccessToken();
        console.log('🎫 Cognito Token:', token ? 'EXISTS' : 'NULL');
        if (token) {
          console.log('🎫 Token preview:', token.substring(0, 50) + '...');
        }
      }
    };
    checkAuth();
  }, [])

  // Check if user has admin privileges
  if (user?.role !== 'ADMIN') {
    return (
      <div className="max-w-7xl mx-auto space-y-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Access Restricted</h3>
            <p className="text-gray-600 text-center">
              You need administrator privileges to access user management.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const getRoleBadge = (role: string) => {
    const variants = {
      ADMIN: 'destructive',
      MEMBER: 'secondary'
    } as const
    
    return (
      <Badge variant={variants[role as keyof typeof variants] || 'secondary'}>
        {role}
      </Badge>
    )
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'default',
      pending: 'secondary',
      inactive: 'outline',
      suspended: 'destructive'
    } as const
    
    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status}
      </Badge>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  if (usersError) {
    return (
      <div className="max-w-7xl mx-auto space-y-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Users</h3>
            <p className="text-gray-600 text-center">
              Failed to load user data. Please try again.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Users</h1>
          <p className="text-gray-600 mt-1">Manage your team members and their permissions</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Invite User
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-2xl font-bold text-gray-900">{stats?.total_users || 0}</p>
            )}
            <p className="text-xs text-muted-foreground">All team members</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-2xl font-bold text-gray-900">{stats?.active_users || 0}</p>
            )}
            <p className="text-xs text-muted-foreground">Currently active</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Invites</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-2xl font-bold text-gray-900">{stats?.pending_invitations || 0}</p>
            )}
            <p className="text-xs text-muted-foreground">Awaiting response</p>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search users by name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Users Table */}
          {usersLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-[200px]" />
                    <Skeleton className="h-4 w-[150px]" />
                  </div>
                </div>
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12">
              <Users className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No users found</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by inviting your first team member.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Activity</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((userItem: any) => (
                    <TableRow key={userItem.id}>
                      <TableCell>
                        <div className="flex items-center space-x-3">
                          <div className="flex-shrink-0 h-8 w-8 bg-blue-500 rounded-full flex items-center justify-center">
                            <span className="text-sm font-medium text-white">
                              {userItem.name?.charAt(0).toUpperCase() || 'U'}
                            </span>
                          </div>
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {userItem.name || 'Unknown User'}
                              {userItem.id === user?.id && (
                                <Badge variant="outline" className="ml-2">You</Badge>
                              )}
                            </div>
                            <div className="text-sm text-gray-500">
                              {userItem.email}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {getRoleBadge(userItem.role)}
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(userItem.status)}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {userItem.status === 'pending' ? (
                          <span>
                            Invited {formatDate(userItem.created_at)}
                          </span>
                        ) : userItem.last_login ? (
                          <span>
                            {formatDate(userItem.last_login)}
                          </span>
                        ) : (
                          <span>Never</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {pagination && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-700">
                    Showing {((currentPage - 1) * 10) + 1} to {Math.min(currentPage * 10, pagination.total)} of{' '}
                    {pagination.total} users
                  </p>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={!pagination.hasPrev}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => prev + 1)}
                      disabled={!pagination.hasNext}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
